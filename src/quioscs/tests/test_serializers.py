import pytest
from mock import patch, Mock
from model_mommy import mommy

from features.models import Feature, Values, ValuesType, Mask
from iris_masters.models import District
from main.test.mixins import FieldsTestSerializerMixin
from public_api.tests.test_serializers import AttachmentsTestSerializersMixin
from quioscs.serializers import (ElementDetailQuioscsSerializer, RecordCardQuioscSerializer,
                                 RecordCardCreateQuioscsSerializer, UbicationQuioscsSerializer, ValuesQuioscSerializer,
                                 ValuesTypeQuioscSerializer, MaskQuioscSerializer, FeatureQuioscSerializer,
                                 ElementDetailFeatureQuioscSerializer)
from record_cards.models import Citizen
from record_cards.tests.utils import CreateRecordCardMixin
from themes.models import ElementDetailFeature
from themes.tests.utils import CreateThemesMixin
from communications.tests.utils import load_missing_data
from iris_masters.tests.utils import load_missing_data_process, load_missing_data_districts


@pytest.mark.django_db
class TestElementDetailQuioscsSerializer(CreateThemesMixin, FieldsTestSerializerMixin):
    serializer_class = ElementDetailQuioscsSerializer
    data_keys = ["id", "description", "area_id", "area_description", "element_id", "element_description",
                 "record_type", "features", "response_channels", "requires_ubication", "immediate_response"]

    def get_instance(self):
        return self.create_element_detail()


@pytest.mark.django_db
class TestRecordCardQuioscSerializer(CreateRecordCardMixin, FieldsTestSerializerMixin):
    serializer_class = RecordCardQuioscSerializer
    data_keys = ["id", "element_detail", "description", "normalized_record_id", "resolution_time"]

    def get_instance(self):
        return self.create_record_card(ans_limit_delta=100)


