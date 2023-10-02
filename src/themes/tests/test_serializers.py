import uuid
from datetime import date

import pytest
from django.conf import settings
from django.utils import timezone
from django.utils.functional import cached_property
from model_mommy import mommy
from rest_framework.exceptions import ValidationError

from features.models import Feature
from iris_masters.models import Application, District, Process, RecordState, ResponseChannel, RecordType
from main.test.mixins import FieldsTestSerializerMixin
from profiles.models import Group
from record_cards.tests.utils import SetGroupRequestMixin
from themes.models import ElementDetailFeature, ThemeGroup, ElementDetail, Zone

from themes.serializers import (ApplicationElementDetailSerializer, AreaSerializer, DerivationDistrictSerializer,
                                ElementDetailFeatureSerializer, ElementDetailListSerializer, ElementDetailSerializer,
                                ElementSerializer, KeyWordSerializer, DerivationDirectSerializer,
                                AreaListSerializer, ElementListSerializer, ElementDetailSearchSerializer,
                                AreaShortSerializer, ElementShortSerializer, ElementDetailShortSerializer,
                                ElementDetailFeatureListSerializer, ElementDetailCreateSerializer,
                                ElementDetailChangeSerializer, ThemeGroupSerializer, ElementDetailThemeGroupSerializer,
                                ElementDetailResponseChannelSerializer, ElementDetailCheckSerializer,
                                ElementDetailActiveSerializer, GroupProfileElementDetailSerializer,
                                ElementDetailDeleteRegisterSerializer, ElementDetailCopySerializer, ZoneSerializer,
                                DerivationPolygonSerializer, AreaDescriptionSerializer, ElementDescriptionSerializer,
                                ElementDetailDescriptionSerializer)
from themes.tests.utils import CreateThemesMixin
from iris_masters.tests.utils import load_missing_data_process, load_missing_data_districts
from communications.tests.utils import load_missing_data


@pytest.mark.django_db
class UniqueValidityTest:
    serializer_class = AreaSerializer
    unique_field = "description"

    def given_a_serializer(self, data):
        extra_data = self.get_extra_data()
        extra_data.update(data)
        return self.serializer_class(data=extra_data)

    def given_fields(self):
        return [f"{self.unique_field}_{lang}" for lang, name in settings.LANGUAGES]

    @pytest.mark.parametrize("description,existent,valid", (
            ("Aaaa", None, True),
            ("Aaaa", "Aaaa", False),
            ("Aaaa", "AaaA", False),
            ("Aaaa", "AaaAaaa", True),
    ))
    def test_serializer_unique_description(self, description, existent, valid):
        load_missing_data()
        load_missing_data_process()
        fields = self.given_fields()
        if existent:
            self.when_exists_previous_value(existent, fields)
        ser = self.given_a_serializer(data={
            field: description for field in fields
        })
        assert ser.is_valid() is valid
        assert isinstance(ser.errors, dict)
        if not valid:
            self.should_have_all_fields_as_errors(ser, fields)
        else:
            ser.save()

    def when_exists_previous_value(self, description, fields):
        initial_data = {field: description for field in fields}
        initial_data.update(self.get_extra_data())
        ser = self.given_a_serializer(data=initial_data)
        assert ser.is_valid(), "Your test has not valid data for creating previous elements {}".format(ser.errors)
        assert isinstance(ser.errors, dict)
        ser.save()

    def should_have_all_fields_as_errors(self, ser, fields):
        for field in fields:
            assert field in ser.errors, "All fields should be invalid"

    def get_extra_data(self):
        return {}


class TestThemeGroupSerializer(UniqueValidityTest):
    serializer_class = ThemeGroupSerializer

    def get_extra_data(self):
        return {"position": 10}

    def given_fields(self):
        return ["description"]

    @pytest.mark.parametrize("description,position,valid", (
            ("test", 10, True),
            ("", 10, False),
            ("test", None, False),
    ))
    def test_theme_group_serializer(self, description, position, valid):
        data = {
            "description": description,
            "position": position
        }
        ser = ThemeGroupSerializer(data=data)
        assert ser.is_valid() is valid, "ThemeGroup Serializer fails"
        assert isinstance(ser.errors, dict)


class TestAreaSerializer(UniqueValidityTest):
    serializer_class = AreaSerializer
    unique_field = "description"

    def get_extra_data(self):
        return {"favourite": True}


