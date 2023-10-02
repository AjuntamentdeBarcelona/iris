import base64
import uuid

import pytest
from mock import Mock, patch
from model_mommy import mommy

from communications.models import Conversation, ConversationUnreadMessagesGroup
from features.models import Feature, ValuesType, Values
from iris_masters.models import (Process, Support, District, RecordState, RecordType, ResponseChannel, InputChannel,
                                 ApplicantType, Parameter)
from main.test.mixins import FieldsTestSerializerMixin
from main.utils import GALICIAN
from profiles.models import Group
from profiles.tests.utils import create_groups
from public_api.serializers import (AreaPublicSerializer, ElementDetailPublicSerializer,
                                    ElementDetailRetrievePublicSerializer, ElementDetailFeaturePublicSerializer,
                                    ElementPublicSerializer, RecordCardRetrievePublicSerializer,
                                    RecordCardFeaturesPublicSerializer, RecordCardSpecialFeaturesPublicSerializer,
                                    RecordCardCreatedPublicSerializer, RecordFeatureCreatePublicSerializer,
                                    UbicationCreatePublicSerializer, RecordCardCreatePublicSerializer,
                                    DistrictPublicSerializer, RecordStatePublicSerializer, UbicationPublicSerializer,
                                    RecordCardRetrieveStatePublicSerializer, UbicationSSIPublicSerializer,
                                    RecordCardSSIPublicSerializer, RecordTypePublicSerializer,
                                    ClaimResponseSerializer, ElementDetailLastUpdateSerializer,
                                    ResponseChannelPublicSerializer, InputChannelPublicSerializer,
                                    ApplicantTypePublicSerializer, CitizenPublicSerializer,
                                    SocialEntityPublicSerializer, UbicationMobileSerializer,
                                    RecordCardResponsePublicSerializer, RecordCardMobileCreatePublicSerializer,
                                    RecordCardMobileCreatedPublicSerializer, Base64AttachmentSerializer,
                                    RecordFilePublicSerializer, MessageHashCreateSerializer,
                                    MessageShortHashSerializer)
from public_api.tests.utils import set_custom_translations
from record_cards.models import (RecordCardFeatures, RecordCardSpecialFeatures, Ubication, Citizen, Applicant,
                                 ApplicantResponse, RecordFile, RecordCard)
from record_cards.tests.utils import CreateRecordCardMixin, SetGroupRequestMixin
from themes.models import Element, ElementDetail, ElementDetailFeature
from themes.tests.utils import CreateThemesMixin
from communications.tests.utils import load_missing_data
from iris_masters.tests.utils import (load_missing_data_process, load_missing_data_districts, load_missing_data_input,
                                      load_missing_data_applicant)


@pytest.mark.django_db
class TestFieldsAreaSerializer(CreateThemesMixin, FieldsTestSerializerMixin):
    serializer_class = AreaPublicSerializer
    data_keys = ["id", "description", "area_code", "areaIcon"]

    def get_instance(self):
        return self.create_area()


@pytest.mark.django_db
class TestElementFieldsSerializer(CreateThemesMixin, FieldsTestSerializerMixin):
    serializer_class = ElementPublicSerializer
    data_keys = ["element", "elementId", "area", "areaId", "areaIcon"]

    def get_instance(self):
        return self.create_element(is_favorite=True)


@pytest.mark.django_db
class TestElementDetailFieldsSerializer(CreateThemesMixin, FieldsTestSerializerMixin):
    serializer_class = ElementDetailPublicSerializer
    data_keys = ["detailId", "area", "areaId", "element", "elementId", "detail", "theme", "application", "recordType",
                 "head_text", "footer_text", "average_close_days", "recordIcon",
                 'iconName', 'requiresAppointment', 'headText',
                 "characteristics", "requiresUbication", "favourite", "description_gl", "description_es",
                 "description_en", "element_gl", "element_es", "element_en", "area_gl", "area_es", "area_en"]

    def get_instance(self):
        return self.create_element_detail()


@pytest.mark.django_db
class TestElementDetailRetrieveFieldsSerializer(CreateThemesMixin, FieldsTestSerializerMixin):
    serializer_class = ElementDetailRetrievePublicSerializer
    data_keys = ["detailId", "area", "areaId", "element", "elementId", "detail", "theme", "application",
                 "mandatoryFields", "mandatory_fields", "mandatory_drupal_fields", "characteristics", "head_text",
                 "footer_text", "recordType", "record_type_id", "immediate_response", "response_channels",
                 "external_process_type", "max_bytes_files_size", "average_close_days", "extension_files"]

    def get_instance(self):
        return self.create_element_detail()


@pytest.mark.django_db
class TestElementDetailFeatureFieldsSerializer(CreateThemesMixin, FieldsTestSerializerMixin):
    serializer_class = ElementDetailFeaturePublicSerializer
    data_keys = ["id", "type", "mandatory", "title", "special", "mask", "desc_mask", "options", "explanatory_text",
                 "order", "codename", "editable_for_citizen", "options_proxy", "description_gl", "description_es",
                 "description_en"]

    def get_instance(self):
        element_detail = self.create_element_detail()
        feature = mommy.make(Feature, user_id="2323")
        return mommy.make(ElementDetailFeature, element_detail=element_detail, feature=feature, user_id="2323")


@pytest.mark.django_db
class TestRecordCardFeaturesFieldsSerializer(CreateRecordCardMixin, FieldsTestSerializerMixin):
    serializer_class = RecordCardFeaturesPublicSerializer
    data_keys = ["id", "type", "title", "special", "mask", "options"]

    def get_instance(self):
        record_card = self.create_record_card()
        feature = mommy.make(Feature, user_id="2323")
        return mommy.make(RecordCardFeatures, record_card=record_card, feature=feature, user_id="2323")


