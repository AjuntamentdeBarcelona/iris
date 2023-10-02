import base64
import uuid
from datetime import timedelta

import pytest
from django.dispatch import Signal
from django.utils import timezone
from mock import Mock, patch
from model_mommy import mommy
from rest_framework.status import (HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_201_CREATED, HTTP_409_CONFLICT,
                                   HTTP_404_NOT_FOUND)

from communications.models import Conversation, Message, ConversationUnreadMessagesGroup
from features.models import Feature
from iris_masters.models import (Support, RecordType, Application, District, ResponseChannel, RecordState,
                                 ResolutionType, Reason, Parameter, InputChannel, ApplicantType, Process)
from main.open_api.tests.base import (OpenAPIResourceListMixin, OpenAPIRetrieveMixin, PostOperationMixin,
                                      DictListGetMixin)
from main.urls import OPEN_API_URL_NAME
from main.utils import GALICIAN, SPANISH
from public_api.tests.base import BasePublicAPITest
from record_cards.models import (Citizen, Applicant, RecordCard, ApplicantResponse, WorkflowResolution,
                                 RecordCardStateHistory, Comment, RecordFile, InternalOperator)
from record_cards.record_actions.alarms import RecordCardAlarms
from record_cards.tests.utils import CreateRecordCardMixin, CreateRecordFileMixin
from themes.models import ElementDetailFeature, ApplicationElementDetail, ElementDetail
from themes.tests.utils import CreateThemesMixin


class TestPublicAreaList(CreateThemesMixin, OpenAPIResourceListMixin, BasePublicAPITest):
    path = "/areas"

    def given_an_object(self):
        element_detail = self.create_element_detail(short_description=uuid.uuid4(), description=uuid.uuid4())
        mommy.make(ApplicationElementDetail, application=Application.objects.get(description_hash=Application.ATE_HASH),
                   detail=element_detail, user_id="222")
        return element_detail.element.area


class TestPublicElementFavouriteList(CreateThemesMixin, OpenAPIResourceListMixin, BasePublicAPITest):
    path = "/elements/favourites"

    def given_an_object(self):
        element = self.create_element(is_favorite=True)
        element_detail = self.create_element_detail(element=element, short_description=uuid.uuid4(),
                                                    description=uuid.uuid4())
        mommy.make(ApplicationElementDetail, application=Application.objects.get(description_hash=Application.ATE_HASH),
                   detail=element_detail, user_id="222")
        return element


class TestPublicElementDetailSearch(CreateThemesMixin, OpenAPIResourceListMixin, BasePublicAPITest):
    path = "/details"

    def given_an_object(self):
        element_detail = self.create_element_detail(short_description=uuid.uuid4(), description=uuid.uuid4())
        mommy.make(ApplicationElementDetail, application=Application.objects.get(description_hash=Application.ATE_HASH),
                   detail=element_detail, user_id="222")
        return element_detail

    @pytest.mark.parametrize("object_number", (0, 1, 3))
    def test_list(self, object_number):
        element_details = [self.given_an_object() for _ in range(0, object_number)]

        force_params = {"page_size": self.paginate_by}
        if element_details:
            force_params["search"] = element_details[0].description
        response = self.list(force_params=force_params)

        objects_list = 1 if element_details else 0
        self.should_return_list(objects_list, self.paginate_by, response)


class TestElementDetailRetrieveView(CreateThemesMixin, OpenAPIRetrieveMixin, BasePublicAPITest):
    detail_path = "/details/{id}/fields"

    def test_retrieve(self):
        obj = self.given_an_object()
        response = self.retrieve(force_params={"id": obj.id})
        assert response.status_code == HTTP_200_OK
        assert response.json()["detailId"] == obj.id

    def given_an_object(self, application_id=Application.ATE_PK):
        element_detail = self.create_element_detail(short_description=uuid.uuid4(), description=uuid.uuid4())
        ApplicationElementDetail.objects.create(detail=element_detail, application_id=application_id)
        feature = mommy.make(Feature, user_id="2323")
        mommy.make(ElementDetailFeature, element_detail=element_detail, feature=feature, user_id="2323")
        return element_detail

    def test_retrieve_webdirecto(self):
        obj = self.given_an_object(Application.WEB_DIRECTO)
        response = self.retrieve(force_params={"id": obj.id})
        assert response.status_code == HTTP_200_OK
        assert response.json()["detailId"] == obj.id

    def test_retrieve_consultes_directo(self):
        obj = self.given_an_object(Application.CONSULTES_DIRECTO)
        response = self.retrieve(force_params={"id": obj.id})
        assert response.status_code == HTTP_200_OK
        assert response.json()["detailId"] == obj.id


class TestElementDetailLastUpdated(CreateThemesMixin, DictListGetMixin, BasePublicAPITest):
    path = "/details/last_updated/"

    def test_detail_last_updated(self):
        element_detail = self.create_element_detail(short_description=uuid.uuid4(), description=uuid.uuid4())
        ApplicationElementDetail.objects.create(detail=element_detail, application_id=Application.ATE_PK)
        response = self.dict_list_retrieve()
        assert response.status_code == HTTP_200_OK
        assert response.json()["updated_at"]


class TestRecordCardRetrieveView(CreateRecordCardMixin, OpenAPIRetrieveMixin, BasePublicAPITest):
    detail_path = "/incidences/{id}"

    def test_retrieve(self):
        obj = self.given_an_object()
        response = self.retrieve(force_params=self.get_url_params(obj))
        assert response.status_code == HTTP_200_OK
        self.check_object(response.json(), obj)

    def get_url_params(self, obj):
        return {"id": obj.id, }

    def given_an_object(self):
        return self.create_record_card()

    def check_object(self, data, obj):
        assert data["incidenceId"] == obj.id