class TestElementSerializer(CreateThemesMixin, UniqueValidityTest):
    serializer_class = ElementSerializer
    unique_field = "description"

    @pytest.mark.parametrize("description,existent,valid", (
            ("Aaaa", None, True),
            ("Aaaa", "AaaAaaa", True),
    ))
    def test_serializer_unique_description(self, description, existent, valid):
        load_missing_data()
        load_missing_data_process()
        fields = self.given_fields()
        if existent:
            self.when_exists_previous_value(existent, fields)
        ser = self.given_a_serializer(data={
            field: description for field in fields
        })
        assert ser.is_valid() is valid
        assert isinstance(ser.errors, dict)
        if not valid:
            self.should_have_all_fields_as_errors(ser, fields)
        else:
            ser.save()

    @cached_property
    def area(self):
        return self.create_area()

    def get_extra_data(self):
        return {
            "area_id": self.area.pk,
            "is_favorite": True
        }

    def test_same_description_with_different_areas(self):
        description = "aaaa"
        fields = self.given_fields()
        self.when_exists_previous_value(description, fields)
        self.when_area_is_diferent()
        ser = self.given_a_serializer(data={
            field: description for field in fields
        })
        assert ser.is_valid(), "Elements of different areas can have the same description"
        assert isinstance(ser.errors, dict)

    def when_area_is_diferent(self):
        self.area = self.create_area()