@pytest.mark.django_db
class TestRecordCardSpecialFeaturesFieldsSerializer(CreateRecordCardMixin, FieldsTestSerializerMixin):
    serializer_class = RecordCardSpecialFeaturesPublicSerializer
    data_keys = ["id", "type", "title", "special", "mask", "options"]

    def get_instance(self):
        record_card = self.create_record_card()
        feature = mommy.make(Feature, user_id="2323")
        return mommy.make(RecordCardSpecialFeatures, record_card=record_card, feature=feature, user_id="2323")


@pytest.mark.django_db
class TestRecordCardRetrieveFieldsSerializer(CreateRecordCardMixin, FieldsTestSerializerMixin):
    serializer_class = RecordCardRetrievePublicSerializer
    data_keys = ["incidenceId", "code", "stateId", "state", "comments", "transaction", "task", "characteristics",
                 "location", "pictures", "average_close_days", "close_cancel_date", "address_mobile_email"]

    def get_instance(self):
        return self.create_record_card(create_record_card_response=True)


@pytest.mark.django_db
class TestRecordCardCreatedFieldsSerializer(CreateRecordCardMixin, FieldsTestSerializerMixin):
    serializer_class = RecordCardCreatedPublicSerializer
    data_keys = ["incidenceId", "pictures", "text_es", "text_en", "text_gl"]

    def get_instance(self):
        return self.create_record_card()


@pytest.mark.django_db
class TestRecordFilePublicSerializerFieldsSerializer(CreateRecordCardMixin, FieldsTestSerializerMixin):
    serializer_class = RecordFilePublicSerializer
    data_keys = ["pictureId", "filename"]

    def test_serializer(self, test_file):
        load_missing_data()
        load_missing_data_process()
        _, request = self.set_group_request()
        ser = self.get_serializer_class()(instance=self.get_instance(test_file), context={'request': request})
        assert len(ser.data.keys()) == self.get_keys_number()
        for data_key in self.data_keys:
            assert data_key in ser.data, f'Required {data_key} not present in serializer data'

    def get_instance(self, test_file):
        record = self.create_record_card()
        return RecordFile.objects.create(record_card=record, file=test_file.name, filename=test_file.name)


@pytest.mark.django_db
class TestRecordFeatureCreatePublicSerializer:

    def test_serializer_feature_novalues_type(self):
        feature = mommy.make(Feature, user_id="2222", values_type=None)
        data = {
            "id": feature.id,
            "value": "987456321"
        }
        ser = RecordFeatureCreatePublicSerializer(data=data)
        assert ser.is_valid() is True
        assert isinstance(ser.errors, dict)

    def test_serializer_feature_values_type_value_id(self):
        values_type = mommy.make(ValuesType, user_id="222")
        value = mommy.make(Values, user_id="222", values_type=values_type)

        feature = mommy.make(Feature, user_id="2222", values_type=values_type)
        data = {
            "id": feature.id,
            "value": value.pk
        }
        ser = RecordFeatureCreatePublicSerializer(data=data)
        assert ser.is_valid() is True
        assert isinstance(ser.errors, dict)

    def test_serializer_feature_values_type_value_description(self):
        values_type = mommy.make(ValuesType, user_id="222")
        value = mommy.make(Values, user_id="222", values_type=values_type)

        feature = mommy.make(Feature, user_id="2222", values_type=values_type)
        data = {
            "id": feature.id,
            "value": value.description
        }
        ser = RecordFeatureCreatePublicSerializer(data=data)
        assert ser.is_valid() is True
        assert isinstance(ser.errors, dict)

    def test_serializer_feature_values_type_wrong_value(self):
        values_type = mommy.make(ValuesType, user_id="222")
        mommy.make(Values, user_id="222", values_type=values_type)

        feature = mommy.make(Feature, user_id="2222", values_type=values_type)
        data = {
            "id": feature.id,
            "value": "asdadsasa"
        }
        ser = RecordFeatureCreatePublicSerializer(data=data)
        assert ser.is_valid() is False
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestUbicationCreatePublicSerializer(CreateThemesMixin):

    @pytest.mark.parametrize(
        "ubication_id,latitude,longitude,geocode,address,number,district,add_element_detail,requires_ubication,"
        "requires_ubication_district,valid", (
                (1, "1.222", "1.4675", 1, "c/street", "5A", District.EIXAMPLE, True, True, False, True),
                (None, "1.222", "1.4675", 1, "c/street", "5A", District.EIXAMPLE, True, True, False, True),
                (None, "", "1.4675", 1, "c/street", "5A", District.EIXAMPLE, True, True, False, True),
                (None, "1.222", "", 1, "c/street", "5A", District.EIXAMPLE, True, True, False, True),
                (None, "1.222", "1.4675", None, "c/street", "5A", District.EIXAMPLE, True, True, False, True),
                (None, "1.222", "1.4675", None, "c/street", "5A", District.EIXAMPLE, True, False, True, True),
                (None, "1.222", "1.4675", 1, None, "5A", District.EIXAMPLE, True, True, False, False),
                (None, "1.222", "1.4675", 1, "c/street", None, District.EIXAMPLE, True, True, False, False),
                (None, "1.2222222221222222222123", "1.4675", 1, "c/street", None, District.EIXAMPLE, True, True, False,
                 False),
                (None, "1.2222222221222222222123", "1.4675", 1, "c/street", None, District.EIXAMPLE, False, True, False,
                 False),
                (None, "1.222", "1.4675", None, "c/street", "5A", None, True, False, True, False),
        ))
    def test_serializer(self, ubication_id, latitude, longitude, geocode, address, number, district,
                        add_element_detail, requires_ubication, requires_ubication_district, valid):
        load_missing_data_districts()
        load_missing_data()
        load_missing_data_process()
        data = {
            "latitude": latitude,
            "longitude": longitude,
            "geocode": geocode,
            "address": address,
            "number": number,
            "district": district,
            "via_type": "Carrer",
            "floor": 5,
            "door": "",
        }

        if ubication_id:
            mommy.make(Ubication, user_id="2222", pk=ubication_id)
            data["id"] = ubication_id

        context = {}
        if add_element_detail:
            context["element_detail"] = self.create_element_detail(
                requires_ubication=requires_ubication, requires_ubication_district=requires_ubication_district)

        ser = UbicationCreatePublicSerializer(data=data, context=context)
        assert ser.is_valid() is valid
        assert isinstance(ser.errors, dict)