class TestRecordCardRetrieveStateView(TestRecordCardRetrieveView):
    detail_path = "/incidences/state/{id}"

    def get_url_params(self, obj):
        return {"id": obj.normalized_record_id, }

    def check_object(self, data, obj):
        fields = ["normalized_record_id", "created_at", "record_state", "can_be_claimed", "text_es", "text_en",
                  "text_ca", "close_cancel_date", "claim_record", "can_response_message"]
        for field in data.keys():
            assert field in fields, "This API can only return a very limited set of fields."
        for field in fields:
            assert field in data, "This API must return " + field


class AttachmentsTestApiMixin:

    @pytest.mark.parametrize("files_number,expected_response", (
            (0, HTTP_201_CREATED),
            (1, HTTP_201_CREATED),
            (10, HTTP_400_BAD_REQUEST)
    ))
    def test_create_with_attachment(self, image_file, files_number, expected_response):
        element_detail = self.create_element_detail()
        data = self.get_base_data(element_detail)
        data["pictures"] = [{
            "filename": "test.png",
            "data": str(base64.b64encode(image_file.tobytes()))[2:-1]
        } for _ in range(files_number)]

        get_public_features_pk = Mock(return_value=[])
        get_public_mandatory_features_pk = Mock(return_value=[])
        with patch("themes.managers.ElementDetailFeatureManager.get_public_features_pk", get_public_features_pk):
            with patch("themes.managers.ElementDetailFeatureManager.get_public_mandatory_features_pk",
                       get_public_mandatory_features_pk):
                response = self.post(force_params=data)
                assert response.status_code == expected_response
                if expected_response == HTTP_201_CREATED:
                    record_card = self.get_record_card(response.json())
                    assert RecordFile.objects.filter(record_card=record_card).count() == files_number
                    for record_file in RecordFile.objects.filter(record_card=record_card):
                        assert record_file.file_type == RecordFile.WEB

    def get_base_data(self, element_detail):
        return {}

    @staticmethod
    def get_record_card(response):
        raise NotImplementedError

    def test_max_file_size(self, image_file):
        element_detail = self.create_element_detail()
        data = self.get_base_data(element_detail)
        data["pictures"] = [{
            "filename": "test.png",
            "data": str(base64.b64encode(image_file.tobytes()))[2:-1]
        }]

        get_public_features_pk = Mock(return_value=[])
        get_public_mandatory_features_pk = Mock(return_value=[])
        check_file_size = Mock(return_value=False)
        with patch("themes.managers.ElementDetailFeatureManager.get_public_features_pk", get_public_features_pk):
            with patch("themes.managers.ElementDetailFeatureManager.get_public_mandatory_features_pk",
                       get_public_mandatory_features_pk):
                with patch("public_api.views.SetBase64AttachmentsMixin.check_file_size", check_file_size):
                    response = self.post(force_params=data)
                    assert response.status_code == HTTP_400_BAD_REQUEST