class TestElementDetailSerializer(CreateThemesMixin, UniqueValidityTest):
    serializer_class = ElementDetailSerializer
    unique_field = "description"

    @pytest.mark.parametrize("description,existent,valid", (
            ("Aaaa", None, True),
            ("Aaaa", "Aaaa", False),
            ("Aaaa", "AaaA", False),
            ("Aaaa", "AaaAaaa", True),
    ))
    def test_serializer_unique_deleted_description(self, description, existent, valid):
        fields = self.given_fields()
        if existent:
            self.when_exists_previous_value(existent, fields)
            ElementDetail.objects.all().delete()
        ser = self.given_a_serializer(data={
            field: description for field in fields
        })
        assert ser.is_valid() is valid
        assert isinstance(ser.errors, dict)
        if not valid:
            self.should_have_all_fields_as_errors(ser, fields)

    @cached_property
    def element(self):
        return self.create_element()

    def test_same_description_with_different_elements(self):
        description = "aaaa"
        fields = self.given_fields()
        self.when_exists_previous_value(description, fields)
        self.when_element_is_different()
        ser = self.given_a_serializer(data={
            field: description for field in fields
        })
        assert ser.is_valid(), "Elements of different elements can have the same description"
        assert isinstance(ser.errors, dict)

    def test_keywords_element_detail(self):
        fields = self.given_fields()
        description = "aaaa"
        data = {field: description for field in fields}
        data.update({"keywords": ["test", "test2", "test3"]})
        ser = self.given_a_serializer(data=data)
        assert ser.is_valid(), "Element Detail Serializer fails with keywords"
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize("application", (5, 6, 7))
    def test_application_element_detail(self, application):
        fields = self.given_fields()
        description = "aaaa"
        data = {field: description for field in fields}
        mommy.make(Application, user_id="222", pk=application)
        data.update({"applications": [{"application": application, "favorited": True,
                                       "description": "new_description"}]})
        ser = self.given_a_serializer(data=data)
        assert ser.is_valid(), "Element Detail Serializer fails with applications"
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize("feature", (5, 6, 7))
    def test_element_detail_features(self, feature):
        fields = self.given_fields()
        description = "aaaa"
        data = {field: description for field in fields}
        mommy.make(Feature, user_id="222", pk=feature)
        data.update({"features": [{"feature": feature, "is_mandatory": True, "order": 2,
                                   "description": "new_description"}]})
        ser = self.given_a_serializer(data=data)
        assert ser.is_valid(), "Element Detail Serializer fails with attributes"
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize("theme_groups", (0, 1, 10))
    def test_element_detail_theme_groups(self, theme_groups):
        fields = self.given_fields()
        description = "aaaa"
        data = {field: description for field in fields}

        groups = []
        for _ in range(theme_groups):
            theme_group = mommy.make(ThemeGroup, user_id="222")
            groups.append({"theme_group": theme_group.pk})

        data.update({"theme_groups": groups})
        ser = self.given_a_serializer(data=data)
        assert ser.is_valid(), "Element Detail Serializer fails with theme groups"
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize("response_channel", (1, 2, 3))
    def test_response_channels_element_detail(self, response_channel):
        load_missing_data()
        fields = self.given_fields()
        description = "aaaa"
        data = {field: description for field in fields}
        data.update({"response_channels": [{"responsechannel": response_channel}]})
        ser = self.given_a_serializer(data=data)
        assert ser.is_valid(), "Element Detail Serializer fails with response channels"
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize("groups_number", (0, 1, 10))
    def test_element_detail_groups_profiles(self, groups_number):
        load_missing_data()
        fields = self.given_fields()
        description = "aaaa"
        data = {field: description for field in fields}

        groups = []
        for _ in range(groups_number):
            group = mommy.make(Group, user_id="222", profile_ctrl_user_id="2222")
            groups.append({"group": group.pk})

        data.update({"group_profiles": groups})
        ser = self.given_a_serializer(data=data)
        assert ser.is_valid(), "Element Detail Serializer fails with theme groups"
        assert isinstance(ser.errors, dict)

    def get_extra_data(self):
        return {
            "element_id": self.element.pk,
            "process": mommy.make(Process, id=Process.CLOSED_DIRECTLY).pk,
            "active": True,
            "active_date": timezone.now().date(),
            "visible": False,
            "visible_date": timezone.now().date(),
            "record_type_id": mommy.make(RecordType, user_id="22222").pk,
            "pend_commmunications": True,
            "allow_english_lang": True
        }

    def when_element_is_different(self):
        self.element = self.create_element()

    @pytest.mark.parametrize("immediate_response,external_protocol_id,valid", (
            (True, "", False),
            (True, "1235", True),
            (False, "35435", True),
            (False, "", True)
    ))
    def test_external_protocol_id_required(self, immediate_response, external_protocol_id, valid):
        fields = self.given_fields()
        description = "aaaa"
        data = {field: description for field in fields}
        data.update({"immediate_response": immediate_response, "external_protocol_id": external_protocol_id})
        ser = self.given_a_serializer(data=data)
        assert ser.is_valid() is valid, "Element Detail Serializer fails with attributes"
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize("process,external_email, valid", (
            (Process.EXTERNAL_PROCESSING_EMAIL, "", False),
            (Process.EXTERNAL_PROCESSING_EMAIL, "1235", False),
            (Process.EXTERNAL_PROCESSING_EMAIL, "test@test.com", True),
            (Process.CLOSED_DIRECTLY, "test@test.com", True),
            (Process.EXTERNAL_PROCESSING, "", True),
    ))
    def test_external_email(self, process, external_email, valid):
        load_missing_data_process()
        fields = self.given_fields()
        description = "aaaa"
        data = {field: description for field in fields}
        data.update({"process": process, "external_email": external_email, "allow_english_lang": False})
        ser = self.given_a_serializer(data=data)
        ser.instance = ElementDetail(pk=1000)
        assert ser.is_valid() is valid, 'Element Detail Serializer fails with attributes'
        assert isinstance(ser.errors, dict)

    @staticmethod
    def set_district_derivations(create_wrong_derivation=False):
        group_pk = mommy.make(Group, user_id='222', profile_ctrl_user_id='322').pk
        district_derivations = []
        for record_state in [RecordState.PENDING_VALIDATE, RecordState.IN_PLANING]:
            for district in District.objects.filter(allow_derivation=True):
                district_derivations.append({
                    "group": group_pk,
                    "district": district.pk,
                    "record_state": record_state
                })
        if create_wrong_derivation:
            for district in District.objects.all():
                district_derivations.append({
                    "group": group_pk,
                    "district": district.pk,
                    "record_state": RecordState.IN_RESOLUTION
                })
        return district_derivations

    @pytest.mark.parametrize("create_wrong_derivation,requires_ubication_district,valid", (
            (False, True, True),
            (True, True, False),
            (False, False, False),
    ))
    def test_element_district_derivations(self, create_wrong_derivation, requires_ubication_district, valid):
        load_missing_data()
        load_missing_data_process()
        load_missing_data_districts()
        element_detail = self.create_element_detail()
        data = ElementDetailSerializer(instance=element_detail).data
        data["district_derivations"] = self.set_district_derivations(create_wrong_derivation)
        data["requires_ubication_district"] = requires_ubication_district
        ser = ElementDetailSerializer(instance=element_detail, data=data)
        assert ser.is_valid() is valid, "Element Detail Serializer with district derivations"
        assert isinstance(ser.errors, dict)
        if create_wrong_derivation:
            assert "district_derivations" in ser.errors
            assert isinstance(ser.errors["district_derivations"], list)

    @pytest.mark.parametrize("create_wrong_derivation,valid", (
            (False, True),
            (True, False),
    ))
    def test_element_direct_derivations(self, create_wrong_derivation, valid):
        fields = self.given_fields()
        description = "aaaa"
        data = {field: description for field in fields}
        data["direct_derivations"] = [{
            "group": mommy.make(Group, user_id="222", profile_ctrl_user_id="322").pk,
            "record_state": RecordState.PENDING_VALIDATE
        }]
        if create_wrong_derivation:
            data["direct_derivations"].append({
                "group": mommy.make(Group, user_id="222", profile_ctrl_user_id="322").pk,
                "record_state": RecordState.PENDING_VALIDATE
            })
        ser = self.given_a_serializer(data=data)
        assert ser.is_valid() is valid, "Element Detail Serializer with district derivations"
        assert isinstance(ser.errors, dict)
        if create_wrong_derivation:
            assert "direct_derivations" in ser.errors
            assert isinstance(ser.errors["direct_derivations"], list)

    @pytest.mark.parametrize("create_direct,create_district,create_polygon,valid", (
            (True, False, False, True),
            (True, True, False, False),
            (True, False, True, False),
            (True, True, True, False),
            (False, True, True, True),
            (False, False, True, True),
            (False, True, False, True),
            (False, False, False, True),
    ))
    def test_element_combined_derivations_same_state(self, create_direct, create_district, create_polygon, valid):
        load_missing_data_districts()
        fields = self.given_fields()
        description = "aaaa"
        data = {field: description for field in fields}

        if create_direct:
            data["direct_derivations"] = [{
                "group": mommy.make(Group, user_id="222", profile_ctrl_user_id="322").pk,
                "record_state": RecordState.PENDING_VALIDATE
            }]

        if create_district:
            data["district_derivations"] = []
            data["requires_ubication_district"] = True
            for district in District.objects.filter(allow_derivation=True):
                data["district_derivations"].append({
                    "group": mommy.make(Group, user_id="222", profile_ctrl_user_id="322").pk,
                    "district": district.pk,
                    "record_state": RecordState.PENDING_VALIDATE
                })

        if create_polygon:
            data["polygon_derivations"] = [{
                "group": mommy.make(Group, user_id="222", profile_ctrl_user_id="322").pk,
                "record_state": RecordState.PENDING_VALIDATE,
                "zone": Zone.CARRCENT_PK,
                "polygon_code": "070"
            }]

        ser = self.given_a_serializer(data=data)
        assert ser.is_valid() is valid, "Element Detail Serializer with district derivations"
        assert isinstance(ser.errors, dict)
        if not valid:
            assert "direct_derivations" in ser.errors
            assert "district_derivations" in ser.errors
            assert "polygon_derivations" in ser.errors
            assert isinstance(ser.errors["direct_derivations"], list)
            assert isinstance(ser.errors["district_derivations"], list)
            assert isinstance(ser.errors["polygon_derivations"], list)

    @pytest.mark.parametrize("polygon_code,raise_validation_exception", (("070", True), (None, True)))
    def test_element_detail_polygon_derivations(self, polygon_code, raise_validation_exception):
        zone = Zone()
        zone.save()
        fields = self.given_fields()
        description = "aaaa"
        data = {field: description for field in fields}
        data["polygon_derivations"] = [{
            "polygon_code": polygon_code,
            "zone": Zone.objects.first().pk,
            "group": mommy.make(Group, user_id="222", profile_ctrl_user_id="222").pk
        }]
        ser = self.given_a_serializer(data=data)
        assert ser.is_valid(), "Element Detail Serializer with polygon derivations"
        assert isinstance(ser.errors, dict)
        try:
            ser.save()
            validation_exception = False
        except ValidationError:
            validation_exception = True
        assert validation_exception is raise_validation_exception

    @pytest.mark.parametrize("zones,valid", (
            ([Zone.CARRCENT_PK, Zone.CARRCENT_PK], True),
            ([Zone.CARRCENT_PK, Zone.SENYAL_VERTICAL_PK], False)
    ))
    def test_polygon_derivations_zones(self, zones, valid):
        fields = self.given_fields()
        description = "aaaa"
        data = {field: description for field in fields}
        data["polygon_derivations"] = [{
            "polygon_code": str(uuid.uuid4())[:10], "zone": zone, "record_state": RecordState.PENDING_VALIDATE,
            "group": mommy.make(Group, user_id="222", profile_ctrl_user_id="222").pk
        } for zone in zones]
        ser = self.given_a_serializer(data=data)
        assert ser.is_valid() is valid, "Element Detail Serializer fails with zones in polygon derivations"
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize("polygon_codes,valid", (
            (["070", "071", "072"], True),
            (["070", "071", "070"], False)
    ))
    def test_polygon_derivations_polygon_codes(self, polygon_codes, valid):
        fields = self.given_fields()
        description = "aaaa"
        data = {field: description for field in fields}
        data["polygon_derivations"] = [{
            "polygon_code": polygon_code, "zone": Zone.CARRCENT_PK, "record_state": RecordState.PENDING_VALIDATE,
            "group": mommy.make(Group, user_id="222", profile_ctrl_user_id="222").pk
        } for polygon_code in polygon_codes]
        ser = self.given_a_serializer(data=data)
        assert ser.is_valid() is valid, "Element Detail Serializer fails with polygon_codes in polygon derivations"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestElementDetailActiveSerializer(CreateThemesMixin):

    @pytest.mark.parametrize("initial_active,expected_active,activation_date,valid", (
            (False, True, None, True),
            (False, False, None, True),
            (False, None, None, False),
            (True, True, None, True),
            (True, False, None, True),
            (True, None, None, False),
            (False, True, "2019-01-01", True),
            (False, True, "2019-01-40", False),
            (True, True, "2019-01-01", True),
            (True, False, "2019-01-0", False),
    ))
    def test_element_detail_active_serializer(self, initial_active, expected_active, activation_date, valid):
        load_missing_data()
        load_missing_data_process()
        element_detail = self.create_element_detail(active=initial_active)
        data = {"id": element_detail.pk, "active": expected_active}
        if activation_date:
            data["activation_date"] = activation_date

        ser = ElementDetailActiveSerializer(instance=element_detail, data=data)
        assert ser.is_valid() is valid
        assert isinstance(ser.errors, dict)
        if valid:
            ser.save()
            element_detail = ElementDetail.objects.get(pk=element_detail.pk)
            assert element_detail.active is expected_active
            if activation_date:
                assert element_detail.activation_date == date(2019, 1, 1)

    @pytest.mark.parametrize("create_relationship", (True, False))
    def test_element_detail_active_serializer_response_channels(self, create_relationship):
        load_missing_data_process()
        load_missing_data()
        element_detail = self.create_element_detail(active=False, add_response_channels=create_relationship)
        data = {"id": element_detail.pk, "active": True, "activation_date": "2019-01-01"}
        ser = ElementDetailActiveSerializer(instance=element_detail, data=data)
        assert ser.is_valid() is create_relationship