class AttachmentsTestSerializersMixin:

    @pytest.mark.parametrize("files_number,valid", ((0, True), (1, True), (3, True), (10, False)))
    def test_record_attachments(self, image_file, files_number, valid):
        load_missing_data()
        load_missing_data_districts()
        load_missing_data_process()
        element_detail = self.create_element_detail()
        data = self.get_base_data(element_detail)
        data["pictures"] = [{
            "filename": "test.png",
            "data": str(base64.b64encode(image_file.tobytes()))[2:-1]
        } for _ in range(files_number)]

        with patch("themes.managers.ElementDetailFeatureManager.get_public_features_pk", Mock(return_value=[])):
            with patch("themes.managers.ElementDetailFeatureManager.get_public_mandatory_features_pk",
                       Mock(return_value=[])):
                serializer = self.get_serializer_class()(data=data, context={'element_detail': element_detail})
                assert serializer.is_valid() is valid
                assert isinstance(serializer.errors, dict)

    def test_bad_base64file(self):
        load_missing_data()
        load_missing_data_districts()
        load_missing_data_process()
        element_detail = self.create_element_detail()
        data = self.get_base_data(element_detail)
        data["pictures"] = [{
            "filename": "test.png",
            "data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGPwzO0EAAJCAUB17jgyAAAAC"
        }]
        with patch("themes.managers.ElementDetailFeatureManager.get_public_features_pk", Mock(return_value=[])):
            with patch("themes.managers.ElementDetailFeatureManager.get_public_mandatory_features_pk",
                       Mock(return_value=[])):
                serializer = self.get_serializer_class()(data=data, context={'element_detail': element_detail})
                assert serializer.is_valid() is False
                assert isinstance(serializer.errors, dict)

    def get_base_data(self, element_detail):
        return {}

    def get_serializer_class(self):
        raise NotImplementedError