class TestRecordCardPublicCreateView(CreateThemesMixin, PostOperationMixin, BasePublicAPITest):
    path = "/incidences"

    @pytest.mark.parametrize(
        "element_detail,comments,transaction,support,applicant,citizen_applicant,social_entity_applicant,feature,"
        "feature_value,location,email,expected_response", (
                (True, "Test comments", "Urgent", True, False, True, False, True, "value", True, "test@test.com",
                 HTTP_201_CREATED),
                (True, "Test comments", "Urgent", True, False, False, True, True, "value", True, "test@test.com",
                 HTTP_201_CREATED),
                (False, "Test comments", "Urgent", True, True, False, False, True, "value", True,
                 "test@test.com", HTTP_400_BAD_REQUEST),
                (True, "", "Urgent", True, True, False, False, True, "value", True, "test@test.com",
                 HTTP_400_BAD_REQUEST),
                (True, "Test comments", "", True, True, False, False, True, "value", True, "test@test.com",
                 HTTP_400_BAD_REQUEST),
                (True, "Test comments", "Urgent", False, True, False, False, True, "value", True, "",
                 HTTP_201_CREATED),
                (True, "Test comments", "Urgent", True, False, False, False, True, "value", True, "test@test.com",
                 HTTP_400_BAD_REQUEST),
                (True, "Test comments", "Urgent", True, True, False, False, False, "value", True,
                 "test@test.com", HTTP_400_BAD_REQUEST),
                (True, "Test comments", "Urgent", True, True, False, False, True, "", True, "test@test.com",
                 HTTP_400_BAD_REQUEST),
                (True, "Test comments", "Urgent", True, True, False, False, True, "value", False, "",
                 HTTP_201_CREATED),
        ))
    def test_create_record_card(self, element_detail, comments, transaction, support, applicant, citizen_applicant,
                                social_entity_applicant, feature, feature_value, location, email,
                                expected_response):
        mommy.make(RecordType, pk=RecordType.SERVICE_REQUEST, user_id="2222")

        data = {
            "comments": comments,
            "transaction": transaction,
            "authorization": True
        }

        if element_detail:
            data["detailId"] = self.create_element_detail(record_type_id=RecordType.SERVICE_REQUEST).pk
        if support:
            data["device"] = mommy.make(Support, user_id="2222").pk

        self.set_applicant(applicant, citizen_applicant, social_entity_applicant, email, data)

        feature_data = {}
        if feature:
            feature_object = mommy.make(Feature, user_id="2222")
            feature_data["id"] = feature_object.pk
            features_pk_return = [feature_object.pk]
        else:
            features_pk_return = []

        if feature_value:
            feature_data["value"] = feature_value
        if feature_data:
            data["characteristics"] = [feature_data]

        if location:
            data["location"] = {"latitude": "", "longitude": "", "geocode": 1, "address": "Lincoln", "number": "0012",
                                "district": District.SARRIA_SANTGERVASSI}

        get_public_features_pk = Mock(return_value=features_pk_return)
        get_public_mandatory_features_pk = Mock(return_value=[])
        with patch("themes.managers.ElementDetailFeatureManager.get_public_features_pk", get_public_features_pk):
            with patch("themes.managers.ElementDetailFeatureManager.get_public_mandatory_features_pk",
                       get_public_mandatory_features_pk):
                response = self.post(force_params=data)
                assert response.status_code == expected_response
                if expected_response == HTTP_201_CREATED:
                    record_card = RecordCard.objects.get(normalized_record_id=response.json()["incidenceId"])
                    assert record_card.element_detail_id == data["detailId"]
                    assert record_card.organization == "WEB"
                    assert record_card.page_origin == "ATENCIO EN LINIA"
                    if email:
                        assert record_card.recordcardresponse.get_response_channel() == ResponseChannel.EMAIL
                        assert record_card.recordcardresponse.address_mobile_email == email
                    else:
                        assert record_card.recordcardresponse.get_response_channel() == ResponseChannel.NONE
                        assert record_card.recordcardresponse.address_mobile_email == ""
                    assert record_card.recordcardresponse.language == SPANISH

    def test_create_signal(self):
        signal = Mock(spec=Signal)
        element_detail = self.create_element_detail()
        data = self.get_base_data(element_detail)
        with patch("record_cards.models.record_card_created", signal):
            get_public_features_pk = Mock(return_value=[])
            get_public_mandatory_features_pk = Mock(return_value=[])
            with patch("themes.managers.ElementDetailFeatureManager.get_public_features_pk", get_public_features_pk):
                with patch("themes.managers.ElementDetailFeatureManager.get_public_mandatory_features_pk",
                           get_public_mandatory_features_pk):
                    response = self.post(force_params=data)
                    assert response.status_code == HTTP_201_CREATED
                    record_card = RecordCard.objects.get(normalized_record_id=response.json()["incidenceId"])
                    signal.send_robust.assert_called_with(record_card=record_card, sender=RecordCard)

    def get_base_data(self, element_detail):
        return {
            "comments": "description",
            "transaction": "Urgent",
            "nameCitizen": "test",
            "firstSurname": "test",
            "secondSurname": "test",
            "typeDocument": Citizen.NIF,
            "numberDocument": "47855987P",
            "district": District.CIUTAT_VELLA,
            "language": GALICIAN,
            "detailId": element_detail.pk,
            "location": {"latitude": "", "longitude": "", "geocode": 1,
                         "address": "Lincoln", "number": "0012", "district": District.SARRIA_SANTGERVASSI},
            "authorization": True
        }

    @staticmethod
    def get_record_card(response):
        return RecordCard.objects.get(normalized_record_id=response["incidenceId"])

    @staticmethod
    def set_applicant(applicant, citizen_applicant, social_entity_applicant, email, data):
        if applicant:
            citizen = mommy.make(Citizen, user_id="2222")
            db_applicant = mommy.make(Applicant, user_id="222", citizen=citizen)
            data["applicant"] = db_applicant.pk
            if email:
                mommy.make(ApplicantResponse, user_id="2222", enabled=True, email=email, applicant=db_applicant,
                           response_channel_id=ResponseChannel.EMAIL)
        if citizen_applicant:
            data["nameCitizen"] = "test"
            data["firstSurname"] = "test"
            data["secondSurname"] = "test"
            data["typeDocument"] = Citizen.NIF
            data["numberDocument"] = "47855987P"
            data["district"] = District.CIUTAT_VELLA
            if email:
                data["email"] = email
        if social_entity_applicant:
            data["socialReason"] = "test"
            data["contactPerson"] = "test"
            data["cif"] = "G07148612"
            if email:
                data["email"] = email
        data["language"] = SPANISH

    @pytest.mark.parametrize(
        "latitude,longitude,geocode,address,number,district,requires_ubication,requires_ubication_district,"
        "expected_response", (
                ("1.222", "1.4675", 1, "Lincoln", "0012", District.SARRIA_SANTGERVASSI, True, False, HTTP_201_CREATED),
                ("1.222", "1.4675", 1, "Lincoln", "0012", District.SARRIA_SANTGERVASSI, True, False, HTTP_201_CREATED),
                ("", "1.4675", 1, "Lincoln", "0012", District.SARRIA_SANTGERVASSI, True, False, HTTP_201_CREATED),
                ("1.222", "", 1, "Lincoln", "0012", District.SARRIA_SANTGERVASSI, True, False, HTTP_201_CREATED),
                ("1.222", "1.4675", None, "Lincoln", "0012", District.SARRIA_SANTGERVASSI, True, False,
                 HTTP_201_CREATED),
                ("1.222", "1.4675", None, "Lincoln", "0012", District.SARRIA_SANTGERVASSI, False, True,
                 HTTP_201_CREATED),
                ("1.222", "1.4675", 1, None, "0012", District.SARRIA_SANTGERVASSI, True, False, HTTP_400_BAD_REQUEST),
                ("1.222", "1.4675", 1, "Lincoln", None, District.SARRIA_SANTGERVASSI, True, False,
                 HTTP_400_BAD_REQUEST),
                ("1.2222222221222222222123", "1.4675", 1, "Lincoln", None, District.SARRIA_SANTGERVASSI, True, False,
                 HTTP_400_BAD_REQUEST),
                ("1.2222222221222222222123", "1.4675", 1, "Lincoln", None, District.SARRIA_SANTGERVASSI, True, False,
                 HTTP_400_BAD_REQUEST),
                ("1.222", "1.4675", None, "Lincoln", "0012", None, False, True, HTTP_400_BAD_REQUEST),
        ))
    def test_record_public_ubication(self, latitude, longitude, geocode, address, number, district,
                                     requires_ubication, requires_ubication_district, expected_response):

        ubication_data = {
            "latitude": latitude,
            "longitude": longitude,
            "address": address,
            "number": number,
            "district": district
        }
        if geocode:
            ubication_data["geocode"] = geocode

        mommy.make(RecordType, pk=RecordType.SERVICE_REQUEST, user_id="2222")
        element_detail = self.create_element_detail(requires_ubication=requires_ubication,
                                                    requires_ubication_district=requires_ubication_district,
                                                    record_type_id=RecordType.SERVICE_REQUEST)

        data = {
            "comments": "Test comments",
            "transaction": "URGENT",
            "detailId": element_detail.pk,
            "device": mommy.make(Support, user_id="2222").pk,
            "socialReason": "test",
            "contactPerson": "test",
            "cif": "G07148612",
            "language": GALICIAN,
            "email": "test@test.com",
            "location": ubication_data,
            "authorization": True
        }

        feature_data = {}
        feature_object = mommy.make(Feature, user_id="2222")
        feature_data["id"] = feature_object.pk
        feature_data["value"] = "aasdadsads"
        features_pk_return = [feature_object.pk]
        data["characteristics"] = [{"id": feature_object.pk, "value": "aasdadsads"}]

        get_public_features_pk = Mock(return_value=features_pk_return)
        get_public_mandatory_features_pk = Mock(return_value=[])
        with patch("themes.managers.ElementDetailFeatureManager.get_public_features_pk", get_public_features_pk):
            with patch("themes.managers.ElementDetailFeatureManager.get_public_mandatory_features_pk",
                       get_public_mandatory_features_pk):
                response = self.post(force_params=data)
                assert response.status_code == expected_response

    @pytest.mark.parametrize("applicant_blocked,allowed_theme,expected_response", (
            (True, False, HTTP_400_BAD_REQUEST),
            (False, False, HTTP_201_CREATED),
            (True, True, HTTP_201_CREATED),
            (False, True, HTTP_201_CREATED)
    ))
    def test_api_applicant_blocked(self, applicant_blocked, allowed_theme, expected_response):
        if allowed_theme:
            element = self.create_element()
            no_block_theme_pk = int(Parameter.get_parameter_by_key("TEMATICA_NO_BLOQUEJADA", 392))
            element_detail = mommy.make(ElementDetail, user_id="22222", pk=no_block_theme_pk, element=element,
                                        process_id=Process.CLOSED_DIRECTLY,
                                        record_type_id=mommy.make(RecordType, user_id="user_id").pk)
        else:
            element_detail = self.create_element_detail()
        citizen = mommy.make(Citizen, user_id="2222", blocked=applicant_blocked)
        data = self.get_base_data(element_detail)
        data["numberDocument"] = citizen.dni
        get_public_features_pk = Mock(return_value=[])
        get_public_mandatory_features_pk = Mock(return_value=[])
        with patch("themes.managers.ElementDetailFeatureManager.get_public_features_pk", get_public_features_pk):
            with patch("themes.managers.ElementDetailFeatureManager.get_public_mandatory_features_pk",
                       get_public_mandatory_features_pk):
                response = self.post(force_params=data)
                assert response.status_code == expected_response

    def test_public_create_autovalidate(self):
        element_detail = self.create_element_detail(autovalidate_records=True, process_id=Process.EXTERNAL_PROCESSING)
        data = self.get_base_data(element_detail)
        data.pop("location")
        get_public_features_pk = Mock(return_value=[])
        get_public_mandatory_features_pk = Mock(return_value=[])
        with patch("themes.managers.ElementDetailFeatureManager.get_public_features_pk", get_public_features_pk):
            with patch("themes.managers.ElementDetailFeatureManager.get_public_mandatory_features_pk",
                       get_public_mandatory_features_pk):
                response = self.post(force_params=data)
        assert response.status_code == HTTP_201_CREATED
        record_card = RecordCard.objects.get(normalized_record_id=response.json()["incidenceId"])
        assert record_card.record_state_id == RecordState.EXTERNAL_PROCESSING

    def test_public_create_internal_operator(self):
        element_detail = self.create_element_detail()
        data = self.get_base_data(element_detail)
        data.pop("location")

        citizen = mommy.make(Citizen, dni="GUB", user_id="2222")
        default_applicant = mommy.make(Applicant, citizen=citizen, user_id="2222")

        input_channel_id = int(Parameter.get_parameter_by_key("CANAL_ENTRADA_ATE", 7))
        InternalOperator.objects.create(document=data.get("numberDocument"), applicant_type_id=ApplicantType.CIUTADA,
                                        input_channel_id=input_channel_id)

        get_public_features_pk = Mock(return_value=[])
        get_public_mandatory_features_pk = Mock(return_value=[])
        with patch("themes.managers.ElementDetailFeatureManager.get_public_features_pk", get_public_features_pk):
            with patch("themes.managers.ElementDetailFeatureManager.get_public_mandatory_features_pk",
                       get_public_mandatory_features_pk):
                response = self.post(force_params=data)
        assert response.status_code == HTTP_201_CREATED
        record_card = RecordCard.objects.get(normalized_record_id=response.json()["incidenceId"])
        assert record_card.request.applicant_id == default_applicant.pk
        assert record_card.recordcardresponse.response_channel_id == ResponseChannel.NONE

    def test_public_create_immediate_response(self):
        element_detail = self.create_element_detail(immediate_response=True)
        data = self.get_base_data(element_detail)
        data.pop("location")

        get_public_features_pk = Mock(return_value=[])
        get_public_mandatory_features_pk = Mock(return_value=[])
        with patch("themes.managers.ElementDetailFeatureManager.get_public_features_pk", get_public_features_pk):
            with patch("themes.managers.ElementDetailFeatureManager.get_public_mandatory_features_pk",
                       get_public_mandatory_features_pk):
                response = self.post(force_params=data)
        assert response.status_code == HTTP_201_CREATED
        record_card = RecordCard.objects.get(normalized_record_id=response.json()["incidenceId"])
        assert record_card.recordcardresponse.response_channel_id == ResponseChannel.IMMEDIATE