class TestElementDetailCheckSerializer:

    @pytest.mark.parametrize(
        "can_save,mandatory_fields_missing,will_be_active,valid", (
                (True, True, True, True),
                (False, True, True, True),
                (None, True, True, False),
                (True, False, True, True),
                (True, None, True, False),
                (True, True, False, True),
                (True, True, None, False),
        ))
    def test_record_card_traceability_serializer(self, can_save, mandatory_fields_missing, will_be_active, valid):
        data = {
            "can_save": can_save,
            "mandatory_fields_missing": mandatory_fields_missing,
            "will_be_active": will_be_active,
        }
        ser = ElementDetailCheckSerializer(data=data)
        assert ser.is_valid() is valid
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestAreaListSerializer(CreateThemesMixin, FieldsTestSerializerMixin):
    serializer_class = AreaListSerializer
    data_keys = ["id", "description", "favourite", "description_es", "description_gl", "description_en", "order",
                 "can_delete", "icon_name"]

    def get_instance(self):
        return self.create_area()


@pytest.mark.django_db
class TestAreaShortSerializer(TestAreaListSerializer):
    serializer_class = AreaShortSerializer
    data_keys = ["id", "description", "order", "area_code", "query_area", "favourite", "description_es",
                 "description_gl", "description_en", "icon_name"]