@pytest.mark.django_db
class TestRecordCardCreatePublicSerializer(CreateThemesMixin):

    @staticmethod
    def assert_serializer_validation(data, features_pk_return, db_element_detail, valid):
        get_public_features_pk = Mock(return_value=features_pk_return)
        get_public_mandatory_features_pk = Mock(return_value=[])
        with patch("themes.managers.ElementDetailFeatureManager.get_public_features_pk", get_public_features_pk):
            with patch("themes.managers.ElementDetailFeatureManager.get_public_mandatory_features_pk",
                       get_public_mandatory_features_pk):
                ser = RecordCardCreatePublicSerializer(data=data, context={"element_detail": db_element_detail})
                assert ser.is_valid() is valid
                assert isinstance(ser.errors, dict)

    def set_basic_data(self, db_element_detail):
        feature = mommy.make(Feature, user_id="2222")

        data = {
            "comments": "Test comments",
            "transaction": "Urgent",
            "detailId": db_element_detail.pk,
            "device": mommy.make(Support, user_id="2222").pk,
            "characteristics": [{
                "id": feature.pk,
                "value": "test"
            }],
            "location": {"latitude": "39.3556", "longitude": "36.54545", "geocode": 1,
                         "address": "avel oeon mas", "number": "3", "district": District.NOU_BARRIS,
                         "via_type": "Carrer", "floor": "4", "door": "A"},
            "authorization": False
        }
        return data, [feature.pk]

    @pytest.mark.parametrize(
        "element_detail,comments,transaction,support,applicant,feature,feature_value,location,valid", (
                (True, "Test comments", "Urgent", True, True, True, "value", True, True),
                (False, "Test comments", "Urgent", True, True, True, "value", True, False),
                (True, "", "Urgent", True, True, True, "value", True, False),
                (True, "Test comments", "", True, True, True, "value", True, False),
                (True, "Test comments", "Urgent", False, True, True, "value", True, True),
                (True, "Test comments", "Urgent", True, False, True, "value", True, False),
                (True, "Test comments", "Urgent", True, True, False, "value", True, False),
                (True, "Test comments", "Urgent", True, True, True, "", True, False),
                (True, "Test comments", "Urgent", True, True, True, "value", False, True),
        ))
    def test_basic_serializer(self, element_detail, comments, transaction, support, applicant, feature, feature_value,
                              location, valid):
        load_missing_data()
        load_missing_data_process()
        load_missing_data_districts()
        data = {
            "comments": comments,
            "transaction": transaction,
            "authorization": True
        }

        db_element_detail = None
        if element_detail:
            db_element_detail = self.create_element_detail()
            data["detailId"] = db_element_detail.pk
        if support:
            data["device"] = mommy.make(Support, user_id="2222").pk

        if applicant:
            citizen = mommy.make(Citizen, user_id="2222")
            data["applicant"] = mommy.make(Applicant, user_id="222", citizen=citizen).pk

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
            data["location"] = {"latitude": "39.3556", "longitude": "36.54545", "geocode": 1,
                                "address": "c/ avel oeon mas", "number": "3", "district": District.GRACIA}

        self.assert_serializer_validation(data, features_pk_return, db_element_detail, valid)

    @pytest.mark.parametrize("applicant,citizen_applicant,socialentity_applicant,add_email,valid", (
            (True, True, True, False, False),
            (True, False, True, False, False),
            (True, True, False, False, False),
            (False, True, True, False, False),
            (False, False, False, False, False),
            (True, False, False, False, True),
            (True, False, False, True, True),
            (False, True, False, False, True),
            (False, True, False, True, True),
            (False, False, True, False, True),
            (False, False, True, True, True),
    ))
    def test_serializer_applicants(self, applicant, citizen_applicant, socialentity_applicant, add_email, valid):

        load_missing_data()
        load_missing_data_process()
        load_missing_data_districts()
        db_element_detail = self.create_element_detail()
        data, features_pk_return = self.set_basic_data(db_element_detail)
        email = "testmail@test.com"

        if applicant:
            citizen = mommy.make(Citizen, user_id="2222")
            db_applicant = mommy.make(Applicant, user_id="222", citizen=citizen)
            data["applicant"] = db_applicant.pk
            if add_email:
                mommy.make(ApplicantResponse, user_id="2222", enabled=True, email=email, applicant=db_applicant,
                           response_channel_id=ResponseChannel.EMAIL)
        if citizen_applicant:
            data["nameCitizen"] = "test"
            data["firstSurname"] = "test"
            data["secondSurname"] = "test"
            data["typeDocument"] = Citizen.NIF
            data["numberDocument"] = "47855987P"
            data["district"] = District.CIUTAT_VELLA
            data["language"] = GALICIAN
            if add_email:
                data["email"] = email

        if socialentity_applicant:
            data["socialReason"] = "test"
            data["contactPerson"] = "test"
            data["cif"] = "G07148612"
            data["language"] = GALICIAN
            if add_email:
                data["email"] = email

        self.assert_serializer_validation(data, features_pk_return, db_element_detail, valid)

    @pytest.mark.parametrize(
        "name,first_surname,second_surname,document_type,document_number,birth_year,sex,district,language,valid", (
                ("test", "test", "test", Citizen.NIF, "47855987P", 1952, Citizen.FEMALE, District.GRACIA,
                 GALICIAN, True),
                ("test", "test", "", Citizen.NIF, "47855987P", 1952, Citizen.FEMALE, District.GRACIA, GALICIAN, True),
                ("", "test", "", Citizen.NIF, "47855987P", 1952, Citizen.FEMALE, District.GRACIA, GALICIAN, False),
                ("test", "", "", Citizen.NIF, "47855987P", 1952, Citizen.FEMALE, District.GRACIA, GALICIAN, False),
                ("test", "test", "test", None, "47855987P", 1952, Citizen.FEMALE, District.GRACIA, GALICIAN, False),
                ("test", "test", "test", Citizen.NIE, "", 1952, Citizen.FEMALE, District.GRACIA, GALICIAN, False),
                ("test", "test", "test", Citizen.NIE, "47855438O", 1852, Citizen.FEMALE, District.GRACIA, GALICIAN,
                 False),
                ("test", "test", "test", Citizen.NIE, "47855438O", 1952, None, District.GRACIA, GALICIAN, True),
                ("test", "test", "test", Citizen.NIE, "47855438O", 1952, Citizen.FEMALE, None, GALICIAN, False),
                ("test", "test", "test", Citizen.NIE, "47855438O", 1952, Citizen.FEMALE, District.GRACIA, None, False),
                ("test", "test", "test", Citizen.NIE, "47855438O", None, Citizen.FEMALE, District.GRACIA,
                 GALICIAN, True),
        ))
    def test_serializer_citizen_applicant(self, name, first_surname, second_surname, document_type, document_number,
                                          birth_year, sex, district, language, valid):
        load_missing_data()
        load_missing_data_process()
        load_missing_data_districts()
        db_element_detail = self.create_element_detail()
        data, features_pk_return = self.set_basic_data(db_element_detail)
        data["nameCitizen"] = name
        data["firstSurname"] = first_surname
        data["secondSurname"] = second_surname
        data["typeDocument"] = document_type
        data["numberDocument"] = document_number
        data["birthYear"] = birth_year
        data["sex"] = sex
        data["district"] = district
        data["language"] = language

        self.assert_serializer_validation(data, features_pk_return, db_element_detail, valid)

    @pytest.mark.parametrize("social_reason, contact_person, cif, district, language, valid", (
            ("test", "test", "G07148612", District.GRACIA, GALICIAN, True),
            ("", "test", "G07148612", District.GRACIA, GALICIAN, False),
            ("test", "", "G07148612", District.GRACIA, GALICIAN, False),
            ("test", "test", "", District.GRACIA, GALICIAN, False),
            ("test", "test", "G07148612", None, GALICIAN, True),
            ("test", "test", "G07148612", District.GRACIA, None, False),
    ))
    def test_serializer_socialentity_applicant(self, social_reason, contact_person, cif, district, language, valid):
        load_missing_data()
        load_missing_data_process()
        load_missing_data_districts()
        db_element_detail = self.create_element_detail()
        data, features_pk_return = self.set_basic_data(db_element_detail)
        data["socialReason"] = social_reason
        data["contactPerson"] = contact_person
        data["cif"] = cif
        data["district"] = district
        data["language"] = language

        self.assert_serializer_validation(data, features_pk_return, db_element_detail, valid)

    @pytest.mark.parametrize("transaction,device,characteristics,location", (
            (True, True, True, True),
            (False, True, True, True),
            (True, False, True, True),
            (True, True, False, True),
            (True, True, True, False),
            (False, False, True, True),
            (True, True, False, False),
            (False, False, False, False),
    ))
    def test_serializer_no_required_fields(self, transaction, device, characteristics, location):
        load_missing_data()
        load_missing_data_process()
        load_missing_data_districts()
        element = mommy.make(Element, user_id="20", element_code="empty", element__area__area_code="empty2",
                             area__user_id="20")
        element_detail = mommy.make(ElementDetail, short_description=uuid.uuid4(), description=uuid.uuid4(),
                                    element=element, user_id="222", process_id=Process.CLOSED_DIRECTLY)
        data = {
            "comments": "Test comments",
            "detailId": element_detail.pk,
            "authorization": True
        }

        if transaction:
            data["transaction"] = "Urgent"
        if device:
            data["device"] = mommy.make(Support, user_id="2222").pk
        if characteristics:
            feature = mommy.make(Feature, user_id="2222")
            ElementDetailFeature.objects.create(element_detail=element_detail, feature=feature, is_mandatory=True)
            features_pk = [feature.pk]
            data["characteristics"] = [{"id": feature.pk, "value": "test"}]
        else:
            features_pk = []
        if location:
            data["location"] = {"latitude": "39.3556", "longitude": "36.54545", "geocode": 1,
                                "address": "c/ avel oeon mas", "number": "3"}

        citizen = mommy.make(Citizen, user_id="2222")
        data["applicant"] = mommy.make(Applicant, user_id="222", citizen=citizen).pk

        self.assert_serializer_validation(data, features_pk, element_detail, True)

    def get_base_data(self, element_detail):
        data, _ = self.set_basic_data(element_detail)
        data.pop("characteristics", None)
        data["nameCitizen"] = "test"
        data["firstSurname"] = "test"
        data["secondSurname"] = "test"
        data["typeDocument"] = Citizen.NIF
        data["numberDocument"] = "47855987P"
        data["district"] = District.CIUTAT_VELLA
        data["language"] = GALICIAN
        data["email"] = "test@test.com"
        return data

    def get_serializer_class(self):
        return RecordCardCreatePublicSerializer

    def test_required_ubication_by_element_detail(self):
        load_missing_data()
        load_missing_data_process()
        load_missing_data_districts()
        db_element_detail = self.create_element_detail(requires_ubication=True)
        citizen = mommy.make(Citizen, user_id="2222")

        data = {
            "comments": "comments",
            "transaction": "Urgent",
            "authorization": True,
            "detailId": db_element_detail.pk,
            "device": mommy.make(Support, user_id="2222").pk,
            "applicant": mommy.make(Applicant, user_id="222", citizen=citizen).pk
        }

        self.assert_serializer_validation(data, [], db_element_detail, False)


