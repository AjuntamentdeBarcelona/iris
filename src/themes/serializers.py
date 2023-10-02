from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import empty

from main.api.serializers import (IrisSerializer, ManyToManyExtendedSerializer, SerializerUpdateExtraMixin,
                                  SerializerCreateExtraMixin, GetGroupFromRequestMixin)
from features.serializers import FeatureRegularSerializer
from main.api.validators import BulkUniqueRelatedValidator
from iris_masters.models import RecordType, District, Application, RecordState, ExternalService, Process
from main.utils import get_translated_fields
from profiles.models import Group
from themes.models import (DESCRIPTIONS_MAX_LENGTH, Area, Element, ElementDetail, Keyword, ApplicationElementDetail,
                           ElementDetailFeature, DerivationDistrict, ElementDetailResponseChannel, DerivationDirect,
                           ThemeGroup, ElementDetailThemeGroup, GroupProfileElementDetail, ElementDetailDeleteRegister,
                           DerivationPolygon, Zone)


class ThemeGroupSerializer(IrisSerializer):
    description = serializers.CharField(max_length=60, min_length=3)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validators = [
            BulkUniqueRelatedValidator(
                main_fields=["description"], filter_fields=[], queryset=ThemeGroup.objects.all(),
                message=_("The description must be unique and there is or was another theme group with the same.")
            )
        ]

    class Meta:
        model = ThemeGroup
        fields = ("id", "user_id", "created_at", "updated_at", "description", "position", "can_delete")
        read_only_fields = ("id", "user_id", "created_at", "updated_at")


class AreaSerializer(IrisSerializer):
    description = serializers.CharField(max_length=DESCRIPTIONS_MAX_LENGTH, min_length=3)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validators = [
            BulkUniqueRelatedValidator(
                main_fields=[field for field in self.get_translation_fields("description")],
                filter_fields=[], queryset=Area.objects.all_with_deleted(),
                message=_("The description must be unique and there is or was another area with the same.")
            )
        ]

    class Meta:
        model = Area
        fields = ("id", "description", "order", "area_code", "query_area", "favourite", "can_delete", "icon_name")


class KeyWordSerializer(SerializerCreateExtraMixin, serializers.ModelSerializer):
    detail = serializers.PrimaryKeyRelatedField(
        queryset=ElementDetail.objects.filter(**ElementDetail.ENABLED_ELEMENTDETAIL_FILTERS),
        error_messages={"does_not_exist": _("The selected element detail does not exists")}, required=False
    )

    class Meta:
        model = Keyword
        fields = ("description", "detail")


class ElementSerializer(IrisSerializer):
    area_id = serializers.PrimaryKeyRelatedField(
        source="area",
        queryset=Area.objects.all(),
        error_messages={
            "does_not_exist": _("The selected area does not exists"),
        }
    )
    area = AreaSerializer(read_only=True)
    description = serializers.CharField(max_length=DESCRIPTIONS_MAX_LENGTH, min_length=3)

    class Meta:
        model = Element
        fields = ("id", "description", "order", "element_code", "area",
                  "area_id", "can_delete", "is_favorite", "icon_name")


class ApplicationElementDetailSerializer(serializers.ModelSerializer):
    description = serializers.StringRelatedField(source="application", read_only=True)

    class Meta:
        model = ApplicationElementDetail
        fields = ("application", "favorited", "description")


class ElementDetailFeatureSerializer(SerializerCreateExtraMixin, serializers.ModelSerializer):
    description = serializers.StringRelatedField(source="feature", read_only=True)
    is_special = serializers.SerializerMethodField()

    class Meta:
        model = ElementDetailFeature
        fields = ("feature", "order", "is_mandatory", "description", "is_special")

    def get_is_special(self, obj):
        return obj.feature.is_special


class DerivationDirectSerializer(SerializerCreateExtraMixin, serializers.ModelSerializer):
    element_detail = serializers.PrimaryKeyRelatedField(
        queryset=ElementDetail.objects.filter(**ElementDetail.ENABLED_ELEMENTDETAIL_FILTERS),
        error_messages={"does_not_exist": _("The selected element detail does not exists")}, required=False
    )

    record_state = serializers.PrimaryKeyRelatedField(
        queryset=RecordState.objects.filter(enabled=True),
        error_messages={"does_not_exist": _("The selected record state does not exists")},
    )

    group = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.filter(deleted__isnull=True),
        error_messages={"does_not_exist": _("The selected group does not exists")},
    )

    class Meta:
        model = DerivationDirect
        fields = ("element_detail", "record_state", "group")