@pytest.mark.django_db
class TestElementListSerializer(CreateThemesMixin, FieldsTestSerializerMixin):
    serializer_class = ElementListSerializer
    data_keys = ["id", "description", "area", "is_favorite", "description_es", "description_gl", "description_en",
                 "order", "can_delete", "is_query", "is_issue", "icon_name"]

    def get_instance(self):
        element = self.create_element()
        element.is_query = True
        element.is_issue = False
        return element


@pytest.mark.django_db
class TestElementShortSerializer(TestElementListSerializer):
    serializer_class = ElementShortSerializer
    data_keys = ["id", "description", "order", "element_code", "area", "is_favorite", "description_es",
                 "description_gl", "description_en", "icon_name"]


@pytest.mark.django_db
class TestElementDetailListSerializer(CreateThemesMixin, FieldsTestSerializerMixin):
    serializer_class = ElementDetailListSerializer
    data_keys = ["id", "short_description", "description", "pda_description", "app_description", "detail_code",
                 "rat_code", "similarity_hours", "similarity_meters", "validation_place_days",
                 "app_resolution_radius_meters", "sla_hours", "allow_multiderivation_on_reassignment", "order",
                 "element", "process", "allow_external", "custom_answer", "show_pda_resolution_time",
                 "requires_ubication", "requires_ubication_full_address", "requires_ubication_district",
                 "requires_citizen", "aggrupation_first", "immediate_response", "first_instance_response",
                 "requires_appointment", "allow_resolution_change", "validated_reassignable", "sla_allows_claims",
                 "allows_open_data", "allows_open_data_location", "allows_open_data_sensible_location", "allows_ssi",
                 "allows_ssi_location", "allows_ssi_sensible_location", "autovalidate_records", "record_type_id",
                 "keywords", "applications", "lopd", "head_text", "footer_text", "description_es", "description_gl",
                 "description_en", "head_text_es", "head_text_gl", "head_text_en", "app_description_es",
                 "app_description_gl", "app_description_en", "short_description_es", "short_description_gl",
                 "short_description_en", "footer_text_es", "footer_text_gl", "footer_text_en", "lopd_es", "lopd_gl",
                 "lopd_en", "active", "activation_date", "is_visible", "can_delete"]

    def get_instance(self):
        return self.create_element_detail()


@pytest.mark.django_db
class TestElementDetailChangeSerializer(CreateThemesMixin, FieldsTestSerializerMixin):
    serializer_class = ElementDetailChangeSerializer
    data_keys = ["id", "description", "description_es", "description_gl", "description_en"]

    def get_instance(self):
        return self.create_element_detail()


@pytest.mark.django_db
class TestElementDetailSearchSerializer(TestElementDetailListSerializer):
    serializer_class = ElementDetailSearchSerializer
    data_keys = ["id", "description", "detail_code", "order", "element", "process",
                 "external_protocol_id", "allow_external", "custom_answer", "requires_citizen", "immediate_response",
                 "first_instance_response", "record_type_id", "keywords", "applications",
                 "active", "activation_date", "is_visible", "visible", "visible_date", "description_gl",
                 "description_es", "description_en"]