@pytest.mark.django_db
class TestDistrictPublicSerializer(FieldsTestSerializerMixin):
    serializer_class = DistrictPublicSerializer
    data_keys = ["id", "name"]

    def get_instance(self):
        return District.objects.get(pk=1)


@pytest.mark.django_db
class TestRecordStatePublicSerializer(FieldsTestSerializerMixin):
    serializer_class = RecordStatePublicSerializer
    data_keys = ["description", "pk"]

    def get_instance(self):
        return RecordState.objects.get(id=RecordState.IN_RESOLUTION)


@pytest.mark.django_db
class TestRecordCardRetrieveStatePublicSerializer(CreateRecordCardMixin, FieldsTestSerializerMixin):
    serializer_class = RecordCardRetrieveStatePublicSerializer
    data_keys = ["normalized_record_id", "record_state", "created_at", "can_be_claimed", "text_es", "text_en",
                 "text_gl", "close_cancel_date", "claim_record", "can_response_message"]

    def get_instance(self):
        return self.create_record_card()

    def test_returns_text_gl(self):
        gl_text = "(GL)"
        set_custom_translations(gl_text, "gl")
        ser = self.get_instanced_serializer()
        assert gl_text in ser.data["text_gl"]

@pytest.mark.django_db
class TestUbicationPublicSerializer(FieldsTestSerializerMixin):
    serializer_class = UbicationPublicSerializer
    data_keys = ["latitude", "longitude", "geocode", "address", "number", "district"]

    def get_instance(self):
        return mommy.make(Ubication, user_id="22222", district_id=District.CIUTAT_VELLA)


@pytest.mark.django_db
class TestSSIUbicationPublicSerializer(TestUbicationPublicSerializer):
    serializer_class = UbicationSSIPublicSerializer
    data_keys = ["via_type", "street", "number", "district", "neighborhood", "geocode_district_id", "neighborhood_id",
                 "statistical_sector", "xetrs89a", "yetrs89a"]


@pytest.mark.django_db
class TestRecordCardSSIPublicSerializer(CreateRecordCardMixin, FieldsTestSerializerMixin):
    serializer_class = RecordCardSSIPublicSerializer
    data_keys = ["id", "created_at", "area", "area_id", "element", "element_id", "element_detail", "element_detail_id",
                 "normalized_record_id", "record_state", "record_state_id", "record_type", "record_type_id",
                 "ubication", "start_date_process", "closing_date"]

    def get_instance(self):
        return self.create_record_card()


@pytest.mark.django_db
class TestRecordTypePublicSerializer(CreateRecordCardMixin, FieldsTestSerializerMixin):
    serializer_class = RecordTypePublicSerializer
    data_keys = ["id", "description"]

    def get_instance(self):
        return mommy.make(RecordType, user_id="2222222")


@pytest.mark.django_db
class TestClaimResponseSerializer(FieldsTestSerializerMixin):
    serializer_class = ClaimResponseSerializer
    data_keys = ["reference", "reason"]

    def get_instance(self):
        return {"reference": "AAA1244-02", "reason": "test reason"}


@pytest.mark.django_db
class TestElementDetailLastUpdate(CreateThemesMixin, FieldsTestSerializerMixin):
    serializer_class = ElementDetailLastUpdateSerializer
    data_keys = ["updated_at"]

    def get_instance(self):
        return self.create_element_detail()


@pytest.mark.django_db
class TestResponseChannelPublicSerializer(FieldsTestSerializerMixin):
    serializer_class = ResponseChannelPublicSerializer
    data_keys = ["id", "name"]

    def get_instance(self):
        return ResponseChannel.objects.get(pk=ResponseChannel.EMAIL)