class DerivationDistrictSerializer(SerializerCreateExtraMixin, serializers.ModelSerializer):
    element_detail = serializers.PrimaryKeyRelatedField(
        queryset=ElementDetail.objects.filter(**ElementDetail.ENABLED_ELEMENTDETAIL_FILTERS),
        error_messages={"does_not_exist": _("The selected element detail does not exists")}, required=False
    )

    district = serializers.PrimaryKeyRelatedField(
        queryset=District.objects.filter(allow_derivation=True),
        error_messages={"does_not_exist": _("The selected district does not exists")},
    )

    record_state = serializers.PrimaryKeyRelatedField(
        queryset=RecordState.objects.filter(enabled=True),
        error_messages={"does_not_exist": _("The selected record state does not exists")},
    )

    group = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.filter(deleted__isnull=True),
        error_messages={"does_not_exist": _("The selected group does not exists")},
    )

    class Meta:
        model = DerivationDistrict
        fields = ("element_detail", "district", "record_state", "group")


class ZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Zone
        fields = ("id", "description")
        read_only_fields = fields


class DerivationPolygonSerializer(SerializerCreateExtraMixin, serializers.ModelSerializer):
    element_detail = serializers.PrimaryKeyRelatedField(
        queryset=ElementDetail.objects.filter(**ElementDetail.ENABLED_ELEMENTDETAIL_FILTERS),
        error_messages={"does_not_exist": _("The selected element detail does not exists")}, required=False
    )

    zone = serializers.PrimaryKeyRelatedField(
        queryset=Zone.objects.all(), error_messages={"does_not_exist": _("The selected group does not exists")})

    record_state = serializers.PrimaryKeyRelatedField(
        queryset=RecordState.objects.filter(enabled=True),
        error_messages={"does_not_exist": _("The selected record state does not exists")},
    )

    group = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.filter(deleted__isnull=True),
        error_messages={"does_not_exist": _("The selected group does not exists")},
    )

    class Meta:
        model = DerivationPolygon
        fields = ("element_detail", "zone", "polygon_code", "group", "record_state", "district_mode")


class ElementDetailResponseChannelSerializer(serializers.ModelSerializer):
    name = serializers.StringRelatedField(source="responsechannel", read_only=True)

    class Meta:
        model = ElementDetailResponseChannel
        fields = ("responsechannel", "name")


class ElementDetailThemeGroupSerializer(serializers.ModelSerializer):
    description = serializers.StringRelatedField(source="theme_group", read_only=True)

    class Meta:
        model = ElementDetailThemeGroup
        fields = ("theme_group", "description")


class GroupProfileElementDetailSerializer(serializers.ModelSerializer):
    description = serializers.StringRelatedField(source="group", read_only=True)

    class Meta:
        model = GroupProfileElementDetail
        fields = ("group", "description")