@pytest.mark.django_db
class TestElementDetailShortSerializer(TestElementDetailListSerializer):
    serializer_class = ElementDetailShortSerializer
    data_keys = ["id", "short_description", "description", "pda_description", "app_description", "detail_code",
                 "rat_code", "similarity_hours", "similarity_meters", "lopd", "head_text",
                 "app_resolution_radius_meters", "sla_hours", "allow_multiderivation_on_reassignment", "order",
                 "element", "process", "allow_external", "custom_answer", "show_pda_resolution_time",
                 "requires_ubication", "requires_ubication_full_address", "requires_ubication_district",
                 "requires_citizen", "aggrupation_first", "immediate_response", "first_instance_response",
                 "requires_appointment", "allow_resolution_change", "footer_text", "validated_reassignable",
                 "sla_allows_claims", "autovalidate_records", "lopd_es", "lopd_gl", "lopd_en", "footer_text_es",
                 "footer_text_gl", "footer_text_en", "head_text_es", "head_text_gl", "head_text_en",
                 "short_description_es", "short_description_gl", "short_description_en", "description_es",
                 "description_gl", "description_en", "app_description_es", "app_description_gl", "app_description_en",
                 "validation_place_days", "active", "activation_date", "external_protocol_id"]


@pytest.mark.django_db
class TestElementDetailCreateSerializer(CreateThemesMixin):

    @pytest.mark.parametrize("description,add_element,add_process,detail_code,add_record_type,valid", (
            ("description", True, True, "Detail Code", True, True),
            (False, True, True, "Detail Code", True, False),
            ("description", False, True, "Detail Code", True, False),
            ("description", True, False, "Detail Code", True, False),
            ("description", True, True, "", True, True),
            ("description", True, True, "Detail Code", False, False),
    ))
    def test_element_detail_createserializer(self, description, add_element, add_process, detail_code, add_record_type,
                                             valid):
        data = {
            "description_gl": description,
            "description_es": description,
            "description_en": description
        }

        if add_element:
            data["element_id"] = self.create_element().pk
        if add_process:
            data["process"] = mommy.make(Process, id=Process.CLOSED_DIRECTLY).pk
        if detail_code:
            data["detail_code"] = "Detail Code"
        if add_record_type:
            data["record_type_id"] = mommy.make(RecordType, user_id="22222").pk

        ser = ElementDetailCreateSerializer(data=data)
        assert ser.is_valid() is valid, "ElementDetail Create serializer fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestElementDetailFeatureListSerializer(CreateThemesMixin, FieldsTestSerializerMixin):
    serializer_class = ElementDetailFeatureListSerializer
    data_keys = ["feature", "is_mandatory", "order", "enabled"]

    def get_instance(self):
        element_detail = self.create_element_detail()
        feature = mommy.make(Feature, deleted=None, user_id="222")
        return mommy.make(ElementDetailFeature, element_detail=element_detail, feature=feature, user_id="ssss")