@pytest.mark.django_db
class TestRecordCardCreateQuioscsSerializer(CreateThemesMixin, AttachmentsTestSerializersMixin):

    @pytest.mark.parametrize("description,document,email,create_element_detail,feature,feature_value,location,valid", (
            ("test", "46588745P", "test@test.com", True, True, "aaaaaa", True, True),
            ("", "46588745P", "test@test.com", True, True, "aaaaaa", True, False),
            ("test", "46588745P", None, True, True, "aaaaaa", True, True),
            ("test", "46588745P", "test@test.com", False, True, "aaaaaa", True, False),
            ("test", "46588745P", "test@test.com", True, False, "aaaaaa", True, False),
            ("test", "46588745P", "test@test.com", True, True, "", True, False),
            ("test", "46588745P", "test@test.com", True, True, "aaaaaa", False, True),
            ("test", "", "test@test.com", True, True, "aaaaaa", False, False)
    ))
    def test_record_card_create_quiosc_view(self, description, document, email, create_element_detail, feature,
                                            feature_value, location, valid):
        load_missing_data()
        load_missing_data_districts()
        load_missing_data_process()
        context = {}

        data = {
            "description": description,
            "document": document,
            "document_type": Citizen.NIF,
            "email": email
        }

        if create_element_detail:
            element_detail = self.create_element_detail()
            data["element_detail_id"] = element_detail.pk
            context["element_detail"] = element_detail

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
                ser = RecordCardCreateQuioscsSerializer(data=data, context=context)
                assert ser.is_valid() is valid
                assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize(
        "geocode,via_type,street,number,district,add_element_detail,requires_ubication,"
        "requires_ubication_district,valid", (
                ("1", "carrer", "street", "5A", District.EIXAMPLE, True, True, False, True),
                ("", "carrer", "street", "5A", District.EIXAMPLE, True, True, False, True),
                ("1", "", "street", "5A", District.EIXAMPLE, True, True, False, False),
                ("1", "carrer", "", "5A", District.EIXAMPLE, True, True, False, False),
                ("1", "carrer", "street", "", District.EIXAMPLE, True, True, False, False),
                ("1", "carrer", "street", "5A", District.EIXAMPLE, True, False, True, True),
                ("1", "carrer", "street", "5A", None, True, False, True, False),
                ("1", "carrer", "street", "5A", District.EIXAMPLE, False, True, False, False),
        ))
    def test_record_ubication(self, geocode, via_type, street, number, district, add_element_detail, requires_ubication,
                              requires_ubication_district, valid):
        load_missing_data()
        load_missing_data_districts()
        load_missing_data_process()
        ubication_data = {
            "geocode": geocode,
            "via_type": via_type,
            "street": street,
            "number": number,
            "district": district
        }

        element_detail = self.create_element_detail(requires_ubication=requires_ubication,
                                                    requires_ubication_district=requires_ubication_district)

        context = {}
        if add_element_detail:
            context["element_detail"] = element_detail

        feature_object = mommy.make(Feature, user_id="2222")
        data = {
            "description": "description",
            "document_type": Citizen.NIF,
            "document": "45688744O",
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
                ser = RecordCardCreateQuioscsSerializer(data=data, context=context)
                assert ser.is_valid() is valid
                assert isinstance(ser.errors, dict)

    def get_base_data(self, element_detail):
        return {
            "description": "description",
            "document_type": Citizen.NIF,
            "document": "45688744O",
            "email": "test@test.com",
            "element_detail_id": element_detail.pk,
            "location": {
                "geocode": "geocode",
                "via_type": "via_type",
                "street": "street",
                "number": "number",
                "district": District.LES_CORTS
            },
            "features": []
        }

    def get_serializer_class(self):
        return RecordCardCreateQuioscsSerializer

    @pytest.mark.parametrize("document_type,valid", (
            (Citizen.NIF, True),
            (Citizen.NIE, True),
            (Citizen.PASS, True),
            (10, False),
    ))
    def test_document_type(self, document_type, valid):
        load_missing_data()
        load_missing_data_districts()
        load_missing_data_process()
        element_detail = self.create_element_detail()
        data = self.get_base_data(element_detail)
        data["document_type"] = document_type

        with patch("themes.managers.ElementDetailFeatureManager.get_public_features_pk", Mock(return_value=[])):
            with patch("themes.managers.ElementDetailFeatureManager.get_public_mandatory_features_pk",
                       Mock(return_value=[])):
                serializer = self.get_serializer_class()(data=data, context={"element_detail": element_detail})
                assert serializer.is_valid() is valid
                assert isinstance(serializer.errors, dict)

    def test_required_ubication_by_element_detail(self):
        load_missing_data()
        load_missing_data_districts()
        load_missing_data_process()
        db_element_detail = self.create_element_detail(requires_ubication=True)
        data = {
            "description": "description",
            "document_type": Citizen.NIF,
            "document": "45688744O",
            "email": "test@test.com",
            "element_detail_id": db_element_detail.pk,
            "features": []
        }

        with patch("themes.managers.ElementDetailFeatureManager.get_public_features_pk", Mock(return_value=[])):
            with patch("themes.managers.ElementDetailFeatureManager.get_public_mandatory_features_pk",
                       Mock(return_value=[])):
                ser = RecordCardCreateQuioscsSerializer(data=data, context={"element_detail": db_element_detail})
                assert ser.is_valid() is False
                assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestUbicationQuioscsSerializer(CreateThemesMixin):

    @pytest.mark.parametrize(
        "geocode,via_type,street,number,district,add_element_detail,requires_ubication,"
        "requires_ubication_district,valid", (
                ("1", "carrer", "street", "5A", District.EIXAMPLE, True, True, False, True),
                ("", "carrer", "street", "5A", District.EIXAMPLE, True, True, False, True),
                ("1", "", "street", "5A", District.EIXAMPLE, True, True, False, False),
                ("1", "carrer", "", "5A", District.EIXAMPLE, True, True, False, False),
                ("1", "carrer", "street", "", District.EIXAMPLE, True, True, False, False),
                ("1", "carrer", "street", "5A", District.EIXAMPLE, True, False, True, True),
                ("1", "carrer", "street", "5A", None, True, False, True, False),
                ("1", "carrer", "street", "5A", District.EIXAMPLE, False, True, False, False),
        ))
    def test_ubication_quioscs_serializer(self, geocode, via_type, street, number, district,
                                          add_element_detail, requires_ubication, requires_ubication_district, valid):
        load_missing_data()
        load_missing_data_districts()
        load_missing_data_process()
        data = {
            "geocode": geocode,
            "via_type": via_type,
            "street": street,
            "number": number,
            "district": district
        }

        context = {}
        if add_element_detail:
            context["element_detail"] = self.create_element_detail(
                requires_ubication=requires_ubication, requires_ubication_district=requires_ubication_district)

        ser = UbicationQuioscsSerializer(data=data, context=context)
        assert ser.is_valid() is valid
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestValuesQuioscSerializer(FieldsTestSerializerMixin):
    serializer_class = ValuesQuioscSerializer
    data_keys = ["id", "description", "description_es", "description_en", "description_gl"]

    def get_instance(self):
        values_type = mommy.make(ValuesType, user_id="222222")
        return mommy.make(Values, user_id="222222", values_type=values_type)


@pytest.mark.django_db
class TestValuesTypeQuioscSerializer(FieldsTestSerializerMixin):
    serializer_class = ValuesTypeQuioscSerializer
    data_keys = ["id", "description", "description_es", "description_en", "description_gl", "values"]

    def get_instance(self):
        values_type = mommy.make(ValuesType, user_id="222222")
        mommy.make(Values, user_id="222222", values_type=values_type)
        return values_type


@pytest.mark.django_db
class TestMaskQuioscSerializer(FieldsTestSerializerMixin):
    serializer_class = MaskQuioscSerializer
    data_keys = ["id", "description", "description_es", "description_en", "description_gl", "type"]

    def test_serializer(self):
        if not Mask.objects.filter(id=1):
            mask = Mask(id=1)
            mask.save()
        super().test_serializer()

    def get_instance(self):
        return Mask.objects.get(pk=Mask.ANY_CHAR)


@pytest.mark.django_db
class TestFeatureQuioscSerializer(FieldsTestSerializerMixin):
    serializer_class = FeatureQuioscSerializer
    data_keys = ["id", "description", "description_es", "description_en", "description_gl", "values_type", "mask",
                 "explanatory_text", "explanatory_text_gl", "explanatory_text_es", "explanatory_text_en"]

    def test_serializer(self):
        if not Mask.objects.filter(id=4):
            mask = Mask(id=4)
            mask.save()
        super().test_serializer()

    def get_instance(self):
        values_type = mommy.make(ValuesType, user_id="222222")
        mommy.make(Values, user_id="222222", values_type=values_type)
        return mommy.make(Feature, user_id="2222", values_type=values_type, mask_id=Mask.INTEGER)


@pytest.mark.django_db
class TestElementDetailFeatureQuioscSerializer(CreateThemesMixin, FieldsTestSerializerMixin):
    serializer_class = ElementDetailFeatureQuioscSerializer
    data_keys = ["feature", "order", "is_mandatory"]
    feature_keys = ["id", "description", "description_es", "description_en", "description_gl", "values_type", "mask",
                    "explanatory_text", "explanatory_text_gl", "explanatory_text_es", "explanatory_text_en"]

    def get_instance(self):
        values_type = mommy.make(ValuesType, user_id="222222")
        mommy.make(Values, user_id="222222", values_type=values_type)
        feature = mommy.make(Feature, user_id="2222", values_type=values_type, mask_id=Mask.INTEGER)
        element_detail = self.create_element_detail()
        return ElementDetailFeature.objects.create(element_detail=element_detail, feature=feature)

    def test_serializer(self):
        load_missing_data()
        load_missing_data_process()
        if not Mask.objects.filter(id=4):
            mask = Mask(id=4)
            mask.save()
        _, request = self.set_group_request()
        ser = self.get_serializer_class()(instance=self.get_instance(), context={"request": request})
        assert len(ser.data.keys()) == self.get_keys_number()
        for data_key in self.data_keys:
            assert data_key in ser.data, f"Required {data_key} not present in serializer data"
        for feature_key in self.feature_keys:
            assert feature_key in ser.data["feature"], f"Required {feature_key} not present in serializer data"
