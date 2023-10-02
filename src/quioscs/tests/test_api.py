import pytest
from django.dispatch import Signal
from mock import Mock, patch
from model_mommy import mommy
from rest_framework.status import HTTP_201_CREATED, HTTP_400_BAD_REQUEST

from features.models import Feature
from iris_masters.models import InputChannel, District, Parameter, Process, RecordType, RecordState
from main.open_api.tests.base import BaseOpenAPITest, OpenAPIResourceListMixin, OpenAPIRetrieveMixin, PostOperationMixin
from public_api.tests.test_api import AttachmentsTestApiMixin
from record_cards.models import RecordCard, Citizen
from themes.models import ElementDetail
from themes.tests.utils import CreateThemesMixin
from communications.tests.utils import load_missing_data


class TestElementDetailQuioscs(CreateThemesMixin, OpenAPIResourceListMixin, BaseOpenAPITest):
    path = "/quioscs/details/"
    base_api_path = "/services/iris/api"
    model_class = ElementDetail
    delete_previous_objects = True

    def given_an_object(self):
        return self.create_element_detail()

    def test_list(self):
        load_missing_data()
        super().test_list(0)


class TestElementDetailQuioscsRetrieve(CreateThemesMixin, OpenAPIRetrieveMixin, BaseOpenAPITest):
    detail_path = "/quioscs/details/{id}/"
    base_api_path = "/services/iris/api"

    def given_an_object(self):
        element_detail = self.create_element_detail()
        return {"id": element_detail.pk}