class ElementDetailSerializer(SerializerCreateExtraMixin, SerializerUpdateExtraMixin, IrisSerializer):
    post_create_extra_actions = True
    post_data_keys = ["direct_derivations"]

    element_id = serializers.PrimaryKeyRelatedField(
        source="element", queryset=Element.objects.filter(**Element.ENABLED_ELEMENT_FILTERS),
        error_messages={"does_not_exist": _("The selected element does not exists")})
    record_type_id = serializers.PrimaryKeyRelatedField(
        source="record_type", queryset=RecordType.objects.all(),
        error_messages={"does_not_exist": _("The selected record does not exists")})
    external_service_id = serializers.PrimaryKeyRelatedField(
        source="external_service", queryset=ExternalService.objects.all(),
        required=False, allow_null=True,
        error_messages={"does_not_exist": _("The selected external service does not exists")})
    element = ElementSerializer(read_only=True)
    short_description = serializers.CharField(max_length=DESCRIPTIONS_MAX_LENGTH, min_length=3,
                                              required=False, allow_blank=True)

    keywords = serializers.SerializerMethodField()
    applications = ManyToManyExtendedSerializer(source="applicationelementdetail_set", required=False,
                                                **{"many_to_many_serializer": ApplicationElementDetailSerializer,
                                                   "model": ApplicationElementDetail, "related_field": "detail",
                                                   "to": "application", "extra_values_params": ["favorited"]})

    features = ManyToManyExtendedSerializer(source="feature_configs", required=False,
                                            **{"many_to_many_serializer": ElementDetailFeatureSerializer,
                                               "model": ElementDetailFeature, "related_field": "element_detail",
                                               "to": "feature", "extra_values_params": ["order", "is_mandatory"]})

    direct_derivations = serializers.SerializerMethodField()
    district_derivations = serializers.SerializerMethodField()
    polygon_derivations = serializers.SerializerMethodField()
    response_channels = ManyToManyExtendedSerializer(
        source="elementdetailresponsechannel_set", required=False,
        **{"many_to_many_serializer": ElementDetailResponseChannelSerializer,
           "model": ElementDetailResponseChannel, "related_field": "elementdetail", "to": "responsechannel",
           "extra_query_fields": {"application_id": Application.IRIS_PK}})

    theme_groups = ManyToManyExtendedSerializer(
        source="elementdetailthemegroup_set", required=False,
        **{"many_to_many_serializer": ElementDetailThemeGroupSerializer,
           "model": ElementDetailThemeGroup, "related_field": "element_detail", "to": "theme_group"})

    group_profiles = ManyToManyExtendedSerializer(
        source="groupprofileelementdetail_set", required=False,
        **{"many_to_many_serializer": GroupProfileElementDetailSerializer,
           "model": GroupProfileElementDetail, "related_field": "element_detail", "to": "group"})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validators = [
            BulkUniqueRelatedValidator(
                main_fields=[field for field in self.get_translation_fields("description")],
                filter_fields=("element",),
                queryset=ElementDetail.all_objects.all(),
                message=_("The description must be unique and there is another detail with the same.")
            )
        ]

    class Meta:
        model = ElementDetail
        fields = ("id", "short_description", "description", "pda_description", "app_description",
                  "detail_code", "rat_code", "similarity_hours", "similarity_meters", "validation_place_days",
                  "app_resolution_radius_meters", "sla_hours", "allow_multiderivation_on_reassignment",
                  "order", "element", "element_id", "response_channels", "process", "allow_external", "custom_answer",
                  "show_pda_resolution_time", "requires_ubication", "requires_ubication_full_address",
                  "requires_ubication_district", "requires_citizen", "aggrupation_first", "immediate_response",
                  "external_protocol_id", "first_instance_response", "requires_appointment", "allow_resolution_change",
                  "validated_reassignable", "sla_allows_claims", "allows_open_data", "allows_open_data_location",
                  "allows_open_data_sensible_location", "allows_ssi", "allows_ssi_location", "direct_derivations",
                  "district_derivations", "polygon_derivations", "allows_ssi_sensible_location", "autovalidate_records",
                  "record_type_id", "keywords", "applications", "autovalidate_records", "lopd", "head_text",
                  "footer_text", "features", "external_service_id", "theme_groups", "active", "activation_date",
                  "is_active", "visible", "visible_date", "is_visible", "can_delete", "external_email", "sms_template",
                  "email_template", "group_profiles", "pend_commmunications", "allow_english_lang")
        extra_kwargs = {"process": {"required": True, "allow_null": False}}

    def validate(self, attrs):
        validation = super().validate(attrs)
        ElementDetail.check_external_protocol_with_immediate_response(attrs.get("immediate_response"),
                                                                      attrs.get("external_protocol_id"))
        return validation

    @swagger_serializer_method(serializer_or_field=serializers.ListField)
    def get_direct_derivations(self, obj):
        return [DerivationDirectSerializer(profile_derivation).data
                for profile_derivation in obj.derivationdirect_set.filter(enabled=True)]

    @swagger_serializer_method(serializer_or_field=serializers.ListField)
    def get_district_derivations(self, obj):
        return [DerivationDistrictSerializer(district_derivation).data
                for district_derivation in obj.derivationdistrict_set.filter(enabled=True)]

    @swagger_serializer_method(serializer_or_field=serializers.ListField)
    def get_polygon_derivations(self, obj):
        return [DerivationPolygonSerializer(polygon_derivation).data
                for polygon_derivation in obj.derivationpolygon_set.filter(enabled=True)]

    @swagger_serializer_method(serializer_or_field=serializers.ListField)
    def get_keywords(self, element_detail):
        return [keyword.description for keyword in element_detail.keyword_set.filter(enabled=True)]

    def run_validation(self, data=empty):
        """
        We override the default `run_validation`, because the validation
        performed by validators and the `.validate()` method should
        be coerced into an error dictionary with a "non_fields_error" key.
        """
        if "external_email" in self.fields and self.instance \
           and data.get("process") == Process.EXTERNAL_PROCESSING_EMAIL:
            self.fields["external_email"].allow_blank = False
        validated_data = super().run_validation(data)

        self.check_derivations(validated_data)

        return validated_data

    def check_derivations(self, validated_data):
        """
        Check derivations, states selected, correct number, of districts, ...

        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        district_derivations = self.transform_district_derivations()
        self.check_polygon_derivations()
        self.check_repetead_states_derivations(district_derivations)
        self.check_district_derivations(district_derivations, validated_data)

    def check_polygon_derivations(self):
        polygon_derivations = self.initial_data.get("polygon_derivations", [])
        if polygon_derivations:
            base_zone = polygon_derivations[0]["zone"]
            polygon_codes = [polygon_derivations[0]["polygon_code"]]
            for pol_derivation in polygon_derivations[1:]:
                if pol_derivation["polygon_code"] in polygon_codes:
                    error_message = _("Polygon codes can not be repeated: {}").format(pol_derivation["polygon_code"])
                    raise ValidationError({"polygon_derivations": error_message}, code="invalid")
                polygon_codes.append(pol_derivation["polygon_code"])

                if pol_derivation["zone"] != base_zone:
                    error_message = _("All polygon derivations must be from the same zone: {}").format(base_zone)
                    raise ValidationError({"polygon_derivations": error_message}, code="invalid")

    def check_repetead_states_derivations(self, district_derivations):
        """
        Check if states are not repetead in derivations
        :param district_derivations: Dict of district derivations with states_codes ans keys
        :return:
        """
        direct_state_codes, state_error_codes = self.check_direct_derivations()
        polygon_state_codes = [pol_derivation.get("record_state", RecordState.PENDING_VALIDATE)
                               for pol_derivation in self.initial_data.get("polygon_derivations", [])]

        combined_errors = self.check_combined_state_errors(direct_state_codes, state_error_codes,
                                                           district_derivations.keys(), polygon_state_codes)
        if state_error_codes:
            errors = {"direct_derivations": state_error_codes}
            if combined_errors:
                errors["district_derivations"] = state_error_codes
                errors["polygon_derivations"] = state_error_codes
            raise ValidationError(errors, code="invalid")

    def transform_district_derivations(self):
        """
        Transform district derivations list to a dict with states_codes as keys
        :return:
        """
        state_district_derivations = {}
        for district_derivation in self.initial_data.get("district_derivations", []):
            if district_derivation["record_state"] not in state_district_derivations:
                state_district_derivations[district_derivation["record_state"]] = []
            state_district_derivations[district_derivation["record_state"]].append(int(district_derivation["district"]))
        return state_district_derivations

    @staticmethod
    def check_combined_state_errors(direct_state_codes, state_error_codes, state_district_codes, polygon_state_codes):
        """
        Check if states are not repeated on the different types of derivations
        :param direct_state_codes: States with previous derivations
        :param state_error_codes: List of repeated states codes
        :param state_district_codes: State codes of district derivations
        :param polygon_state_codes: State codes of polygon derivations
        :return:
        """
        combined_errors = False
        for derivation_state_code in direct_state_codes:
            if derivation_state_code in state_district_codes or derivation_state_code in polygon_state_codes:
                combined_errors = True
                state_error_codes.append(derivation_state_code)
        return combined_errors

    def check_direct_derivations(self):
        """
        Check if the RecordState on direct derivations are not repeated
        :return:
        """
        derivations_state_codes = []
        state_error_codes = []
        for direct_derivation in self.initial_data.get("direct_derivations", []):
            if not direct_derivation["record_state"] in derivations_state_codes:
                derivations_state_codes.append(direct_derivation["record_state"])
            else:
                state_error_codes.append(direct_derivation["record_state"])
        return derivations_state_codes, state_error_codes

    def check_district_derivations(self, district_derivations, validated_data):
        """
        Check if all the RecordState on derivations has all the districts set

        :param district_derivations: Dict of district derivations with states_codes ans keys
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        if self.instance and district_derivations and not self.requires_ubication(validated_data):
            raise ValidationError(
                {"requires_ubication_district": _("If district derivations are set, this field must be set")})

        derivation_district_codes = District.objects.filter(allow_derivation=True).values_list("id", flat=True)
        state_error_codes = []
        for state_code, districts_codes in district_derivations.items():

            if set(derivation_district_codes) != set(districts_codes):
                state_error_codes.append(state_code)

        if state_error_codes:
            raise ValidationError({"district_derivations": state_error_codes})

    def requires_ubication(self, validated_data):
        return validated_data.get("requires_ubication_district") or validated_data.get("requires_ubication")

    def do_post_create_extra_actions(self, instance, validated_data):
        """
        Perform extra actions on create after the instance creation
        :param instance: Instance of the created object
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        if "direct_derivations" in self.initial_data:
            self.serialize_direct_derivations(instance.pk)

        if "district_derivations" in self.initial_data:
            self.serialize_district_derivations(instance.pk)

        if "polygon_derivations" in self.initial_data:
            self.serialize_polygon_derivations(instance.pk)

        if "keywords" in self.initial_data:
            self.serialize_keywords(instance.pk)

    def serialize_direct_derivations(self, element_detail_pk, active_derivations=None):
        """
        Serialize direct derivations of element detail
        :param element_detail_pk: Element detail pk for derivations
        :param active_derivations: List of active derivations, only used on the update operation
        :return:
        """
        for direct_derivation in self.initial_data["direct_derivations"]:
            found = False
            if active_derivations:
                for active_derivation in active_derivations:
                    if self.same_direct_derivation(direct_derivation, active_derivation):
                        found = True
                        break
            if not found:
                direct_derivation["element_detail"] = element_detail_pk
                direct_derivation_serializer = DerivationDirectSerializer(data=direct_derivation, context=self.context)
                direct_derivation_serializer.is_valid(raise_exception=True)
                direct_derivation_serializer.save()

    @staticmethod
    def same_direct_derivation(derivation, active_derivation):
        return derivation["record_state"] == active_derivation["record_state"] and \
               derivation["group"] == active_derivation["group"]

    def serialize_district_derivations(self, element_detail_pk, active_derivations=None):
        """
        Serialize district derivations of element detail
        :param element_detail_pk: Element detail pk for derivations
        :param active_derivations: List of active derivations, only used on the update operation
        :return:
        """
        for derivation in self.initial_data["district_derivations"]:
            found = False
            if active_derivations:
                for active_derivation in active_derivations:
                    if self.same_district_derivation(derivation, active_derivation):
                        found = True
                        break
            if not found:
                derivation["element_detail"] = element_detail_pk
                districtderivation_serializer = DerivationDistrictSerializer(data=derivation, context=self.context)
                districtderivation_serializer.is_valid(raise_exception=True)
                districtderivation_serializer.save()

    @staticmethod
    def same_district_derivation(derivation, active_derivation):
        return derivation["record_state"] == active_derivation["record_state"] and \
               derivation["group"] == active_derivation["group"] and \
               derivation["district"] == active_derivation["district"]

    def serialize_polygon_derivations(self, element_detail_pk, active_derivations=None):
        """
        Serialize district derivations of an element detail.
        :param element_detail_pk: Element detail pk for derivations
        :param active_derivations: List of active derivations, only used on the update operation
        :return:
        """
        derivation_errors = []
        active_derivations = active_derivations if active_derivations else []
        for derivation in self.initial_data.get("polygon_derivations", []):
            derivation["record_state"] = derivation.get("record_state", RecordState.PENDING_VALIDATE)

            if not self._exists_same_polygon_derivation(derivation, active_derivations):
                self._save_new_polygon(derivation, element_detail_pk, derivation_errors)

        if derivation_errors:
            raise ValidationError({"polygon_derivations": derivation_errors}, code="invalid")

    def _exists_same_polygon_derivation(self, derivation, active_derivations):
        """
        :param derivation:
        :param active_derivations:
        :return: True if exists an equivalent derivation withing current active derivations
        """
        for active_derivation in active_derivations:
            if self.same_polygon_derivation(derivation, active_derivation):
                return True
        return False

    def _save_new_polygon(self, derivation, element_detail_pk, derivation_errors):
        """
        Validates and saves a new polygon for the given element detail. In case of validation error, it will be added
        to the derivation_errors list passed as parameter to this method.
        :param derivation: Derivation data received for saving.
        :param element_detail_pk: ElementDatail pk for saving the poligon derivation
        :param derivation_errors: List object for accumulating errors
        """
        derivation["element_detail"] = element_detail_pk
        polygon_derivation_serializer = DerivationPolygonSerializer(data=derivation, context=self.context)
        if polygon_derivation_serializer.is_valid():
            polygon_derivation_serializer.save()
        else:
            errors = polygon_derivation_serializer.errors.copy()
            errors.update({"record_state_id": derivation["record_state"]})
            derivation_errors.append(errors)

    @staticmethod
    def same_polygon_derivation(derivation, active_derivation):
        return derivation["zone"] == active_derivation["zone"] and \
               derivation["polygon_code"] == active_derivation["polygon_code"] and \
               derivation["group"] == active_derivation["group"] and \
               derivation["record_state"] == active_derivation["record_state"] and \
               derivation["district_mode"] == active_derivation["district_mode"]

    def serialize_keywords(self, element_detail_pk, active_keywords=None):
        """
        Serialize keywords of element detail
        :param element_detail_pk: Element detail pk for keywords
        :param active_keywords: List of active keywords, only used on the update operation
        :return:
        """
        for keyword in self.initial_data["keywords"]:
            found = False
            if active_keywords:
                for active_keyword in active_keywords:
                    if keyword == active_keyword["description"]:
                        found = True
                        break
            if not found:
                ser = KeyWordSerializer(data={"description": keyword.upper(), "detail": element_detail_pk},
                                        context=self.context)
                if not ser.is_valid():
                    raise ValidationError("Invalid Keyword: {}".format(keyword))
                ser.save()

    def do_extra_actions_on_update(self, validated_data):
        """
        Perform extra actions on update
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        self.check_active_mandatory_fields(validated_data)
        self.update_derivations()

        if "keywords" in self.initial_data:
            self.update_keywords()

        if "applications" in self.initial_data:
            self.update_applications(validated_data)
        if "response_channels" in self.initial_data:
            self.update_response_channels(validated_data)
        if "features" in self.initial_data:
            self.update_features(validated_data)
        if "theme_groups" in self.initial_data:
            self.update_theme_groups(validated_data)
        if "group_profiles" in self.initial_data:
            self.update_group_profiles(validated_data)

    def update_applications(self, validated_data):
        """
        Update detail applications

        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        ser = ManyToManyExtendedSerializer(**{"many_to_many_serializer": ApplicationElementDetailSerializer,
                                              "model": ApplicationElementDetail, "related_field": "detail",
                                              "to": "application", "extra_values_params": ["favorited"]},
                                           source="applicationelementdetail_set",
                                           data=self.initial_data["applications"])
        ser.bind(field_name="", parent=self)
        if ser.is_valid():
            ser.save()
        validated_data.pop(ser.source, None)

    def update_response_channels(self, validated_data):
        """
        Update detail response channels

        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        ser = ManyToManyExtendedSerializer(
            source="elementdetailresponsechannel_set", data=self.initial_data["response_channels"],
            **{"many_to_many_serializer": ElementDetailResponseChannelSerializer, "to": "responsechannel",
               "model": ElementDetailResponseChannel, "related_field": "elementdetail",
               "extra_query_fields": {"application_id": Application.IRIS_PK}})
        ser.bind(field_name="", parent=self)
        if ser.is_valid():
            ser.save()
        validated_data.pop(ser.source, None)

    def update_features(self, validated_data):
        """
        Update detail features

        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        ser = ManyToManyExtendedSerializer(**{"many_to_many_serializer": ElementDetailFeatureSerializer,
                                              "model": ElementDetailFeature, "related_field": "element_detail",
                                              "to": "feature", "extra_values_params": ["order", "is_mandatory"]},
                                           source="feature_configs",
                                           data=self.initial_data["features"])
        ser.bind(field_name="", parent=self)
        if ser.is_valid():
            ser.save()
        validated_data.pop(ser.source, None)

    def update_theme_groups(self, validated_data):
        """
        Update detail theme groups

        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        ser = ManyToManyExtendedSerializer(**{"many_to_many_serializer": ElementDetailThemeGroupSerializer,
                                              "model": ElementDetailThemeGroup, "related_field": "element_detail",
                                              "to": "theme_group"},
                                           source="elementdetailthemegroup_set",
                                           data=self.initial_data["theme_groups"])
        ser.bind(field_name="", parent=self)
        if ser.is_valid():
            ser.save()
        validated_data.pop(ser.source, None)

    def update_group_profiles(self, validated_data):
        """
        Update detail group profiles

        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        ser = ManyToManyExtendedSerializer(**{"many_to_many_serializer": GroupProfileElementDetailSerializer,
                                              "model": GroupProfileElementDetail, "related_field": "element_detail",
                                              "to": "group"},
                                           source="groupprofileelementdetail_set",
                                           data=self.initial_data["group_profiles"])
        ser.bind(field_name="", parent=self)
        if ser.is_valid():
            ser.save()
        validated_data.pop(ser.source, None)

    @staticmethod
    def check_active_mandatory_fields(validated_data):
        # if the user has set the theme to be active, check the active mandatory fields. If any field is missing,
        # the active flag will be set to False because the theme can be saved but it can not be active.
        if validated_data.get("active"):
            for field in ElementDetail.ACTIVE_MANDATORY_FIEDLS:
                if not validated_data.get(field):
                    validated_data["active"] = False
                    return

            for relationship in ElementDetail.RELATION_ACTIVE_MANDATORY:
                if not validated_data.get(relationship, []):
                    validated_data["active"] = False
                    return

    def update_derivations(self):
        """
        Update theme derivations
        :return:
        """
        if "direct_derivations" in self.initial_data:
            self.update_direct_derivations()
        if "district_derivations" in self.initial_data:
            self.update_district_derivations()
        if "polygon_derivations" in self.initial_data:
            self.update_polygon_derivations()

    def update_direct_derivations(self):
        """
        Update direct derivations of element detail, disabling the ones that change and creating the new ones
        :return:
        """
        active_derivations = self.instance.derivationdirect_set.filter(enabled=True).values(
            "record_state", "group", "id")
        disabled_items = []
        # Look for derivations that have changed
        for active_derivation in active_derivations:
            found = False
            for derivation in self.initial_data["direct_derivations"]:
                if self.same_direct_derivation(derivation, active_derivation):
                    found = True
                    break
            if not found:
                disabled_items.append(active_derivation["id"])

        # Disable derivations that have changed
        if disabled_items:
            DerivationDirect.objects.filter(id__in=disabled_items).update(enabled=False)

        self.serialize_direct_derivations(self.instance.pk, active_derivations)

    def update_district_derivations(self):
        """
        Update district derivations of element detail, disabling the ones that change and creating the new ones
        :return:
        """
        active_derivations = self.instance.derivationdistrict_set.filter(enabled=True).values(
            "record_state", "group", "district", "id")
        disabled_items = []
        # Look for derivations that have changed
        for active_derivation in active_derivations:
            found = False
            for derivation in self.initial_data["district_derivations"]:
                if self.same_district_derivation(derivation, active_derivation):
                    found = True
                    break
            if not found:
                disabled_items.append(active_derivation["id"])

        # Disable derivations that have changed
        if disabled_items:
            DerivationDistrict.objects.filter(id__in=disabled_items).update(enabled=False)

        self.serialize_district_derivations(self.instance.pk, active_derivations)

    def update_polygon_derivations(self):
        """
        Update polygon derivations of element detail, disabling the ones that change and creating the new ones
        :return:
        """
        active_derivations = self.instance.derivationpolygon_set.filter(enabled=True).values(
            "record_state", "group", "zone", "polygon_code", "id", "district_mode")
        disabled_items = []
        # Look for derivations that have changed
        for active_derivation in active_derivations:
            found = False
            for derivation in self.initial_data["polygon_derivations"]:
                if "record_state" not in derivation:
                    derivation["record_state"] = RecordState.PENDING_VALIDATE
                if self.same_polygon_derivation(derivation, active_derivation):
                    found = True
                    break
            if not found:
                disabled_items.append(active_derivation["id"])

        # Disable derivations that have changed
        if disabled_items:
            DerivationPolygon.objects.filter(id__in=disabled_items).update(enabled=False)

        self.serialize_polygon_derivations(self.instance.pk, active_derivations)

    def update_keywords(self):
        """
        Update keywords of element detail, disabling the ones that change and creating the new ones
        :return:
        """
        active_keywords = self.instance.keyword_set.filter(enabled=True).values("description", "id")
        disabled_keywords = []
        # Look for keywords that have changed
        for active_keyword in active_keywords:
            found = False
            for keyword in self.initial_data["keywords"]:
                if keyword == active_keyword["description"]:
                    found = True
                    break
            if not found:
                disabled_keywords.append(active_keyword["id"])

        # Disable keywords that have changed
        if disabled_keywords:
            Keyword.objects.filter(id__in=disabled_keywords).update(enabled=False)

        self.serialize_keywords(self.instance.pk, active_keywords)


class ElementDetailCheckSerializer(serializers.Serializer):
    can_save = serializers.BooleanField()
    mandatory_fields_missing = serializers.BooleanField()
    will_be_active = serializers.BooleanField()


class ElementDetailActiveSerializer(serializers.ModelSerializer):
    """
    Serializer for active/deactive element detail and activtion date
    """

    class Meta:
        model = ElementDetail
        fields = ("id", "active", "activation_date")

    def run_validation(self, data=empty):
        validated_data = super().run_validation(data)
        if validated_data.get("active"):
            for field in ElementDetail.ACTIVE_MANDATORY_FIEDLS:
                if not getattr(self.instance, field, None):
                    raise ValidationError({"active": _("Theme can not be set to active because there is "
                                                       "mandatory information missing")})
            for relationship in ElementDetail.RELATION_ACTIVE_MANDATORY:
                rel = getattr(self.instance, relationship)
                if not rel or not rel.filter(enabled=True).exists():
                    raise ValidationError({"active": _("Theme can not be set to active because there is "
                                                       "mandatory information missing")})
        return validated_data


class AreaShortSerializer(AreaSerializer):
    class Meta:
        model = Area
        fields = ("id", "description", "order", "area_code", "query_area", "favourite", "icon_name")


class ElementShortSerializer(ElementSerializer):
    area = AreaShortSerializer(read_only=True)

    class Meta:
        model = Element
        fields = ("id", "description", "order", "element_code", "area", "is_favorite", "icon_name")


class ElementDetailShortSerializer(ElementDetailSerializer):
    element = ElementShortSerializer(read_only=True)

    class Meta:
        model = ElementDetail
        fields = ("id", "short_description", "description", "pda_description", "app_description",
                  "validation_place_days", "detail_code", "rat_code", "similarity_hours", "similarity_meters",
                  "lopd", "head_text", "app_resolution_radius_meters", "sla_hours",
                  "allow_multiderivation_on_reassignment", "order", "element", "process", "allow_external",
                  "custom_answer", "show_pda_resolution_time", "requires_ubication", "requires_ubication_full_address",
                  "requires_ubication_district", "requires_citizen", "aggrupation_first", "immediate_response",
                  "first_instance_response", "requires_appointment", "allow_resolution_change", "footer_text",
                  "validated_reassignable", "sla_allows_claims", "autovalidate_records", "autovalidate_records",
                  "active", "activation_date", "external_protocol_id")


class AreaListSerializer(IrisSerializer):
    class Meta:
        model = Area
        fields = ("id", "description", "favourite", "order", "can_delete", "icon_name")
        read_only_fields = ("id", "description", "favourite", "order", "can_delete")


class ElementListSerializer(IrisSerializer):
    area = AreaShortSerializer(many=False)
    is_query = serializers.BooleanField()
    is_issue = serializers.BooleanField()

    class Meta:
        model = Element
        fields = ("id", "description", "area", "is_favorite", "order",
                  "can_delete", "is_query", "is_issue", "icon_name")
        read_only_fields = ("id", "description", "area", "is_favorite",
                            "order", "can_delete", "is_query", "is_issue")


class ElementDetailSearchSerializer(ElementDetailSerializer):
    element = ElementShortSerializer(many=False)
    applications = None

    class Meta:
        model = ElementDetail
        fields = ("id", "description", "detail_code", "order", "element", "process",
                  "external_protocol_id", "allow_external", "custom_answer", "requires_citizen", "immediate_response",
                  "first_instance_response", "record_type_id", "keywords", "applications",
                  "active", "activation_date", "is_visible", "visible", "visible_date")
        read_only_fields = fields


class ElementDetailCreateSerializer(ElementDetailSerializer):
    class Meta:
        model = ElementDetail
        fields = ("id", "short_description", "description", "element_id", "detail_code", "process", "record_type_id")
        extra_kwargs = {"process": {"required": True, "allow_null": False}}


class ElementDetailListSerializer(ElementDetailSerializer):
    element = ElementShortSerializer(many=False)

    class Meta:
        model = ElementDetail
        fields = ("id", "short_description", "description", "pda_description", "app_description",
                  "detail_code", "rat_code", "similarity_hours", "similarity_meters", "validation_place_days",
                  "app_resolution_radius_meters", "sla_hours", "allow_multiderivation_on_reassignment", "order",
                  "element", "process", "allow_external", "custom_answer", "show_pda_resolution_time",
                  "requires_ubication", "requires_ubication_full_address", "requires_ubication_district",
                  "requires_citizen", "aggrupation_first", "immediate_response", "first_instance_response",
                  "requires_appointment", "allow_resolution_change", "validated_reassignable", "sla_allows_claims",
                  "allows_open_data", "allows_open_data_location", "allows_open_data_sensible_location",
                  "allows_ssi", "allows_ssi_location", "allows_ssi_sensible_location", "autovalidate_records",
                  "record_type_id", "keywords", "autovalidate_records", "applications", "lopd", "head_text",
                  "footer_text", "active", "activation_date", "is_visible", "can_delete")
        read_only_fields = fields


class ElementDetailChangeSerializer(ElementDetailSerializer):
    class Meta:
        model = ElementDetail
        fields = ("id", "description")
        read_only_fields = fields


class ElementDetailFeatureListSerializer(serializers.ModelSerializer):
    feature = FeatureRegularSerializer()

    class Meta:
        model = ElementDetailFeature
        fields = ("feature", "order", "is_mandatory", "enabled")
        read_only_fields = fields


class AreaAutocompleteSerializer(IrisSerializer):
    """Not being used!"""
    class Meta:
        model = Area
        fields = ("id", "description")


class ElementAutocompleteSerializer(IrisSerializer):
    """Not being used!"""
    class Meta:
        model = Element
        fields = ("id", "description")


class ElementDetailAutocompleteSerializer(IrisSerializer):
    """Not being used!"""
    class Meta:
        model = ElementDetail
        fields = ("id", "description")


class ElementDetailDeleteRegisterSerializer(SerializerCreateExtraMixin, GetGroupFromRequestMixin,
                                            serializers.ModelSerializer):
    extra_actions = True

    deleted_detail_id = serializers.PrimaryKeyRelatedField(
        source="deleted_detail", queryset=ElementDetail.objects.filter(**ElementDetail.ENABLED_ELEMENTDETAIL_FILTERS),
        error_messages={"does_not_exist": _("The selected ElementDetail does not exist or it's deleted")})
    reasignation_detail_id = serializers.PrimaryKeyRelatedField(
        source="reasignation_detail",
        queryset=ElementDetail.objects.filter(**ElementDetail.ENABLED_ELEMENTDETAIL_FILTERS),
        error_messages={"does_not_exist": _("The selected ElementDetail does not exist or it's deleted")})

    class Meta:
        model = ElementDetailDeleteRegister
        fields = ("id", "user_id", "created_at", "updated_at", "deleted_detail_id", "reasignation_detail_id",
                  "only_open")
        read_only_fields = ("id", "user_id", "created_at", "updated_at")

    def run_validation(self, data=empty):
        validated_data = super().run_validation(data)

        if validated_data["deleted_detail"] == validated_data["reasignation_detail"]:
            error_message = _("Deleted detail and Reasignation detail can not be the same")
            raise ValidationError({"deleted_group": error_message, "reasignation_group": error_message}, code="invalid")

        return validated_data

    def do_extra_actions_on_create(self, validated_data):
        validated_data["group"] = self.get_group_from_request(self.context.get("request"))


class ElementDetailCopySerializer(serializers.Serializer):
    element_id = serializers.PrimaryKeyRelatedField(
        queryset=Element.objects.filter(**Element.ENABLED_ELEMENT_FILTERS), source="element",
        error_messages={"does_not_exist": _("The selected element does not exists")})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        description_fields = get_translated_fields('description')
        for field in description_fields:
            self.fields[field] = serializers.CharField()
        self.validators = [
            BulkUniqueRelatedValidator(
                main_fields=description_fields,
                filter_fields=("element",),
                queryset=ElementDetail.all_objects.all(),
                message=_("The description must be unique and there is another detail with the same.")
            )
        ]


class AreaDescriptionSerializer(IrisSerializer):
    class Meta:
        model = Area
        fields = ("id", "description")
        read_only_fields = fields


class ElementDescriptionSerializer(IrisSerializer):
    area = AreaDescriptionSerializer()

    class Meta:
        model = Element
        fields = ("id", "description", "area")
        read_only_fields = fields


class ElementDetailDescriptionSerializer(IrisSerializer):
    element = ElementDescriptionSerializer()

    class Meta:
        model = ElementDetail
        fields = ("id", "description", "element", "external_protocol_id")
        read_only_fields = fields


class AreaRegularSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    description = serializers.CharField()


class ElementRegularSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    description = serializers.CharField()
    area = AreaRegularSerializer()


class ElementDetailRegularSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    description = serializers.CharField()
    element = ElementRegularSerializer()