@pytest.mark.django_db
class TestInputChannelPublicSerializer(FieldsTestSerializerMixin):
    serializer_class = InputChannelPublicSerializer
    data_keys = ["id", "description"]

    def test_serializer(self):
        load_missing_data_input()
        super().test_serializer()

    def get_instance(self):
        return InputChannel.objects.get(pk=InputChannel.ALTRES_CANALS)


@pytest.mark.django_db
class TestApplicantTypePublicSerializer(FieldsTestSerializerMixin):
    serializer_class = ApplicantTypePublicSerializer
    data_keys = ["id", "description"]

    def test_serializer(self):
        load_missing_data_applicant()
        super().test_serializer()

    def get_instance(self):
        return ApplicantType.objects.get(pk=ApplicantType.COLECTIUS)


@pytest.mark.django_db
class TestCitizenPublicSerializer:

    @pytest.mark.parametrize("name,first_surname,second_surname,sex,doc_type,dni,birth_year,district_id,valid", (
            ("test", "test", "test", "f", 0, "45644312O", 1955, 3, True),
            ("", "test", "test", "f", 0, "45644312O", 1955, 3, False),
            ("test", "", "test", "f", 0, "45644312O", 1955, 3, False),
            ("test", "test", "", "f", 0, "45644312O", 1955, 3, True),
            ("test", "test", "test", "f", 5, "45644312O", 1955, 3, False),
            ("test", "test", "test", "f", 0, "", 1955, 3, False),
            ("test", "test", "test", "f", 0, "45644312O", 1855, 3, False),
            ("test", "test", "test", "f", 0, "45644312O", 1955, 13, False),
            ("test", "test", "test", "rere", 0, "45644312O", 1955, 3, False),
            ("test", "test", "test", "·", 0, "45644312O", 1955, 3, False),
    ))
    def test_citizen_public_serializer(self, name, first_surname, second_surname, sex, doc_type, dni, birth_year,
                                       district_id, valid):
        load_missing_data()
        load_missing_data_process()
        load_missing_data_districts()
        data = {
            "name": name,
            "first_surname": first_surname,
            "second_surname": second_surname,
            "sex": sex,
            "doc_type": doc_type,
            "dni": dni,
            "birth_year": birth_year,
            "district_id": district_id
        }
        serializer = CitizenPublicSerializer(data=data)
        assert serializer.is_valid() is valid
        assert isinstance(serializer.errors, dict)


@pytest.mark.django_db
class TestSocialEntityPublicSerializer:

    @pytest.mark.parametrize("social_reason,cif,contact,district_id,valid", (
            ("test", "G87569847", "test", 4, True),
            ("", "G87569847", "test", 4, False),
            ("test", "", "test", 4, False),
            ("test", "G87569847", "", 4, False),
            ("test", "G87569847", "test", 14, False),
    ))
    def test_social_entity_public_serializer(self, social_reason, cif, contact, district_id, valid):
        data = {
            "social_reason": social_reason,
            "cif": cif,
            "contact": contact,
            "district_id": district_id,
        }
        load_missing_data()
        load_missing_data_process()
        load_missing_data_districts()
        serializer = SocialEntityPublicSerializer(data=data)
        assert serializer.is_valid() is valid
        assert isinstance(serializer.errors, dict)


@pytest.mark.django_db
class TestUbicationMobileSerializer(CreateThemesMixin):

    @pytest.mark.parametrize(
        "geocode_validation,street,number,floor,door,latitude,longitude,district_id,add_element_detail,"
        "requires_ubication,requires_ubication_district,valid", (
                ("geocode", "street", "street number", 1, "A", 32.222, 2.22, 3, True, True, False, True),
                ("", "street", "street number", 1, "A", 32.222, 2.22, 3, True, True, False, True),
                ("geocode", "", "street number", 1, "A", 32.222, 2.22, 3, True, True, False, False),
                ("geocode", "street", "", 1, "A", 32.222, 2.22, 3, True, True, False, False),
                ("geocode", "street", "street number", 1, "A", 32.222, 2.22, 3, True, True, False, True),
                ("geocode", "street", "street number", "", "A", 32.222, 2.22, 3, True, True, False, True),
                ("geocode", "street", "street number", 1, "", 32.222, 2.22, 3, True, True, False, True),
                ("geocode", "street", "street number", 1, "A", None, 2.22, 3, True, True, False, True),
                ("geocode", "street", "street number", 1, "A", 32.222, None, 3, True, True, False, True),
                ("geocode", "street", "street number", 1, "A", 32.222, 2.22, 15, True, True, False, False),
                ("geocode", "street", "street number", 1, "A", 32.222, 2.22, None, True, True, False, True),
                ("geocode", "street", "street number", 1, "A", 32.222, 2.22, None, True, False, True, False),
        ))
    def test_ubication_mobile_serializer(self, geocode_validation, street, number, floor, door, latitude, longitude,
                                         district_id, add_element_detail, requires_ubication,
                                         requires_ubication_district,
                                         valid):
        load_missing_data()
        load_missing_data_process()
        load_missing_data_districts()
        data = {
            "geocode_validation": geocode_validation,
            "street": street,
            "number": number,
            "floor": floor,
            "door": door,
            "stair": "stair",
            "latitude": latitude,
            "longitude": longitude,
            "district_id": district_id,
        }
        context = {}
        if add_element_detail:
            context["element_detail"] = self.create_element_detail(
                requires_ubication=requires_ubication, requires_ubication_district=requires_ubication_district)

        serializer = UbicationMobileSerializer(data=data, context=context)
        assert serializer.is_valid() is valid
        assert isinstance(serializer.errors, dict)