class TestDistrictPublicList(OpenAPIResourceListMixin, BasePublicAPITest):
    path = "/districts"

    def test_list(self):
        response = self.list(force_params={"page_size": self.paginate_by})
        self.should_return_list(District.objects.count(), self.paginate_by, response)


class TestRecordCardSSIListView(OpenAPIResourceListMixin, CreateRecordCardMixin, BasePublicAPITest):
    base_api_path = "/services/iris/api"
    open_api_url_name = OPEN_API_URL_NAME
    path = "/ssi/records/"

    def given_an_object(self):
        element_detail = self.create_element_detail(allows_ssi=True)
        application = Application.objects.get(id=Application.ATE_PK)
        ApplicationElementDetail.objects.create(detail=element_detail, application=application)
        return self.create_record_card(application=application, element_detail=element_detail)


class TestRecordTypeListView(OpenAPIResourceListMixin, BasePublicAPITest):
    path = "/record_types/"

    def given_an_object(self):
        return mommy.make(RecordType, user_id="2222")


class TestRecordCardPublicClaimView(CreateRecordFileMixin, CreateRecordCardMixin, PostOperationMixin,
                                    BasePublicAPITest):
    path = "/incidences/{reference}/claim/"

    @pytest.mark.parametrize(
        "description,initial_state,exists_previous_claim,claim_limit_exceded,applicant_blocked,resolution_type_id,"
        "ans_limit_delta,expected_response", (
                ("description", RecordState.CLOSED, False, False, False, None, None, HTTP_201_CREATED),
                ("description", RecordState.CANCELLED, False, False, False, None, None, HTTP_201_CREATED),
                ("", RecordState.CLOSED, False, False, False, None, None, HTTP_400_BAD_REQUEST),
                ("description", RecordState.PENDING_VALIDATE, False, False, False, None, None, HTTP_201_CREATED),
                ("description", RecordState.CLOSED, True, False, False, None, None, HTTP_201_CREATED),
                ("description", RecordState.CLOSED, False, True, False, None, None, HTTP_409_CONFLICT),
                ("description", RecordState.CLOSED, False, False, True, None, None, HTTP_409_CONFLICT),
                ("description", RecordState.CLOSED, False, False, False, ResolutionType.PROGRAM_ACTION, True,
                 HTTP_201_CREATED),
                ("description", RecordState.CLOSED, False, False, False, ResolutionType.PROGRAM_ACTION, None,
                 HTTP_201_CREATED),
        ))
    def test_public_claim_record_card(self, description, initial_state, exists_previous_claim, claim_limit_exceded,
                                      applicant_blocked, resolution_type_id, ans_limit_delta, expected_response):
        citizen = mommy.make(Citizen, blocked=applicant_blocked, user_id="2222")
        applicant = mommy.make(Applicant, citizen=citizen, user_id="2222")

        if ans_limit_delta:
            ans_limit_delta = -24 * 365

        record_card = self.create_record_card(record_state_id=initial_state, applicant=applicant, create_worflow=True,
                                              ans_limit_delta=ans_limit_delta)

        if not resolution_type_id:
            resolution_type_id = mommy.make(ResolutionType, user_id="222", can_claim_inside_ans=True).pk

        WorkflowResolution.objects.create(workflow=record_card.workflow, resolution_type_id=resolution_type_id)

        if exists_previous_claim:
            self.create_record_card(claimed_from_id=record_card.pk)

        if claim_limit_exceded:
            RecordCardStateHistory.objects.create(record_card=record_card, group=record_card.responsible_profile,
                                                  previous_state_id=RecordState.PENDING_VALIDATE,
                                                  next_state_id=initial_state, user_id="22222", automatic=False)

            claim_days_limit = int(Parameter.get_parameter_by_key("DIES_PER_RECLAMAR", 60))
            RecordCardStateHistory.objects.filter(next_state__in=RecordState.CLOSED_STATES,
                                                  record_card_id=record_card.pk).update(
                created_at=timezone.now() - timedelta(days=claim_days_limit + 2))

        params = {"description": description, "reference": record_card.normalized_record_id}
        response = self.post(force_params=params)
        assert response.status_code == expected_response
        if expected_response == HTTP_201_CREATED:
            if initial_state not in RecordState.CLOSED_STATES or \
                    (resolution_type_id == ResolutionType.PROGRAM_ACTION and not ans_limit_delta):
                assert RecordCard.objects.get(pk=record_card.pk).citizen_alarm is True
                assert Comment.objects.get(record_card_id=record_card.pk, reason_id=Reason.CLAIM_CITIZEN_REQUEST)
            else:
                claim = RecordCard.objects.get(normalized_record_id=response.json()["reference"])
                record_card = RecordCard.objects.get(pk=record_card.pk)

                assert claim.record_state_id == RecordState.PENDING_VALIDATE
                assert claim.user_id == "WEB"
                assert claim.claims_number == 2
                assert claim.description == description
                assert claim.claimed_from_id == record_card.pk
                assert claim.citizen_web_alarm is True
                assert claim.alarm is True
                assert RecordCardAlarms(claim, record_card.responsible_profile).citizen_claim_web_alarm is True
                assert claim.normalized_record_id == "{}-02".format(record_card.normalized_record_id)

                assert record_card.claims_number == 2
                assert record_card.citizen_web_alarm is True
                assert record_card.alarm is True

    def test_public_claim_copy_files(self, tmpdir_factory):
        citizen = mommy.make(Citizen, blocked=False, user_id="2222")
        applicant = mommy.make(Applicant, citizen=citizen, user_id="2222")
        ans_limit_delta = -24 * 365
        record_card = self.create_record_card(record_state_id=RecordState.CLOSED, applicant=applicant,
                                              create_worflow=True, ans_limit_delta=ans_limit_delta)
        self.create_file(tmpdir_factory, record_card, 1)
        resolution_type_id = mommy.make(ResolutionType, user_id="222", can_claim_inside_ans=True).pk
        WorkflowResolution.objects.create(workflow=record_card.workflow, resolution_type_id=resolution_type_id)

        params = {"description": "description", "reference": record_card.normalized_record_id}
        with patch("record_cards.tasks.copy_record_files.delay") as mock_delay:
            response = self.post(force_params=params)
            assert response.status_code == HTTP_201_CREATED
            mock_delay.assert_called_once()

    def test_public_claim_autovalidate(self):
        citizen = mommy.make(Citizen, blocked=False, user_id="2222")
        applicant = mommy.make(Applicant, citizen=citizen, user_id="2222")
        ans_limit_delta = -24 * 365
        element_detail = self.create_element_detail(autovalidate_records=True, process_id=Process.EXTERNAL_PROCESSING)
        record_card = self.create_record_card(record_state_id=RecordState.CLOSED, applicant=applicant,
                                              create_worflow=True, ans_limit_delta=ans_limit_delta,
                                              element_detail=element_detail)
        resolution_type_id = mommy.make(ResolutionType, user_id="222", can_claim_inside_ans=True).pk
        WorkflowResolution.objects.create(workflow=record_card.workflow, resolution_type_id=resolution_type_id)

        params = {"description": "description", "reference": record_card.normalized_record_id}
        response = self.post(force_params=params)
        assert response.status_code == HTTP_201_CREATED
        claim = RecordCard.objects.get(normalized_record_id=response.json()["reference"])
        assert claim.record_state_id == RecordState.EXTERNAL_PROCESSING