class TestKeywordSerializer:

    @pytest.mark.parametrize("description", ("Aaaa", "bBbb", "ccCc", "dddD"))
    def test_keyword_serializer(self, description):
        ser = KeyWordSerializer(data={"description": description})
        assert ser.is_valid(), "Keyword serializer fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestApplicationElementDetailSerialiser:

    @pytest.mark.parametrize("application,favorited,valid", (
            (True, True, True),
            (True, False, True),
            (True, None, False),
            (None, False, False)
    ))
    def test_application_elementdetail_serializer(self, application, favorited, valid):
        if application:
            create_application = Application()
            create_application.save()
            application = Application.objects.first().pk
        ser = ApplicationElementDetailSerializer(data={"application": application, "favorited": favorited})
        assert ser.is_valid() is valid, "Application ElementDetail serializer fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestElementDetailFeatureSerializer:

    @pytest.mark.parametrize("feature,is_mandatory,valid", (
            (1, True, True),
            (2, False, True),
            (3, None, False),
            (None, False, False)
    ))
    def test_elementdetail_feature_serializer(self, feature, is_mandatory, valid):
        data = {"order": 5, "is_mandatory": is_mandatory}
        if feature:
            data["feature"] = mommy.make(Feature, user_id="222").pk
        ser = ElementDetailFeatureSerializer(data=data)
        assert ser.is_valid() is valid, "ElementDetail Feature serializer fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestElementDetailThemeGroupSerializer:

    @pytest.mark.parametrize("theme_group,valid", (
            (1, True),
            (None, False)
    ))
    def test_elementdetail_theme_group_serializer(self, theme_group, valid):
        if theme_group:
            mommy.make(ThemeGroup, user_id="222", pk=theme_group)
        ser = ElementDetailThemeGroupSerializer(data={"theme_group": theme_group})
        assert ser.is_valid() is valid, "ElementDetail Theme Group serializer fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestGroupProfileElementDetailSerializer:

    @pytest.mark.parametrize("create_group,valid", (
            (True, True),
            (False, False)
    ))
    def test_group_elementdetail_serializer(self, create_group, valid):
        data = {}
        if create_group:
            data["group"] = mommy.make(Group, user_id="222", profile_ctrl_user_id="2222").pk
        ser = GroupProfileElementDetailSerializer(data=data)
        assert ser.is_valid() is valid, "GroupProfile ElementDetail serializer fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestElementDetailResponseChannelSerializer:

    @pytest.mark.parametrize("response_channel,valid", (
            (ResponseChannel.EMAIL, True),
            (None, False)
    ))
    def test_elementdetail_feature_serializer(self, response_channel, valid):
        load_missing_data()
        ser = ElementDetailResponseChannelSerializer(data={"responsechannel": response_channel})
        assert ser.is_valid() is valid, "ElementDetail ResponseChannel serializer fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestDerivationDirectSerializer(CreateThemesMixin):

    @pytest.mark.parametrize("create_element_detail,create_profile,set_record_state,valid", (
            (True, True, True, True),
            (False, True, True, False),
            (True, False, True, False),
            (True, True, False, False),
            (False, False, True, False),
            (False, True, False, False),
            (True, False, False, False),
            (False, False, False, False)
    ))
    def test_multiderivation_serializer_serializer(self, create_element_detail, create_profile, set_record_state,
                                                   valid):
        load_missing_data()
        load_missing_data_process()
        if create_element_detail:
            element_detail_pk = self.create_element_detail().pk
        else:
            element_detail_pk = 0
        group_pk = mommy.make(Group, user_id="222", profile_ctrl_user_id="222").pk if create_profile else 0

        record_state_pk = RecordState.IN_RESOLUTION if set_record_state else None

        ser = DerivationDirectSerializer(data={"element_detail": element_detail_pk, "group": group_pk,
                                               "record_state": record_state_pk})
        assert ser.is_valid() is valid, "MultiDerivation serializer fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestDerivationDistrictSerializer(CreateThemesMixin):

    @pytest.mark.parametrize("create_element_detail,create_profile,district_pk,state_pk,valid", (
            (True, True, District.CIUTAT_VELLA, RecordState.PENDING_VALIDATE, True),
            (False, True, District.EIXAMPLE, RecordState.PENDING_VALIDATE, False),
            (True, False, District.LES_CORTS, RecordState.PENDING_VALIDATE, False),
            (False, False, District.SARRIA_SANTGERVASSI, RecordState.PENDING_VALIDATE, False),
            (True, True, 0, RecordState.PENDING_VALIDATE, False),
            (True, True, District.GRACIA, None, False)
    ))
    def test_derivation_district_serializer(self, create_element_detail, create_profile, district_pk, state_pk, valid):
        load_missing_data()
        load_missing_data_process()
        load_missing_data_districts()
        if create_element_detail:
            element_detail_pk = self.create_element_detail().pk
        else:
            element_detail_pk = 0
        if create_profile:
            group_pk = mommy.make(Group, user_id="222", profile_ctrl_user_id="222").pk
        else:
            group_pk = 0
        ser = DerivationDistrictSerializer(data={"element_detail": element_detail_pk, "group": group_pk,
                                                 "district": district_pk, "record_state": state_pk})
        assert ser.is_valid() is valid, "Derivation District serializer fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestElementDetailDeleteRegisterSerializer(CreateThemesMixin, SetGroupRequestMixin):

    @pytest.mark.parametrize("add_deleted_detail,add_reasignation_detail,only_open,valid", (
            (True, True, False, True),
            (True, False, False, False),
            (False, True, True, False),
            (False, False, True, False),
    ))
    def test_elementdetail_delete_register_serializer(self, add_deleted_detail, add_reasignation_detail, only_open,
                                                      valid):
        load_missing_data()
        load_missing_data_process()
        data = {"only_open": only_open}
        if add_deleted_detail:
            data["deleted_detail_id"] = self.create_element_detail().pk
        if add_reasignation_detail:
            data["reasignation_detail_id"] = self.create_element_detail().pk
        ser = ElementDetailDeleteRegisterSerializer(data=data)
        assert ser.is_valid() is valid, "ElementDetail Delete Register serializer fails"
        assert isinstance(ser.errors, dict)

    def test_same_detail(self):
        load_missing_data()
        load_missing_data_districts()
        load_missing_data_process()
        element_detail = self.create_element_detail()
        data = {
            "only_open": True,
            "deleted_detail_id": element_detail.pk,
            "reasignation_detail_id": element_detail.pk,
        }
        ser = ElementDetailDeleteRegisterSerializer(data=data)
        assert ser.is_valid() is False, "ElementDetail Delete Register serializer fails with same element detail"
        assert isinstance(ser.errors, dict)

    def test_save_group(self):
        load_missing_data()
        load_missing_data_process()
        data = {
            "only_open": True,
            "deleted_detail_id": self.create_element_detail().pk,
            "reasignation_detail_id": self.create_element_detail().pk,
        }
        group, request = self.set_group_request()
        ser = ElementDetailDeleteRegisterSerializer(data=data, context={"request": request})
        assert ser.is_valid() is True, "ElementDetail Delete Register serializer fails"
        instance = ser.save()
        assert instance.group == group