@pytest.mark.django_db
class TestRecordCardResponsePublicSerializer(CreateRecordCardMixin):

    @pytest.mark.parametrize(
        "address_mobile_email,response_channel_id,postal_code,language,add_record_card,immediate_response,valid", (
                ("test@test.com", ResponseChannel.EMAIL, "", "gl", False, False, True),
                ("", ResponseChannel.EMAIL, "", "gl", False, False, False),
                ("test@test.com", None, "", "gl", False, False, False),
                ("666888777", ResponseChannel.SMS, "", "gl", False, False, True),
                ("c/street 2", ResponseChannel.LETTER, "07001", "gl", False, False, True),
                ("test@test.com", ResponseChannel.EMAIL, "", "gl", True, False, True),
                ("", ResponseChannel.EMAIL, "", "gl", True, False, False),
                ("test@test.com", None, "", "gl", True, False, False),
                ("666888777", ResponseChannel.SMS, "", "gl", True, False, True),
                ("c/street 2", ResponseChannel.LETTER, "07001", "gl", True, False, True),
                ("966888777", ResponseChannel.TELEPHONE, "", "gl", True, False, False),
                ("test@test.com", ResponseChannel.EMAIL, "", "gl", True, True, True),
                ("666888777", ResponseChannel.SMS, "", "gl", True, True, False),
                ("test@test.com", ResponseChannel.EMAIL, "", "", False, False, False),
        ))
    def test_record_card_response_public_serializer(self, address_mobile_email, response_channel_id, postal_code,
                                                    language, add_record_card, immediate_response, valid):
        load_missing_data()
        data = {
            "address_mobile_email": address_mobile_email,
            "response_channel_id": response_channel_id,
            "postal_code": postal_code,
            "language": language
        }

        context = {}
        if add_record_card:
            theme_response_channels = [ResponseChannel.EMAIL, ResponseChannel.SMS, ResponseChannel.LETTER,
                                       ResponseChannel.NONE, ResponseChannel.IMMEDIATE]
            record_card = self.create_record_card(immediate_response=immediate_response,
                                                  theme_response_channels=theme_response_channels)
            data["record_card_id"] = record_card.pk
            context = {"record_card_check": True}

        serializer = RecordCardResponsePublicSerializer(data=data, context=context)

        assert serializer.is_valid() is valid
        assert isinstance(serializer.errors, dict)


@pytest.mark.django_db
class TestRecordCardMobileCreatePublicSerializer(CreateThemesMixin, AttachmentsTestSerializersMixin):

    @pytest.mark.parametrize(
        "add_description,add_element_detail,add_input_channel,add_applicant_type,add_recordresponse,add_ubication,"
        "add_citizen,add_social_entity,add_features,valid", (
                (True, True, True, True, True, True, True, False, False, True),
                (True, True, True, True, True, True, True, True, False, False),
                (True, True, True, True, True, True, False, True, False, True),
                (True, True, True, True, True, True, False, False, False, False),
                (True, True, True, True, True, True, True, False, True, True),
                (True, True, True, True, True, True, False, True, True, True),

                (False, True, True, True, True, True, True, False, False, False),
                (True, False, True, True, True, True, True, False, False, False),
                (True, True, False, True, True, True, True, False, False, False),
                (True, True, True, False, True, True, True, False, False, False),
                (True, True, True, True, True, False, True, False, False, False),
        ))
    def test_record_card_mobile_create_public_serializer(self, add_description, add_element_detail, add_input_channel,
                                                         add_applicant_type, add_recordresponse, add_ubication,
                                                         add_citizen, add_social_entity, add_features, valid):
        load_missing_data()
        load_missing_data_process()
        load_missing_data_districts()
        element_detail = self.create_element_detail()
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
                "language": "gl"
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
                "birth_year": 1987,
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

        get_public_features_pk = Mock(return_value=features_pk)
        get_public_mandatory_features_pk = Mock(return_value=[])
        with patch("themes.managers.ElementDetailFeatureManager.get_public_features_pk", get_public_features_pk):
            with patch("themes.managers.ElementDetailFeatureManager.get_public_mandatory_features_pk",
                       get_public_mandatory_features_pk):
                serializer = RecordCardMobileCreatePublicSerializer(data=data,
                                                                    context={'element_detail': element_detail})
                assert serializer.is_valid() is valid
                assert isinstance(serializer.errors, dict)

    def get_base_data(self, element_detail):
        data = {
            "description": "description",
            "element_detail_id": element_detail.pk,
            "input_channel_id": mommy.make(InputChannel, user_id="222222").pk,
            "applicant_type_id": mommy.make(ApplicantType, user_id="222222").pk,
            "record_card_response": {
                "address_mobile_email": "test@test.com",
                "response_channel_id": ResponseChannel.EMAIL,
                "postal_code": "",
                "language": "gl"
            },
            "citizen": {
                "name": "test",
                "first_surname": "test",
                "second_surname": "test",
                "doc_type": 0,
                "dni": "45122874O",
                "sex": "m",
                "birth_year": 1987,
                "district_id": District.CIUTAT_VELLA
            },
            "ubication": {
                "geocode_validation": "geocode_validation",
                "street": "street",
                "number": "number",
                "floor": 1,
                "door": "door",
                "latitude": "",
                "longitude": "",
                "district_id": District.LES_CORTS,
            }
        }
        return data

    def get_serializer_class(self):
        return RecordCardMobileCreatePublicSerializer

    @pytest.mark.parametrize("organization,valid", ((True, False), ("", True), ("organization", True)))
    def test_record_organization(self, organization, valid):
        load_missing_data()
        load_missing_data_process()
        load_missing_data_districts()
        element_detail = self.create_element_detail()
        data = self.get_base_data(element_detail)
        data["organization"] = organization

        with patch("themes.managers.ElementDetailFeatureManager.get_public_features_pk", Mock(return_value=[])):
            with patch("themes.managers.ElementDetailFeatureManager.get_public_mandatory_features_pk",
                       Mock(return_value=[])):
                serializer = self.get_serializer_class()(data=data, context={'element_detail': element_detail})
                assert serializer.is_valid() is valid
                assert isinstance(serializer.errors, dict)