class TestInputChannelListView(OpenAPIResourceListMixin, BasePublicAPITest):
    model_class = InputChannel
    delete_previous_objects = True

    path = "/input_channels/"

    def given_an_object(self):
        return mommy.make(InputChannel, user_id="2222")


class TestApplicantTypeListView(OpenAPIResourceListMixin, BasePublicAPITest):
    model_class = ApplicantType
    delete_previous_objects = True
    path = "/applicant_types/"

    def given_an_object(self):
        return mommy.make(ApplicantType, user_id="2222")


class TestRecordCardMobileCreateView(CreateThemesMixin, PostOperationMixin, AttachmentsTestApiMixin, BasePublicAPITest):
    path = "/mobile/record_cards/"

    @pytest.mark.parametrize(
        "add_description,add_element_detail,add_input_channel,add_applicant_type,add_recordresponse,add_ubication,"
        "add_citizen,add_social_entity,add_features,expected_response", (
                (True, True, True, True, True, True, True, False, False, HTTP_201_CREATED),
                (True, True, True, True, True, True, True, True, False, HTTP_400_BAD_REQUEST),
                (True, True, True, True, True, True, False, True, False, HTTP_201_CREATED),
                (True, True, True, True, True, True, False, False, False, HTTP_400_BAD_REQUEST),
                (True, True, True, True, True, True, True, False, True, HTTP_201_CREATED),
                (True, True, True, True, True, True, False, True, True, HTTP_201_CREATED),
                (False, True, True, True, True, True, True, False, False, HTTP_400_BAD_REQUEST),
                (True, False, True, True, True, True, True, False, False, HTTP_400_BAD_REQUEST),
                (True, True, False, True, True, True, True, False, False, HTTP_400_BAD_REQUEST),
                (True, True, True, False, True, True, True, False, False, HTTP_400_BAD_REQUEST),
                (True, True, True, True, False, True, True, False, False, HTTP_201_CREATED),
                (True, True, True, True, True, False, True, False, False, HTTP_400_BAD_REQUEST),
        ))
    def test_record_card_mobile_create_api(self, add_description, add_element_detail, add_input_channel,
                                           add_applicant_type, add_recordresponse, add_ubication, add_citizen,
                                           add_social_entity, add_features, expected_response):
        element_detail = self.create_element_detail()

        data, features_pk = self.set_data(add_description, add_element_detail, add_input_channel, add_applicant_type,
                                          add_recordresponse, add_ubication, add_citizen, add_social_entity,
                                          add_features, element_detail)

        get_public_features_pk = Mock(return_value=features_pk)
        get_public_mandatory_features_pk = Mock(return_value=[])
        with patch("themes.managers.ElementDetailFeatureManager.get_public_features_pk", get_public_features_pk):
            with patch("themes.managers.ElementDetailFeatureManager.get_public_mandatory_features_pk",
                       get_public_mandatory_features_pk):
                response = self.post(force_params=data)
                assert response.status_code == expected_response
                if expected_response == HTTP_201_CREATED:
                    record_card = RecordCard.objects.get(normalized_record_id=response.json()["normalized_record_id"])
                    assert record_card.element_detail == element_detail
                    if hasattr(record_card, "recordcardresponse"):
                        assert record_card.recordcardresponse.response_channel_id == ResponseChannel.EMAIL

    @staticmethod
    def set_data(add_description, add_element_detail, add_input_channel, add_applicant_type, add_recordresponse,
                 add_ubication, add_citizen, add_social_entity, add_features, element_detail):
        data = {}
        if add_description:
            data["description"] = "description"
        if add_element_detail:
            data["element_detail_id"] = element_detail.pk
        if add_input_channel:
            data["input_channel_id"] = mommy.make(InputChannel, user_id="222222").pk
        if add_applicant_type:
            data["applicant_type_id"] = mommy.make(ApplicantType, user_id="222222").pk
        if add_recordresponse:
            data["record_card_response"] = {
                "address_mobile_email": "test@test.com",
                "response_channel_id": ResponseChannel.EMAIL,
                "postal_code": "",
                "language": "ca"
            }
        if add_ubication:
            data["ubication"] = {
                "geocode_validation": "geocode_validation",
                "street": "street",
                "number": "number",
                "floor": 1,
                "door": "door",
                "latitude": "",
                "longitude": "",
                "district_id": District.LES_CORTS,
            }

        if add_citizen:
            data["citizen"] = {
                "name": "test",
                "first_surname": "test",
                "second_surname": "test",
                "doc_type": 0,
                "dni": "45122874O",
                "sex": "m",
                "district_id": District.CIUTAT_VELLA
            }

        if add_social_entity:
            data["social_entity"] = {
                "social_reason": "test",
                "cif": "O14539870",
                "contact": "test",
                "district_id": District.CIUTAT_VELLA
            }

        if add_features:
            feature = mommy.make(Feature, user_id="2222")
            ElementDetailFeature.objects.create(element_detail=element_detail, feature=feature, is_mandatory=True)
            features_pk = [feature.pk]
            data["features"] = [{"id": feature.pk, "value": "test"}]
        else:
            features_pk = []
        return data, features_pk

    def test_create_signal(self):
        signal = Mock(spec=Signal)
        element_detail = self.create_element_detail()

        data, features_pk = self.set_data(True, True, True, True, True, True, True, False, False, element_detail)
        with patch("record_cards.models.record_card_created", signal):
            get_public_features_pk = Mock(return_value=[])
            get_public_mandatory_features_pk = Mock(return_value=[])
            with patch("themes.managers.ElementDetailFeatureManager.get_public_features_pk", get_public_features_pk):
                with patch("themes.managers.ElementDetailFeatureManager.get_public_mandatory_features_pk",
                           get_public_mandatory_features_pk):
                    response = self.post(force_params=data)
                    assert response.status_code == HTTP_201_CREATED
                    record_card = RecordCard.objects.get(normalized_record_id=response.json()["normalized_record_id"])
                    signal.send_robust.assert_called_with(record_card=record_card, sender=RecordCard)

    def get_base_data(self, element_detail):
        data, features_pk = self.set_data(True, True, True, True, True, True, True, False, False, element_detail)
        return data

    @staticmethod
    def get_record_card(response):
        return RecordCard.objects.get(normalized_record_id=response["normalized_record_id"])

    @pytest.mark.parametrize("applicant_blocked,allowed_theme,expected_response", (
            (True, False, HTTP_400_BAD_REQUEST),
            (False, False, HTTP_201_CREATED),
            (True, True, HTTP_201_CREATED),
            (False, True, HTTP_201_CREATED)
    ))
    def test_api_applicant_blocked(self, applicant_blocked, allowed_theme, expected_response):
        if allowed_theme:
            element = self.create_element()
            no_block_theme_pk = int(Parameter.get_parameter_by_key("TEMATICA_NO_BLOQUEJADA", 392))
            element_detail = mommy.make(ElementDetail, user_id="22222", pk=no_block_theme_pk, element=element,
                                        process_id=Process.CLOSED_DIRECTLY,
                                        record_type_id=mommy.make(RecordType, user_id="user_id").pk)
        else:
            element_detail = self.create_element_detail()
        citizen = mommy.make(Citizen, user_id="2222", blocked=applicant_blocked)
        data = self.get_base_data(element_detail)
        data["citizen"]["dni"] = citizen.dni
        get_public_features_pk = Mock(return_value=[])
        get_public_mandatory_features_pk = Mock(return_value=[])
        with patch("themes.managers.ElementDetailFeatureManager.get_public_features_pk", get_public_features_pk):
            with patch("themes.managers.ElementDetailFeatureManager.get_public_mandatory_features_pk",
                       get_public_mandatory_features_pk):
                response = self.post(force_params=data)
                assert response.status_code == expected_response

    @pytest.mark.parametrize("organization,expected_response", (
            (True, HTTP_400_BAD_REQUEST),
            ("", HTTP_201_CREATED),
            ("organization", HTTP_201_CREATED)
    ))
    def test_record_organization(self, organization, expected_response):
        element_detail = self.create_element_detail()
        data = self.get_base_data(element_detail)
        data["organization"] = organization

        get_public_features_pk = Mock(return_value=[])
        get_public_mandatory_features_pk = Mock(return_value=[])
        with patch("themes.managers.ElementDetailFeatureManager.get_public_features_pk", get_public_features_pk):
            with patch("themes.managers.ElementDetailFeatureManager.get_public_mandatory_features_pk",
                       get_public_mandatory_features_pk):
                response = self.post(force_params=data)
                assert response.status_code == expected_response
                if expected_response == HTTP_201_CREATED:
                    record_card = RecordCard.objects.get(normalized_record_id=response.json()["normalized_record_id"])
                    assert record_card.organization == organization

    def test_bad_file(self):
        element_detail = self.create_element_detail()
        data = self.get_base_data(element_detail)
        data["pictures"] = [{
            "filename": "test.png",
            "data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGPwzO0EAAJCAUB17jgyAAAAC"
        }]

        get_public_features_pk = Mock(return_value=[])
        get_public_mandatory_features_pk = Mock(return_value=[])
        with patch("themes.managers.ElementDetailFeatureManager.get_public_features_pk", get_public_features_pk):
            with patch("themes.managers.ElementDetailFeatureManager.get_public_mandatory_features_pk",
                       get_public_mandatory_features_pk):
                response = self.post(force_params=data)
                assert response.status_code == HTTP_400_BAD_REQUEST

    def test_public_mobile_create_autovalidate(self):
        element_detail = self.create_element_detail(autovalidate_records=True, process_id=Process.EXTERNAL_PROCESSING)
        data = self.get_base_data(element_detail)
        get_public_features_pk = Mock(return_value=[])
        get_public_mandatory_features_pk = Mock(return_value=[])
        with patch("themes.managers.ElementDetailFeatureManager.get_public_features_pk", get_public_features_pk):
            with patch("themes.managers.ElementDetailFeatureManager.get_public_mandatory_features_pk",
                       get_public_mandatory_features_pk):
                response = self.post(force_params=data)
        assert response.status_code == HTTP_201_CREATED
        record_card = RecordCard.objects.get(normalized_record_id=response.json()["normalized_record_id"])
        assert record_card.record_state_id == RecordState.EXTERNAL_PROCESSING

    def test_public_mobile_internal_operator(self):
        element_detail = self.create_element_detail()
        data = self.get_base_data(element_detail)

        citizen = mommy.make(Citizen, dni="GUB", user_id="2222")
        default_applicant = mommy.make(Applicant, citizen=citizen, user_id="2222")

        InternalOperator.objects.create(document=data["citizen"]["dni"], applicant_type_id=data["applicant_type_id"],
                                        input_channel_id=data["input_channel_id"])

        get_public_features_pk = Mock(return_value=[])
        get_public_mandatory_features_pk = Mock(return_value=[])
        with patch("themes.managers.ElementDetailFeatureManager.get_public_features_pk", get_public_features_pk):
            with patch("themes.managers.ElementDetailFeatureManager.get_public_mandatory_features_pk",
                       get_public_mandatory_features_pk):
                response = self.post(force_params=data)
        assert response.status_code == HTTP_201_CREATED
        record_card = RecordCard.objects.get(normalized_record_id=response.json()["normalized_record_id"])
        assert record_card.request.applicant_id == default_applicant.pk
        assert record_card.recordcardresponse.response_channel_id == ResponseChannel.NONE

    def test_public_mobile_immediate_response(self):
        element_detail = self.create_element_detail(immediate_response=True)
        data = self.get_base_data(element_detail)

        get_public_features_pk = Mock(return_value=[])
        get_public_mandatory_features_pk = Mock(return_value=[])
        with patch("themes.managers.ElementDetailFeatureManager.get_public_features_pk", get_public_features_pk):
            with patch("themes.managers.ElementDetailFeatureManager.get_public_mandatory_features_pk",
                       get_public_mandatory_features_pk):
                response = self.post(force_params=data)
        assert response.status_code == HTTP_201_CREATED
        record_card = RecordCard.objects.get(normalized_record_id=response.json()["normalized_record_id"])
        assert record_card.recordcardresponse.response_channel_id == ResponseChannel.IMMEDIATE