@pytest.mark.django_db
class TestRecordCardCreateQuioscsView(CreateThemesMixin, PostOperationMixin, AttachmentsTestApiMixin, BaseOpenAPITest):
    path = "/quioscs/record_cards/"
    base_api_path = "/services/iris/api"

    @pytest.mark.parametrize(
        "description,document,email,create_element_detail,feature,feature_value,location,expected_response", (
                ("test", "46588745P", "test@test.com", True, True, "aaaaaa", True, HTTP_201_CREATED),
                ("", "46588745P", "test@test.com", True, True, "aaaaaa", True, HTTP_400_BAD_REQUEST),
                ("test", "46588745P", "", True, True, "aaaaaa", True, HTTP_201_CREATED),
                ("test", "46588745P", "test@test.com", False, True, "aaaaaa", True, HTTP_400_BAD_REQUEST),
                ("test", "46588745P", "test@test.com", True, False, "aaaaaa", True, HTTP_400_BAD_REQUEST),
                ("test", "46588745P", "test@test.com", True, True, "", True, HTTP_400_BAD_REQUEST),
                ("test", "46588745P", "test@test.com", True, True, "aaaaaa", False, HTTP_201_CREATED),
                ("test", "46588745P", "test@test.com", True, True, "aaaaaa", True, HTTP_201_CREATED),
                ("test", "", "test@test.com", True, True, "aaaaaa", True, HTTP_400_BAD_REQUEST),
        ))
    def test_record_card_create_quiosc(self, description, document, email, create_element_detail, feature,
                                       feature_value, location, expected_response):

        data = {
            "description": description,
            "document": document,
            "document_type": Citizen.PASS,
            "email": email,
        }

        if create_element_detail:
            data["element_detail_id"] = self.create_element_detail().pk

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
            data["features"] = [feature_data]
        if location:
            data["location"] = {"via_type": "Carrer", "geocode": 1, "street": "avel oeon mas", "number": "3",
                                "district": District.CIUTAT_VELLA}

        get_public_features_pk = Mock(return_value=features_pk_return)
        get_public_mandatory_features_pk = Mock(return_value=[])
        with patch("themes.managers.ElementDetailFeatureManager.get_public_features_pk", get_public_features_pk):
            with patch("themes.managers.ElementDetailFeatureManager.get_public_mandatory_features_pk",
                       get_public_mandatory_features_pk):
                response = self.post(force_params=data)
                assert response.status_code == expected_response
                if expected_response == HTTP_201_CREATED:
                    response = response.json()
                    record_card = RecordCard.objects.get(normalized_record_id=response["normalized_record_id"])
                    assert record_card.element_detail.description == response["element_detail"]
                    assert record_card.input_channel_id == InputChannel.QUIOSC
                    assert record_card.organization == "QUIOSCS"

    def test_create_signal(self):
        signal = Mock(spec=Signal)
        data = {
            "description": "description",
            "document": "458442521O",
            "document_type": Citizen.PASS,
            "email": "test@test.com",
            "element_detail_id": self.create_element_detail().pk,
            "location": {"via_type": "Carrer", "geocode": 1, "street": "avel oeon mas", "number": "3",
                         "district": District.CIUTAT_VELLA}
        }
        with patch("record_cards.models.record_card_created", signal):
            get_public_features_pk = Mock(return_value=[])
            get_public_mandatory_features_pk = Mock(return_value=[])
            with patch("themes.managers.ElementDetailFeatureManager.get_public_features_pk", get_public_features_pk):
                with patch("themes.managers.ElementDetailFeatureManager.get_public_mandatory_features_pk",
                           get_public_mandatory_features_pk):
                    response = self.post(force_params=data)
                    assert response.status_code == HTTP_201_CREATED
                    record_card = RecordCard.objects.get(pk=response.json()["id"])
                    signal.send_robust.assert_called_with(record_card=record_card, sender=RecordCard)

    @pytest.mark.parametrize(
        "geocode,via_type,street,number,district,requires_ubication,requires_ubication_district,"
        "expected_response", (
                ("1", "carrer", "street", "5A", District.EIXAMPLE, True, False, HTTP_201_CREATED),
                ("", "carrer", "street", "5A", District.EIXAMPLE, True, False, HTTP_201_CREATED),
                ("1", "", "street", "5A", District.EIXAMPLE, True, False, HTTP_400_BAD_REQUEST),
                ("1", "carrer", "", "5A", District.EIXAMPLE, True, False, HTTP_400_BAD_REQUEST),
                ("1", "carrer", "street", "", District.EIXAMPLE, True, False, HTTP_400_BAD_REQUEST),
                ("1", "carrer", "street", "5A", District.EIXAMPLE, False, True, HTTP_201_CREATED),
                ("1", "carrer", "street", "5A", None, False, True, HTTP_400_BAD_REQUEST),
        ))
    def test_record_ubication(self, geocode, via_type, street, number, district, requires_ubication,
                              requires_ubication_district, expected_response):
        ubication_data = {
            "geocode": geocode,
            "via_type": via_type,
            "street": street,
            "number": number,
            "district": district
        }

        element_detail = self.create_element_detail(requires_ubication=requires_ubication,
                                                    requires_ubication_district=requires_ubication_district)

        feature_object = mommy.make(Feature, user_id="2222")
        data = {
            "description": "description",
            "document": "47855369O",
            "document_type": Citizen.PASS,
            "email": "test@test.com",
            "element_detail_id": element_detail.pk,
            "location": ubication_data,
            "features": [{"id": feature_object.pk, "value": "2222"}]
        }

        features_pk_return = [feature_object.pk]
        get_public_features_pk = Mock(return_value=features_pk_return)
        get_public_mandatory_features_pk = Mock(return_value=[])
        with patch("themes.managers.ElementDetailFeatureManager.get_public_features_pk", get_public_features_pk):
            with patch("themes.managers.ElementDetailFeatureManager.get_public_mandatory_features_pk",
                       get_public_mandatory_features_pk):
                response = self.post(force_params=data)
                assert response.status_code == expected_response

    def get_base_data(self, element_detail):
        return {
            "description": "description",
            "document": "458442521O",
            "document_type": Citizen.PASS,
            "email": "test@test.com",
            "element_detail_id": element_detail.pk,
            "location": {"via_type": "Carrer", "geocode": 1, "street": "avel oeon mas", "number": "3",
                         "district": District.CIUTAT_VELLA}
        }

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
        citizen = mommy.make(Citizen, user_id="2222", blocked=applicant_blocked, doc_type=Citizen.PASS)
        data = self.get_base_data(element_detail)
        data["document"] = citizen.dni
        get_public_features_pk = Mock(return_value=[])
        get_public_mandatory_features_pk = Mock(return_value=[])
        with patch("themes.managers.ElementDetailFeatureManager.get_public_features_pk", get_public_features_pk):
            with patch("themes.managers.ElementDetailFeatureManager.get_public_mandatory_features_pk",
                       get_public_mandatory_features_pk):
                response = self.post(force_params=data)
                assert response.status_code == expected_response

    def test_quiosc_create_autovalidate(self):
        element_detail = self.create_element_detail(autovalidate_records=True, process_id=Process.EXTERNAL_PROCESSING)
        data = self.get_base_data(element_detail)

        get_public_features_pk = Mock(return_value=[])
        get_public_mandatory_features_pk = Mock(return_value=[])
        with patch("themes.managers.ElementDetailFeatureManager.get_public_features_pk", get_public_features_pk):
            with patch("themes.managers.ElementDetailFeatureManager.get_public_mandatory_features_pk",
                       get_public_mandatory_features_pk):
                response = self.post(force_params=data)
                assert response.status_code == HTTP_201_CREATED
        record_card = RecordCard.objects.get(pk=response.json()["id"])
        assert record_card.record_state_id == RecordState.EXTERNAL_PROCESSING