@pytest.mark.django_db
class TestRecordCardMobileCreatedPublicSerializer(CreateRecordCardMixin, FieldsTestSerializerMixin):
    serializer_class = RecordCardMobileCreatedPublicSerializer
    data_keys = ["normalized_record_id", "text_es", "text_en", "text_gl"]

    def get_instance(self):
        return self.create_record_card()


@pytest.mark.django_db
class TestAttachmentSerializer:

    @pytest.mark.parametrize("filename,valid", (
            ("test.png", True),
            ("", False),
            ("testtesttesttesttesttesttesttesttestestesstesetstesestestestestesestestestes.png", False),
    ))
    def test_attachment_serializer(self, filename, valid):
        data = {
            "filename": filename,
            "data": "data_file"
        }
        ser = Base64AttachmentSerializer(data=data)
        assert ser.is_valid() is valid
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize("remove_png_from_allowed_extensions,valid", ((True, False), (False, True)))
    def test_file_extension(self, remove_png_from_allowed_extensions, valid):
        if remove_png_from_allowed_extensions:
            if not Parameter.objects.filter(parameter="EXTENSIONS_PERMESES_FITXERS"):
                parameter = Parameter(parameter="EXTENSIONS_PERMESES_FITXERS")
            else:
                parameter = Parameter.objects.get(parameter="EXTENSIONS_PERMESES_FITXERS")
            parameter.valor = "jpg,jpeg,pdf,docx,xls,odt,xlsx"
            parameter.save()
        data = {
            "filename": "test.png",
            "data": "data_file"
        }
        ser = Base64AttachmentSerializer(data=data)
        assert ser.is_valid() is valid
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestMessageHashCreateSerializer(CreateRecordCardMixin, SetGroupRequestMixin):

    @pytest.mark.parametrize("create_conversation,conversation_opened,record_state_id,message,valid", (
            (True, True, RecordState.PENDING_VALIDATE, "Text message", True),
            (True, False, RecordState.PENDING_VALIDATE, "Text message", False),
            (False, True, RecordState.PENDING_VALIDATE, "Text message", False),
            (True, True, None, "Text message", False),
            (True, True, RecordState.PENDING_VALIDATE, "", False),
    ))
    def test_validate_serializer(self, create_conversation, conversation_opened, record_state_id, message,
                                 valid):
        load_missing_data()
        if create_conversation:
            conversation_pk = mommy.make(
                Conversation, is_opened=conversation_opened, user_id="2222",
                record_card=self.create_record_card(),
                creation_group=mommy.make(Group, user_id="2222", profile_ctrl_user_id="ssssssss")).pk
        else:
            conversation_pk = None
        data = {
            "conversation_id": conversation_pk,
            "record_state_id": record_state_id,
            "text": message
        }
        _, request = self.set_group_request()
        ser = MessageHashCreateSerializer(data=data, context={"request": request})
        assert ser.is_valid() is valid
        assert isinstance(ser.errors, dict)

    def test_applicant_message_hash_alarm(self):
        load_missing_data()
        message_creator, request = self.set_group_request()
        record_card = self.create_record_card(responsible_profile=message_creator)
        conversation_pk = mommy.make(
            Conversation, is_opened=True, user_id="2222", record_card=record_card, type=Conversation.APPLICANT,
            creation_group=record_card.responsible_profile).pk

        data = {
            "conversation_id": conversation_pk,
            "record_state_id": RecordState.PENDING_VALIDATE,
            "text": "Text message"
        }

        ser = MessageHashCreateSerializer(data=data, context={"request": request})
        assert ser.is_valid() is True
        assert isinstance(ser.errors, dict)
        ser.save()
        ConversationUnreadMessagesGroup.objects.create(group=record_card.responsible_profile,
                                                       conversation_id=conversation_pk, unread_messages=3)
        record_card = RecordCard.objects.get(pk=record_card.pk)
        assert record_card.pend_applicant_response is False
        assert record_card.applicant_response is True
        assert record_card.alarm is True

    def test_external_hash_alarm(self):
        load_missing_data()
        dair, parent, soon, _, _, _ = create_groups()

        record_card = self.create_record_card(responsible_profile=parent)
        conversation_pk = mommy.make(
            Conversation, is_opened=True, user_id="2222", record_card=record_card, type=Conversation.EXTERNAL,
            creation_group=dair).pk

        data = {
            "conversation_id": conversation_pk,
            "record_state_id": RecordState.PENDING_VALIDATE,
            "text": "Text message"
        }

        message_creator, request = self.set_group_request(soon)

        internal_conversation_groups = Mock(return_value=[soon.id])
        with patch("communications.managers.ConversationManager.internal_conversation_groups",
                   internal_conversation_groups):
            ser = MessageHashCreateSerializer(data=data, context={"request": request})
            assert ser.is_valid() is True
            assert isinstance(ser.errors, dict)
            ser.save()
            ConversationUnreadMessagesGroup.objects.create(group=record_card.responsible_profile,
                                                           conversation_id=conversation_pk, unread_messages=3)
            record_card = RecordCard.objects.get(pk=record_card.pk)
            assert record_card.pend_response_responsible is False
            assert record_card.response_to_responsible is True
            assert record_card.alarm is True


@pytest.mark.django_db
class TestMessageShortHashSerializer:

    @pytest.mark.parametrize("message,valid", (("Text message", True), ("", False)))
    def test_validate_serializer(self, message, valid):
        ser = MessageShortHashSerializer(data={"text": message})
        assert ser.is_valid() is valid
        assert isinstance(ser.errors, dict)