@pytest.mark.django_db
class TestMessageHashCreateView(CreateRecordCardMixin, BasePublicAPITest):
    path = "/communications/{hash}/"

    @pytest.mark.parametrize("conversation_type,text_message,expected_response", (
            (Conversation.INTERNAL, "text_message", HTTP_404_NOT_FOUND),
            (Conversation.EXTERNAL, "text_message", HTTP_201_CREATED),
            (Conversation.EXTERNAL, "", HTTP_400_BAD_REQUEST),
            (Conversation.APPLICANT, "text_message", HTTP_201_CREATED),
            (Conversation.APPLICANT, "", HTTP_400_BAD_REQUEST),
    ))
    def test_create_message_by_hash(self, conversation_type, text_message, expected_response):
        record_card = self.create_record_card(pend_applicant_response=True)
        conversation = mommy.make(Conversation, is_opened=True, user_id="2222", type=conversation_type,
                                  record_card=record_card)
        message = mommy.make(Message, conversation=conversation, group=record_card.responsible_profile,
                             record_state_id=record_card.record_state_id, user_id="2222")
        response = self.create(force_params={"text": text_message, "hash": message.hash})
        assert response.status_code == expected_response
        if expected_response == HTTP_201_CREATED:
            assert ConversationUnreadMessagesGroup.objects.get(
                conversation=conversation, group=record_card.responsible_profile).unread_messages == 1

            if conversation_type in Conversation.HASH_TYPES:
                message = Message.objects.get(pk=message.pk)
                assert message.is_answered is True

            if conversation_type == Conversation.APPLICANT:
                record_card = RecordCard.objects.get(pk=record_card.pk)
                assert record_card.pend_applicant_response is False
                assert record_card.applicant_response is True

    def prepare_path(self, path, path_spec, force_params=None):
        """
        :param path: Relative URI of the operation.
        :param path_spec: OpenAPI spec as dict for part.
        :param force_params: Explicitly force params.
        :return: Path for performing a request to the given OpenAPI path.
        """
        path = path.format(hash=force_params["hash"])
        return "{}{}".format(self.base_api_path, path)

    def create(self, force_params=None):
        """
        Performs the create operation for this Resource.
        :param force_params: Force params for the request.
        :return: Operation result
        """
        return self.operation_test("post", self.path, self.spec()["paths"][self.path]["post"], force_params)

    def test_message_answered_hash(self):
        record_card = self.create_record_card(pend_applicant_response=True)
        conversation = mommy.make(Conversation, is_opened=True, user_id="2222", type=Conversation.EXTERNAL,
                                  record_card=record_card)
        message = mommy.make(Message, conversation=conversation, group=record_card.responsible_profile,
                             record_state_id=record_card.record_state_id, user_id="2222", is_answered=True)
        response = self.create(force_params={"text": "text message", "hash": message.hash})
        assert response.status_code == HTTP_409_CONFLICT


class TestParameterListATEVisibleView(OpenAPIResourceListMixin, BasePublicAPITest):
    model_class = Parameter
    delete_previous_objects = True
    path = "/parameters/"

    def given_an_object(self):
        return mommy.make(Parameter, user_id="2222", category=Parameter.WEB, show=True, visible=True)


class TestParameterDetailATEVisibleView(OpenAPIRetrieveMixin, BasePublicAPITest):
    lookup_field = "parameter"
    path_pk_param_name = "parameter"
    detail_path = "/parameters/{parameter}/"

    def given_an_object(self):
        parameter = Parameter.objects.get(parameter="ELEMENT_FAVORITS")
        return {"parameter": parameter.parameter}