class TestElementDetailCopySerializer(CreateThemesMixin, UniqueValidityTest):
    serializer_class = ElementDetailCopySerializer

    @pytest.mark.parametrize("description_gl,description_en,description_es,element_id,valid", (
            ("description_gl", "description_en", "description_es", True, True),
            (None, "description_en", "description_es", True, False),
            ("description_gl", None, "description_es", True, False),
            ("description_gl", "description_en", None, True, False),
            ("description_gl", "description_en", "description_es", False, False),
    ))
    def test_element_detail_copy_serializer(self, description_gl, description_en, description_es, element_id, valid):
        load_missing_data()
        data = {"description_gl": description_gl, "description_en": description_en, "description_es": description_es}
        if element_id:
            data["element_id"] = self.create_element().pk

        ser = ElementDetailCopySerializer(data=data)
        assert ser.is_valid() is valid
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize("description,existent,valid", (
            ("Aaaa", None, True),
            ("Aaaa", "Aaaa", False),
            ("Aaaa", "AaaA", False),
            ("Aaaa", "AaaAaaa", True),
    ))
    def test_serializer_unique_description(self, description, existent, valid):
        load_missing_data()
        load_missing_data_process()
        fields = self.given_fields()
        if existent:
            self.when_exists_previous_value(existent, fields)
        ser = self.given_a_serializer(data={
            field: description for field in fields
        })
        assert ser.is_valid() is valid
        assert isinstance(ser.errors, dict)
        if not valid:
            self.should_have_all_fields_as_errors(ser, fields)
        else:
            self.create_element_detail(description=ser.validated_data["description_gl"])

    @cached_property
    def element(self):
        return self.create_element()

    def get_extra_data(self):
        return {"element_id": self.element.pk}

    def when_exists_previous_value(self, description, fields):
        initial_data = {field: description for field in fields}
        initial_data.update(self.get_extra_data())
        ser = self.given_a_serializer(data=initial_data)
        assert ser.is_valid(), "Your test has not valid data for creating previous elements {}".format(ser.errors)
        assert isinstance(ser.errors, dict)
        self.create_element_detail(description=ser.validated_data["description_gl"], element=self.element)


@pytest.mark.django_db
class TestZoneSerializer(FieldsTestSerializerMixin):
    serializer_class = ZoneSerializer
    data_keys = ["id", "description"]

    def get_instance(self):
        return mommy.make(Zone, user_id="zone")


@pytest.mark.django_db
class TestDerivationPolygonSerializer(CreateThemesMixin):

    @pytest.mark.parametrize("create_element_detail,create_group,add_zone,polygon_code,record_state,valid", (
            (True, True, True, "01", RecordState.PENDING_VALIDATE, True),
            (False, True, True, "01", RecordState.PENDING_VALIDATE, False),
            (True, False, True, "01", RecordState.PENDING_VALIDATE, False),
            (True, True, False, "01", RecordState.PENDING_VALIDATE, False),
            (True, True, True, "", RecordState.PENDING_VALIDATE, False),
            (True, True, True, "01", None, False),
    ))
    def test_derivation_polygon_serializer(self, create_element_detail, create_group, add_zone, polygon_code,
                                           record_state, valid):
        load_missing_data()
        load_missing_data_process()
        load_missing_data_districts()
        zone = Zone()
        zone.save()
        data = {"polygon_code": polygon_code, "record_state": record_state}
        if add_zone:
            data["zone"] = Zone.objects.first().pk
        if create_element_detail:
            data["element_detail"] = self.create_element_detail().pk
        else:
            data["element_detail"] = 0
        if create_group:
            data["group"] = mommy.make(Group, user_id="222", profile_ctrl_user_id="222").pk
        else:
            data["group"] = 0

        ser = DerivationPolygonSerializer(data=data)
        assert ser.is_valid() is valid, "Derivation Polygon serializer fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestAreaDescriptionSerializer(FieldsTestSerializerMixin, CreateThemesMixin):
    serializer_class = AreaDescriptionSerializer
    data_keys = ["id", "description", "description_gl", "description_es", "description_en", ]

    def get_instance(self):
        return self.create_area()


@pytest.mark.django_db
class TestElementDescriptionSerializer(FieldsTestSerializerMixin, CreateThemesMixin):
    serializer_class = ElementDescriptionSerializer
    data_keys = ["id", "description", "description_gl", "description_es", "description_en", "area"]

    def get_instance(self):
        return self.create_element()


@pytest.mark.django_db
class TestElementDetailDescriptionSerializer(FieldsTestSerializerMixin, CreateThemesMixin):
    serializer_class = ElementDetailDescriptionSerializer
    data_keys = ["id", "description", "description_gl", "description_es", "description_en", "element",
                 "external_protocol_id"]

    def get_instance(self):
        return self.create_element_detail()
