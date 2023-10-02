"""
Use IRIS2 models from the different Django apps that compose the project,
 but NEVER EXTEND ANY SERIALIZER from the non public part.
 Serializer inheritance is discouraged by  the Django Rest Framework team itself,
 and even more when talking about security and undessired information expossure.
"""
import base64
import binascii
import types

from django.conf import settings
from django.utils import translation
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.compat import MinValueValidator
from rest_framework.exceptions import ValidationError
from rest_framework.fields import empty
from rest_framework.serializers import ModelSerializer

from communications.models import Message, Conversation
from communications.serializers import MessageCreateSerializer
from features.models import Values, Feature
from iris_masters.models import (Support, District, RecordState, RecordType, ResponseChannel, InputChannel,
                                 ApplicantType, Parameter)
from main.api.validators import MaxYearValidator
from main.utils import LANGUAGES
from profiles.models import get_anonymous_group
from public_api.constants import TRANSACTION_URGENT, TRANSACTION_NORMAL
from public_api.record_card_texts import RecordCardStatePublicTexts
from record_cards.models import (RecordCard, Ubication, RecordCardFeatures, RecordCardSpecialFeatures, Applicant,
                                 Citizen, SocialEntity, RecordCardResponse, RecordFile, RecordCardStateHistory)
from record_cards.record_actions.claim_validate import ClaimValidation
from record_cards.record_actions.conversations_alarms import RecordCardConversationAlarms
from record_cards.record_actions.exceptions import RecordClaimException
from record_cards.serializers import (UbicationValidationMixin, RecordCardResponseValidationMixin,
                                      CheckFileExtensionsMixin)
from themes.actions.theme_mandatory_drupal_fields import ThemeMandatoryDrupalFields
from themes.actions.theme_mandatory_fields import ThemeMandatoryFields
from themes.models import Area, ElementDetail, ElementDetailFeature, Element, ApplicationElementDetail


class AreaPublicSerializer(serializers.ModelSerializer):
    areaIcon = serializers.CharField(source="icon_name", read_only=True)

    class Meta:
        model = Area
        fields = ("id", "description", "area_code", "areaIcon")
        read_only_fields = fields


class ElementPublicSerializer(serializers.ModelSerializer):
    element = serializers.SerializerMethodField()
    elementId = serializers.SerializerMethodField()
    area = serializers.SerializerMethodField()
    areaId = serializers.SerializerMethodField()
    areaIcon = serializers.SerializerMethodField()

    class Meta:
        model = Element
        fields = ("element", "elementId", "area", "areaId", "areaIcon")
        read_only_fields = fields

    def get_element(self, obj):
        return obj.description

    def get_elementId(self, obj):
        return obj.pk

    def get_area(self, obj):
        return obj.area.description

    def get_areaId(self, obj):
        return obj.area.pk

    def get_areaIcon(self, obj):
        return obj.area.icon_name


class ElementDetailPublicSerializer(serializers.ModelSerializer):
    detailId = serializers.SerializerMethodField()
    area = serializers.SerializerMethodField()
    areaId = serializers.SerializerMethodField()
    element = serializers.SerializerMethodField()
    elementId = serializers.SerializerMethodField()
    detail = serializers.SerializerMethodField()
    theme = serializers.SerializerMethodField()
    application = serializers.SerializerMethodField()
    recordType = serializers.SerializerMethodField()
    recordIcon = serializers.SerializerMethodField()
    iconName = serializers.SerializerMethodField()
    requiresAppointment = serializers.SerializerMethodField()
    headText = serializers.SerializerMethodField()
    characteristics = serializers.SerializerMethodField()
    requiresUbication = serializers.SerializerMethodField()
    favourite = serializers.SerializerMethodField()
    description_gl = serializers.SerializerMethodField()
    description_es = serializers.SerializerMethodField()
    description_en = serializers.SerializerMethodField()
    element_gl = serializers.SerializerMethodField()
    element_es = serializers.SerializerMethodField()
    element_en = serializers.SerializerMethodField()
    area_gl = serializers.SerializerMethodField()
    area_es = serializers.SerializerMethodField()
    area_en = serializers.SerializerMethodField()

    class Meta:
        model = ElementDetail
        fields = ("detailId", "area", "areaId", "element", "elementId", "detail", "theme", "application", "recordType",
                  "head_text", "footer_text", "average_close_days", "recordIcon",
                  'iconName', 'requiresAppointment', 'headText',
                  "characteristics", "requiresUbication", "favourite", "description_gl", "description_es",
                  "description_en", "element_gl", "element_es", "element_en", "area_gl", "area_es", "area_en")
        read_only_fields = fields

    def get_detailId(self, obj):
        return obj.id

    def get_detail(self, obj):
        return obj.description

    def get_theme(self, obj):
        return obj.pda_description

    def get_element(self, obj):
        return obj.element.description

    def get_elementId(self, obj):
        return obj.element.pk

    def get_area(self, obj):
        return obj.element.area.description

    def get_areaId(self, obj):
        return obj.element.area.pk

    def get_application(self, obj):
        return obj.app_description

    def get_recordType(self, obj):
        return obj.record_type.description if obj.record_type else ""

    def get_recordIcon(self, obj):
        return getattr(obj.record_type, 'description_gl', obj.record_type.description)

    def get_iconName(self, obj):
        return obj.element.area.icon_name

    def get_requiresAppointment(self, obj):
        return obj.requires_appointment

    def get_headText(self, obj):
        return obj.head_text

    def get_characteristics(self, obj):
        characteristics = []

        for elementdetail_feature in obj.feature_configs.all():
            characteristics.append(ElementDetailFeaturePublicSerializer(elementdetail_feature).data)
        return characteristics

    def get_requiresUbication(self, obj):
        return obj.requires_ubication

    def get_favourite(self, obj):
        return obj.element.is_favorite

    def get_description_gl(self, obj):
        return obj.short_description_gl

    def get_description_en(self, obj):
        return obj.short_description_en

    def get_description_es(self, obj):
        return obj.short_description_es

    def get_element_gl(self, obj):
        return obj.element.description_gl

    def get_element_es(self, obj):
        return obj.element.description_es

    def get_element_en(self, obj):
        return obj.element.description_en

    def get_area_gl(self, obj):
        return obj.element.area.description_gl

    def get_area_es(self, obj):
        return obj.element.area.description_es

    def get_area_en(self, obj):
        return obj.element.area.description_en


class ObjectCacheField(serializers.Field):
    def __init__(self, cache_attr=None, lang=None, **kwargs):
        self.lang = lang
        self.cache_attr = cache_attr
        kwargs['source'] = '*'
        kwargs['read_only'] = True
        super().__init__(**kwargs)

    def to_representation(self, value):
        """
        It will look for parent serializer.cache.<self.cache_attr> and for the id of value.<cache_attr>.<cache_attr>_id.

        Example. area cache: self.parent.cache.area and value.area.area_id.
        """
        cache = getattr(self.parent.cache, self.cache_attr)
        cache_item = getattr(value, self.cache_attr)
        return cache.get_translated_description(getattr(cache_item, f'{self.cache_attr}_id'), self.lang)


class ElementDetailRegularPublicSerializer(serializers.Serializer):
    detailId = serializers.IntegerField(source="id")
    area = serializers.SerializerMethodField()
    areaId = serializers.IntegerField(source="element.area_id")
    element = serializers.CharField(source="element.description")
    elementId = serializers.IntegerField(source="element.pk")
    detail = serializers.CharField(source="description")
    theme = serializers.CharField(source="pda_description")
    application = serializers.CharField(source="app_description")
    recordType = serializers.SerializerMethodField()
    recordIcon = serializers.SerializerMethodField()
    iconName = serializers.SerializerMethodField()
    requiresAppointment = serializers.BooleanField(source="requires_appointment")
    headText = serializers.CharField(source="head_text")
    head_text = serializers.CharField()
    footer_text = serializers.CharField()
    characteristics = serializers.SerializerMethodField()
    requiresUbication = serializers.BooleanField(source="requires_ubication")
    favourite = serializers.BooleanField(source="element.is_favorite")
    average_close_days = serializers.IntegerField()
    fav_for_app = serializers.SerializerMethodField()

    def __init__(self, instance=None, data=empty, **kwargs):
        self.cache = kwargs.pop("cache", None)
        self.application = kwargs.pop("application", None)
        super().__init__(instance, data, **kwargs)
        for lang, _ in settings.LANGUAGES:
            self.fields[f'element_{lang}'] = serializers.CharField(source=f"element.description_{lang}")
            self.fields[f'short_description_{lang}'] = serializers.CharField()
            self.fields[f'description_{lang}'] = serializers.CharField()

            # Generate get_area method for serializer Method
            def get_area_method(self, obj):
                return self.cache.area.get_translated_description(obj.element.area_id, lang)
            setattr(self, f'get_area_{lang}', types.MethodType(get_area_method, self))
            self.fields[f'area_{lang}'] = serializers.SerializerMethodField()

    def get_fav_for_app(self, obj):
        result = ApplicationElementDetail.objects.filter(enabled=True,
                                                         application=self.application,
                                                         detail_id=obj.id).first()
        result = '1' if result.favorited else '0'
        return result

    def get_recordType(self, obj):
        return self.cache.record_type.get_item_description(obj.record_type_id)

    def get_recordIcon(self, obj):
        return self.cache.record_type.get_item_description(obj.record_type_id)

    def get_characteristics(self, obj):
        characteristics = []
        for elementdetail_feature in obj.feature_configs.all().order_by("order"):
            characteristics.append(ElementDetailFeaturePublicSerializer(elementdetail_feature).data)
        return characteristics

    def get_area(self, obj):
        return self.cache.area.get_item_description(obj.element.area_id)

    def get_iconName(self, obj):
        return self.cache.area.get_item_icon_name(obj.element.area_id)


class ElementDetailFeaturePublicSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    mandatory = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    special = serializers.SerializerMethodField()
    mask = serializers.SerializerMethodField()
    desc_mask = serializers.SerializerMethodField()
    options = serializers.SerializerMethodField()
    explanatory_text = serializers.SerializerMethodField()
    codename = serializers.SerializerMethodField()
    editable_for_citizen = serializers.SerializerMethodField()
    options_proxy = serializers.SerializerMethodField()
    description_gl = serializers.SerializerMethodField()
    description_es = serializers.SerializerMethodField()
    description_en = serializers.SerializerMethodField()

    class Meta:
        model = ElementDetailFeature
        fields = ("id", "type", "mandatory", "title", "special", "mask", "desc_mask", "options", "explanatory_text",
                  "order", "codename", "editable_for_citizen", "options_proxy", "description_gl", "description_es",
                  "description_en")
        read_only_fields = fields

    def get_id(self, obj):
        return obj.feature.pk

    def get_type(self, obj):
        if obj.feature.values_type:
            return "Options"
        elif obj.feature.mask:
            return obj.feature.mask.type
        return

    def get_mandatory(self, obj):
        return obj.is_mandatory

    def get_title(self, obj):
        return obj.feature.description

    def get_special(self, obj):
        return obj.feature.is_special

    def get_mask(self, obj):
        return obj.feature.mask_id

    def get_desc_mask(self, obj):
        return obj.feature.mask.description if obj.feature.mask else ""

    def get_options(self, obj):
        if obj.feature.values_type:
            result_array = []
            result = Values.objects.filter(
                deleted__isnull=True, values_type=obj.feature.values_type)
            for desc in result:
                result_array.append(desc.description)
            return result_array
        return []

    def get_options_proxy(self, obj):
        if obj.feature.values_type:
            return Values.objects.filter(
                deleted__isnull=True, values_type=obj.feature.values_type).values_list("description_gl",
                                                                                       "description_es",
                                                                                       "description_en")
        return []

    def get_explanatory_text(self, obj):
        return obj.feature.explanatory_text

    def get_codename(self, obj):
        return obj.feature.codename

    def get_editable_for_citizen(self, obj):
        return obj.feature.editable_for_citizen

    def get_description_gl(self, obj):
        return obj.feature.description_gl

    def get_description_es(self, obj):
        return obj.feature.description_es

    def get_description_en(self, obj):
        return obj.feature.description_en


class ResponseChannelPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResponseChannel
        fields = ("id", "name")
        read_only_fields = fields


class ElementDetailRetrievePublicSerializer(ElementDetailPublicSerializer):
    mandatoryFields = serializers.SerializerMethodField()
    characteristics = serializers.SerializerMethodField()
    response_channels = serializers.SerializerMethodField()
    mandatory_fields = serializers.SerializerMethodField()
    external_process_type = serializers.SerializerMethodField()
    max_bytes_files_size = serializers.SerializerMethodField()
    extension_files = serializers.SerializerMethodField()
    mandatory_drupal_fields = serializers.SerializerMethodField()

    class Meta:
        model = ElementDetail
        fields = ("detailId", "area", "areaId", "element", "elementId", "detail", "theme", "application",
                  "mandatoryFields", "mandatory_fields", "mandatory_drupal_fields", "characteristics", "head_text",
                  "footer_text", "recordType", "record_type_id", "immediate_response", "response_channels",
                  "external_process_type", "max_bytes_files_size", "average_close_days", "extension_files")
        read_only_fields = fields

    def get_mandatoryFields(self, obj):
        return obj.feature_configs.filter(
            enabled=True, is_mandatory=True, feature__deleted__isnull=True).values_list("feature__description",
                                                                                        flat=True)

    def get_mandatory_fields(self, obj):
        return ThemeMandatoryFields(obj).get_mapping_value()

    def get_mandatory_drupal_fields(self, obj):
        return ThemeMandatoryDrupalFields(obj).get_mandatory_fields()

    def get_characteristics(self, obj):
        characteristics = []

        elementdetail_feature_qs = obj.feature_configs.filter(
            enabled=True, feature__deleted__isnull=True,
        ).select_related("feature", "feature__mask", "feature__values_type").order_by("order")

        for elementdetail_feature in elementdetail_feature_qs:
            characteristics.append(ElementDetailFeaturePublicSerializer(elementdetail_feature).data)
        return characteristics

    def get_response_channels(self, obj):
        response_channels = []
        kwargs = {"enabled": True}
        request = self.context.get("request")
        if request and hasattr(request, "application"):
            kwargs["application"] = request.application

        details_response_channels = obj.elementdetailresponsechannel_set.filter(
            **kwargs).select_related("responsechannel")

        for details_responsechannel in details_response_channels:
            response_channels.append(ResponseChannelPublicSerializer(details_responsechannel.responsechannel).data)
        return response_channels

    def get_external_process_type(self, obj):
        return True if obj.external_service else False

    def get_max_bytes_files_size(self, obj):
        return settings.DRF_CHUNKED_UPLOAD_MAX_BYTES

    def get_extension_files(self, obj):
        return Parameter.get_parameter_by_key("EXTENSION_PERMESES_FITXERS",
                                              "jpg;jpeg;pdf;zip;rar")


class ElementDetailLastUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ElementDetail
        fields = ("updated_at",)
        read_only_fields = fields


class RecordStatePublicSerializer(serializers.ModelSerializer):
    description = serializers.SerializerMethodField()

    class Meta:
        model = RecordState
        fields = ("description", "pk")
        read_only_fields = fields

    def get_description(self, obj):
        return obj.get_id_display()


class CloseCancelDateMixin:
    def get_close_cancel_date(self, obj):
        state_change = None
        if obj.record_state_id == RecordState.CLOSED:
            state_change = RecordCardStateHistory.objects.filter(record_card=obj,
                                                                 next_state_id=RecordState.CLOSED).first()
        elif obj.record_state_id == RecordState.CANCELLED:
            state_change = RecordCardStateHistory.objects.filter(record_card=obj,
                                                                 next_state_id=RecordState.CANCELLED).first()
        return state_change.created_at if state_change else None


class RecordCardRetrieveStatePublicSerializer(CloseCancelDateMixin, serializers.ModelSerializer):
    record_state = RecordStatePublicSerializer()
    can_be_claimed = serializers.SerializerMethodField()
    text_es = serializers.SerializerMethodField()
    text_en = serializers.SerializerMethodField()
    text_gl = serializers.SerializerMethodField()
    close_cancel_date = serializers.SerializerMethodField()
    claim_record = serializers.SerializerMethodField()
    can_response_message = serializers.SerializerMethodField()

    class Meta:
        model = RecordCard
        fields = ("normalized_record_id", "record_state", "created_at", "can_be_claimed", "text_es", "text_en",
                  "text_gl", "close_cancel_date", "claim_record", "can_response_message")
        read_only_fields = fields

    def get_can_be_claimed(self, obj):
        try:
            ClaimValidation(obj).validate()
            return True
        except RecordClaimException:
            return False

    def get_text_es(self, obj):
        return self.record_message(obj, "es")

    def get_text_en(self, obj):
        return self.record_message(obj, "en")

    def get_text_gl(self, obj):
        return self.record_message(obj, "gl")

    def record_message(self, record, language):
        old_lang = translation.get_language()
        translation.activate(language)
        message = RecordCardStatePublicTexts(record).get_state_text()
        translation.activate(old_lang)
        return message

    def get_claim_record(self, obj):
        last_claim = obj.get_last_claim()
        if not last_claim:
            return {}
        return {"state": RecordStatePublicSerializer(last_claim.record_state).data,
                "normalized_record_id": last_claim.normalized_record_id}

    def get_can_response_message(self, obj):
        if "message" not in self.context:
            return False
        return not self.context["message"].is_answered


class DistrictPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        fields = ("id", "name")
        read_only_fields = fields


class RecordCardSSIPublicSerializer(serializers.ModelSerializer):
    area = serializers.CharField(source="element_detail.element.area.description")
    area_id = serializers.IntegerField(source="element_detail.element.area_id")
    element = serializers.CharField(source="element_detail.element.description")
    element_id = serializers.IntegerField(source="element_detail.element_id")
    element_detail = serializers.CharField(source="element_detail.description")
    record_state = serializers.CharField(source="record_state.description")
    record_type = serializers.CharField(source="record_type.description")
    ubication = serializers.SerializerMethodField()

    class Meta:
        model = RecordCard
        fields = ("id", "created_at", "area", "area_id", "element", "element_id", "element_detail", "element_detail_id",
                  "normalized_record_id", "record_state", "record_state_id", "record_type", "record_type_id",
                  "ubication", "start_date_process", "closing_date")
        read_only_fields = fields

    def get_ubication(self, obj):
        if not obj.element_detail.allows_ssi_location or not obj.ubication:
            return None
        return UbicationSSIPublicSerializer(
            obj.ubication, context={"sensible_location": obj.element_detail.allows_ssi_location}).data


class UbicationSSIPublicSerializer(serializers.ModelSerializer):
    via_type = serializers.SerializerMethodField()
    street = serializers.SerializerMethodField()
    district = serializers.SerializerMethodField()
    number = serializers.SerializerMethodField()
    xetrs89a = serializers.SerializerMethodField()
    yetrs89a = serializers.SerializerMethodField()

    class Meta:
        model = Ubication
        fields = ("via_type", "street", "number", "district", "neighborhood", "geocode_district_id",
                  "neighborhood_id", "statistical_sector", "xetrs89a", "yetrs89a")
        read_only_fields = fields

    def check_sensible_location(self, return_value):
        return None if not self.context.get("sensible_location", None) else return_value

    def get_via_type(self, obj):
        return self.check_sensible_location(obj.via_type)

    def get_street(self, obj):
        return self.check_sensible_location(obj.street)

    def get_number(self, obj):
        return self.check_sensible_location(obj.street2)

    def get_xetrs89a(self, obj):
        return self.check_sensible_location(obj.xetrs89a)

    def get_yetrs89a(self, obj):
        return self.check_sensible_location(obj.yetrs89a)

    def get_district(self, obj):
        return obj.district.name if obj.district else ""


class UbicationPublicSerializer(serializers.ModelSerializer):
    geocode = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    number = serializers.SerializerMethodField()

    class Meta:
        model = Ubication
        fields = ("latitude", "longitude", "geocode", "address", "number", "district")
        read_only_fields = fields

    def get_geocode(self, obj):
        return obj.geocode_district_id

    def get_address(self, obj):
        return obj.short_address

    def get_number(self, obj):
        return obj.street2


class RecordCardFeaturesPublicSerializer(ElementDetailFeaturePublicSerializer):
    class Meta:
        model = RecordCardFeatures
        fields = ("id", "type", "title", "special", "mask", "options")
        read_only_fields = fields

    def get_special(self, obj):
        return False


class RecordCardSpecialFeaturesPublicSerializer(ElementDetailFeaturePublicSerializer):
    class Meta:
        model = RecordCardSpecialFeatures
        fields = ("id", "type", "title", "special", "mask", "options")
        read_only_fields = fields

    def get_special(self, obj):
        return True


class RecordCardRetrievePublicSerializer(CloseCancelDateMixin, serializers.ModelSerializer):
    incidenceId = serializers.SerializerMethodField()
    code = serializers.SerializerMethodField()
    stateId = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()
    transaction = serializers.SerializerMethodField()
    task = serializers.SerializerMethodField()
    characteristics = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    pictures = serializers.SerializerMethodField()
    average_close_days = serializers.IntegerField(source="element_detail.average_close_days")
    close_cancel_date = serializers.SerializerMethodField()
    address_mobile_email = serializers.SerializerMethodField()

    class Meta:
        model = RecordCard
        fields = ("incidenceId", "code", "stateId", "state", "comments", "transaction", "task", "characteristics",
                  "location", "pictures", "average_close_days", "close_cancel_date", "address_mobile_email")
        read_only_fields = fields

    def get_incidenceId(self, obj):
        return obj.pk

    def get_code(self, obj):
        return obj.normalized_record_id

    def get_stateId(self, obj):
        return obj.record_state_id

    def get_state(self, obj):
        return obj.record_state.description

    def get_transaction(self, obj):
        return TRANSACTION_URGENT if obj.urgent else TRANSACTION_NORMAL

    def get_comments(self, obj):
        return obj.description

    def get_task(self, obj):
        # TODO
        return {}

    def get_characteristics(self, obj):
        characteristics = []

        for recordcard_feature in obj.recordcardfeatures_set.all():
            characteristics.append(RecordCardFeaturesPublicSerializer(recordcard_feature).data)

        for recordcard_specialfeature in obj.recordcardspecialfeatures_set.all():
            characteristics.append(RecordCardSpecialFeaturesPublicSerializer(recordcard_specialfeature).data)

        return characteristics

    def get_location(self, obj):
        if obj.ubication and obj.ubication.enabled:
            return UbicationPublicSerializer(instance=obj.ubication).data
        return {}

    def get_pictures(self, obj):
        return [RecordFilePublicSerializer(instance=record_file).data for record_file in obj.recordfile_set.all()]

    def get_address_mobile_email(self, obj):
        return obj.recordcardresponse.address_mobile_email


class RecordFeatureCreatePublicSerializer(serializers.Serializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Feature.objects.all(),
        error_messages={"does_not_exist": _("The selected feature does not exist or is not enabled")})
    value = serializers.CharField()

    class Meta:
        fields = ("id", "value")

    def run_validation(self, data=empty):
        validated_data = super().run_validation(data)
        feature = validated_data["id"]
        errors = {}
        if feature.values_type:
            self.check_value(validated_data, feature, errors)

        if errors:
            raise ValidationError(errors, code="invalid")

        return validated_data

    @staticmethod
    def check_value(validated_data, feature, errors):
        validated_value = False
        possible_values = feature.values_type.values_set.filter(deleted__isnull=True).values(
            "id", "description_es", "description_en", "description_gl")
        for possible_value in possible_values:

            values = {str(v).strip().upper(): v for v in possible_value.values()}
            value = validated_data["value"].strip().upper()
            if value in values:
                validated_data["value"] = possible_value["id"]
                validated_value = True
                break

        if not validated_value:
            errors.update({"value": _("Value is not one of the feature options")})


class UbicationCreatePublicSerializer(UbicationValidationMixin, serializers.Serializer):
    id = serializers.IntegerField(allow_null=True, required=False)
    latitude = serializers.CharField(max_length=20, required=False, allow_blank=True)
    longitude = serializers.CharField(max_length=20, required=False, allow_blank=True)
    geocode = serializers.IntegerField(required=False, allow_null=True)
    via_type = serializers.CharField(max_length=35, required=False, allow_blank=True)
    address = serializers.CharField(max_length=120, required=False, allow_blank=True)
    number = serializers.CharField(max_length=60, required=False, allow_blank=True)
    stair = serializers.CharField(max_length=20, required=False, allow_blank=True)
    floor = serializers.CharField(max_length=20, required=False, allow_blank=True)
    door = serializers.CharField(max_length=20, required=False, allow_blank=True)
    district = serializers.PrimaryKeyRelatedField(
        queryset=District.objects.all(), required=False, allow_null=True,
        error_messages={"does_not_exist": _("The selected district does not exist")})

    @staticmethod
    def check_requires_ubication(validated_data, data_errors):
        """
        Check ubication required fields when element detail requires ubication

        :param validated_data: Dict with validated data of the serializer
        :param data_errors: dict for validation errors
        :return:
        """
        if not validated_data.get("address"):
            data_errors['address'] = _("Address is required with this Element Detail")
        if not validated_data.get("number"):
            data_errors['number'] = _("Number is required with this Element Detail")


class FeaturesValidationMixin:

    @staticmethod
    def features_validation(validated_data, element_detail_key, features_key, errors):
        """
        Validate characteristics set for the record card
        :param validated_data: valdiated data
        :param element_detail_key: element detail key
        :param features_key: feautres key
        :param errors: dict of errors from serializer
        :return:
        """
        element_detail = validated_data[element_detail_key]
        characteristics_ids = [characteristic.get("id").pk for characteristic
                               in validated_data.get(features_key, [])]

        # Check that all the mandatory features of the element detail are set into the record card
        for mandatory_feature in element_detail.feature_configs.get_public_mandatory_features_pk():
            if mandatory_feature not in characteristics_ids:
                errors[features_key] = [_("Mandatory characteristics missing")]

        # Check that all the features set on the record card are related to the element detail
        features_pk = element_detail.feature_configs.get_public_features_pk(allow_hidden=True)
        for characteristic in characteristics_ids:
            if characteristic not in features_pk:
                if features_key in errors:
                    errors[features_key].append(_("Characteristics not related to the detail"))
                else:
                    errors[features_key] = [_("Characteristics not related to the detail")]


class AttachmentsNumberValidationMixin:

    @staticmethod
    def check_attachments(validated_data, errors, attachments_key="pictures"):
        """
        Validate if the number of attachments respect the limit
        :param validated_data: validated data send to the endpoint
        :param errors: dict of errors from serializer
        :param attachments_key: key of attachments in serializer data
        :return:
        """
        max_files_numbers = int(Parameter.get_parameter_by_key("PUBLIC_API_MAX_FILES", 3))
        if len(validated_data.get(attachments_key, [])) > max_files_numbers:
            errors[attachments_key] = _("The number of attachments is greater than the number allowed")


class Base64AttachmentSerializer(CheckFileExtensionsMixin, serializers.Serializer):
    filename = serializers.CharField(max_length=50)
    data = serializers.CharField()

    def run_validation(self, data=empty):
        validated_data = super().run_validation(data)

        try:
            base64.b64decode(validated_data["data"])
        except binascii.Error:
            raise ValidationError({"data": _("Data is not a base64 valid string")}, code="invalid")

        return validated_data


class FileSerializer(CheckFileExtensionsMixin, serializers.Serializer):
    filename = serializers.CharField(max_length=30)
    file = serializers.FileField()

    @staticmethod
    def allowed_files_extensions():
        return Parameter.get_parameter_by_key("WEB_EXT_ANNEXOS", "jpg;jpeg;pdf;zip;rar;").split(";")


class RecordCardCreatePublicSerializer(FeaturesValidationMixin, AttachmentsNumberValidationMixin,
                                       serializers.Serializer):
    detailId = serializers.PrimaryKeyRelatedField(
        queryset=ElementDetail.objects.all(),
        error_messages={"does_not_exist": _("The selected element detail does not exist or is not enabled")})
    # created -> RecordCard.created_at -> auto add
    comments = serializers.CharField()
    transaction = serializers.CharField(required=False)
    device = serializers.PrimaryKeyRelatedField(
        queryset=Support.objects.all(), required=False,
        error_messages={"does_not_exist": _("The selected element detail does not exist or is not enabled")})
    applicant = serializers.PrimaryKeyRelatedField(
        queryset=Applicant.objects.all(), required=False,
        error_messages={"does_not_exist": _("The selected applicant does not exist or is not enabled")})

    nameCitizen = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    firstSurname = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    secondSurname = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    typeDocument = serializers.ChoiceField(required=False, allow_null=True, allow_blank=True, choices=Citizen.DOC_TYPES)
    numberDocument = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    birthYear = serializers.IntegerField(validators=[MinValueValidator(1900)], required=False, allow_null=True)
    sex = serializers.ChoiceField(required=False, allow_null=True, allow_blank=True, choices=Citizen.SEXES)

    socialReason = serializers.CharField(required=False, allow_null=True, allow_blank=True, max_length=60)
    contactPerson = serializers.CharField(required=False, allow_null=True, allow_blank=True, max_length=120)
    cif = serializers.CharField(required=False, allow_null=True, allow_blank=True, max_length=15)

    authorization = serializers.BooleanField(default=False, required=False)
    origin = serializers.CharField(required=False, default=RecordCard.ATE_PAGE_ORIGIN)

    district = serializers.ChoiceField(required=False, allow_null=True, allow_blank=True, choices=District.DISTRICTS)
    language = serializers.ChoiceField(required=False, allow_null=True, allow_blank=True, choices=LANGUAGES)
    email = serializers.EmailField(required=False, allow_null=True, allow_blank=True)
    telephone = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    characteristics = RecordFeatureCreatePublicSerializer(many=True, required=False)
    location = UbicationCreatePublicSerializer(required=False)
    pictures = FileSerializer(many=True, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['location'].context.update(self.context)

    def run_validation(self, data=empty):
        errors = {}
        validated_data = super().run_validation(data)
        self.features_validation(validated_data, "detailId", "characteristics", errors)

        element_detail = validated_data["detailId"]
        if element_detail.requires_ubication or element_detail.requires_ubication_district:
            if not validated_data.get("location"):
                errors['location'] = _("Address is required with this Element Detail")

        self.applicant_validation(validated_data, errors)

        if validated_data.get("transaction"):
            transaction = validated_data.get("transaction").upper()
            if transaction != TRANSACTION_URGENT and transaction != TRANSACTION_NORMAL:
                errors["transaction"] = _("Transaction value is not valid")

        self.check_attachments(validated_data, errors)

        if errors:
            raise ValidationError(errors)

        return validated_data

    def applicant_validation(self, validated_data, errors):
        """
        Validate applicant data
        :param validated_data: validated data send to the endpoint
        :param errors: dict of errors from serializer
        :return:
        """

        self.check_if_any_applicant(validated_data, errors)
        self.check_no_repeat_applicant(validated_data, errors)

        if validated_data.get("nameCitizen"):
            self.check_citizen_applicant(validated_data, errors)

        if validated_data.get("socialReason"):
            self.check_socialentity_applicant(validated_data, errors)

    @staticmethod
    def check_if_any_applicant(validated_data, errors):
        """
        Validate if any applicant data has been set
        :param validated_data: validated data send to the endpoint
        :param errors: dict of errors from serializer
        :return:
        """
        if not validated_data.get("applicant") and not validated_data.get("nameCitizen") and not \
                validated_data.get("socialReason"):
            errors["applicant"] = errors["nameCitizen"] = errors["socialReason"] = _("An applicant must be set")

    @staticmethod
    def check_no_repeat_applicant(validated_data, errors):
        """
        Validate that only one applicant has been set
        :param validated_data: validated data send to the endpoint
        :param errors: dict of errors from serializer
        :return:
        """
        error_message = _("Only one applicant can be set")
        if validated_data.get("applicant"):
            if validated_data.get("nameCitizen"):
                errors["nameCitizen"] = error_message
            if validated_data.get("socialReason"):
                errors["socialReason"] = error_message

        if validated_data.get("nameCitizen") and validated_data.get("socialReason"):
            errors["socialReason"] = error_message

    @staticmethod
    def check_required_field(parent_field_name, field_name, validated_data, errors):
        if not validated_data.get(field_name) and validated_data.get(field_name) != 0:
            errors[field_name] = _("If {} is set, {} must be set too".format(parent_field_name, field_name))

    def check_citizen_applicant(self, validated_data, errors):
        """
        Validate citizen data
        :param validated_data: validated data send to the endpoint
        :param errors: dict of errors from serializer
        :return:
        """
        parent_field_name = "nameCitizen"
        self.check_required_field(parent_field_name, "firstSurname", validated_data, errors)
        self.check_required_field(parent_field_name, "typeDocument", validated_data, errors)
        self.check_required_field(parent_field_name, "numberDocument", validated_data, errors)
        self.check_required_field(parent_field_name, "district", validated_data, errors)
        self.check_required_field(parent_field_name, "language", validated_data, errors)

    def check_socialentity_applicant(self, validated_data, errors):
        """
        Validate citizen data
        :param validated_data: validated data send to the endpoint
        :param errors: dict of errors from serializer
        :return:
        """
        parent_field_name = "socialReason"
        self.check_required_field(parent_field_name, "contactPerson", validated_data, errors)
        self.check_required_field(parent_field_name, "cif", validated_data, errors)
        self.check_required_field(parent_field_name, "language", validated_data, errors)


class RecordFilePublicSerializer(serializers.ModelSerializer):
    pictureId = serializers.SerializerMethodField()

    class Meta:
        model = RecordFile
        fields = ("pictureId", "filename")
        read_only_fields = fields

    def get_pictureId(self, obj):
        return obj.pk


class RecordCardCreatedPublicSerializer(serializers.ModelSerializer):
    incidenceId = serializers.SerializerMethodField()
    pictures = serializers.SerializerMethodField()
    text_es = serializers.SerializerMethodField()
    text_en = serializers.SerializerMethodField()
    text_gl = serializers.SerializerMethodField()

    class Meta:
        model = RecordCard
        fields = ("incidenceId", "pictures", "text_es", "text_en", "text_gl")
        read_only_fields = fields

    def get_incidenceId(self, obj):
        return obj.normalized_record_id

    def get_pictures(self, obj):
        return [RecordFilePublicSerializer(instance=record_file).data for record_file in obj.recordfile_set.all()]

    def get_text_es(self, obj):
        return obj.element_detail.footer_text_es if obj.element_detail.footer_text_es else ''

    def get_text_en(self, obj):
        return obj.element_detail.footer_text_en if obj.element_detail.footer_text_es else ''

    def get_text_gl(self, obj):
        return obj.element_detail.footer_text_gl if obj.element_detail.footer_text_es else ''


class RecordTypePublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecordType
        fields = ("id", "description")
        read_only_fields = fields


class ClaimResponseSerializer(serializers.Serializer):
    reference = serializers.CharField()
    reason = serializers.CharField()


class InputChannelPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = InputChannel
        fields = ("id", "description")
        read_only_fields = fields


class ApplicantTypePublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicantType
        fields = ("id", "description")
        read_only_fields = fields


class CitizenPublicSerializer(serializers.ModelSerializer):
    district_id = serializers.PrimaryKeyRelatedField(
        queryset=District.objects.all(),
        error_messages={"does_not_exist": _("The selected district does not exist")},
        required=False, allow_null=True)

    birth_year = serializers.IntegerField(validators=[MinValueValidator(1900), MaxYearValidator()], required=False,
                                          allow_null=True)

    class Meta:
        model = Citizen
        fields = ("id", "name", "first_surname", "second_surname", "sex", "doc_type", "dni", "birth_year",
                  "district_id", "language")


class SocialEntityPublicSerializer(serializers.ModelSerializer):
    district_id = serializers.PrimaryKeyRelatedField(
        queryset=District.objects.all(),
        error_messages={"does_not_exist": _("The selected district does not exist")},
        required=False, allow_null=True)

    class Meta:
        model = SocialEntity
        fields = ("id", "social_reason", "cif", "contact", "district_id", "language")


class UbicationMobileSerializer(UbicationValidationMixin, serializers.ModelSerializer):
    district_id = serializers.PrimaryKeyRelatedField(
        queryset=District.objects.filter(allow_derivation=True), required=False, allow_null=True, source="district",
        error_messages={"does_not_exist": _("The selected district does not exist")})
    number = serializers.CharField(source='street2', allow_blank=True)

    class Meta:
        model = Ubication
        fields = ("id", "geocode_validation", "street", "number", "stair", "floor", "door", "latitude", "longitude",
                  "district_id", "neighborhood", "neighborhood_b", "neighborhood_id", "statistical_sector")

    @staticmethod
    def check_requires_ubication(validated_data, data_errors):
        """
        Check ubication required fields when element detail requires ubication

        :param validated_data: Dict with validated data of the serializer
        :param data_errors: dict for validation errors
        :return:
        """
        if not validated_data.get("street"):
            data_errors['street'] = _("Street is required with this Element Detail")
        if not validated_data.get("street2"):
            data_errors['street2'] = _("Street2 is required with this Element Detail")


class RecordCardResponsePublicSerializer(RecordCardResponseValidationMixin, serializers.ModelSerializer):
    record_card_id = serializers.PrimaryKeyRelatedField(
        queryset=RecordCard.objects.filter(enabled=True), required=False, allow_null=True, source="record_card",
        error_messages={"does_not_exist": _("The selected RecordCard does not exist or is not enabled")})
    address_mobile_email = serializers.CharField()
    response_channel_id = serializers.PrimaryKeyRelatedField(
        queryset=ResponseChannel.objects.filter(enabled=True), source="response_channel",
        error_messages={"does_not_exist": _("The selected response channel does not exist")})
    language = serializers.ChoiceField(choices=LANGUAGES, required=False)

    class Meta:
        model = RecordCardResponse
        fields = ("address_mobile_email", "response_channel_id", "postal_code", "language", "record_card_id")

    def check_response_fields(self, response_channel_id, validated_data, validation_errors):
        if response_channel_id == ResponseChannel.LETTER and not validated_data.get("postal_code"):
            validation_errors["postal_code"] = _("This field is mandatory for giving an answer by Letter.")


class RecordCardMobileCreatePublicSerializer(FeaturesValidationMixin, AttachmentsNumberValidationMixin,
                                             serializers.Serializer):
    description = serializers.CharField()
    element_detail_id = serializers.PrimaryKeyRelatedField(
        queryset=ElementDetail.objects.all(), source='element_detail',
        error_messages={"does_not_exist": _("The selected element detail does not exist or is not enabled")})
    input_channel_id = serializers.PrimaryKeyRelatedField(
        queryset=InputChannel.objects.all(), source='input_channel',
        error_messages={"does_not_exist": _("The selected input channel does not exist or is not enabled")})
    applicant_type_id = serializers.PrimaryKeyRelatedField(
        queryset=ApplicantType.objects.all(), source='applicant_type',
        error_messages={"does_not_exist": _("The selected input channel does not exist or is not enabled")})

    citizen = CitizenPublicSerializer(required=False)
    social_entity = SocialEntityPublicSerializer(required=False)

    features = RecordFeatureCreatePublicSerializer(many=True, required=False)

    record_card_response = RecordCardResponsePublicSerializer(required=False)

    ubication = UbicationMobileSerializer()

    pictures = Base64AttachmentSerializer(many=True, required=False)
    organization = serializers.CharField(required=False, allow_blank=True, max_length=100)

    def __init__(self, instance=None, data=empty, **kwargs):
        super().__init__(instance, data, **kwargs)
        self.fields['ubication'].context.update(self.context)

    def run_validation(self, data=empty):
        errors = {}
        validated_data = super().run_validation(data)
        self.features_validation(validated_data, "element_detail", "features", errors)
        self.check_attachments(validated_data, errors)

        self.check_applicant(validated_data, errors)

        if errors:
            raise ValidationError(errors, code='invalid')
        return validated_data

    @staticmethod
    def check_applicant(validated_data, errors):
        """
        Validate applicant data

        :param validated_data: validated data send to the endpoint
        :param errors: dict of errors from serializer
        :return:
        """
        if validated_data.get("citizen") and validated_data.get("social_entity"):
            errors["citizen"] = _("Citizen and social entity can not be filled at the same time")
            errors["social_entity"] = _("Citizen and social entity can not be filled at the same time")

        if not validated_data.get("citizen") and not validated_data.get("social_entity"):
            errors["citizen"] = _("Citizen or social entity must be filled to create the RecordCard")
            errors["social_entity"] = _("Citizen or social entity must be filled to create the RecordCard")


class RecordCardMobileCreatedPublicSerializer(serializers.ModelSerializer):
    text_es = serializers.SerializerMethodField()
    text_en = serializers.SerializerMethodField()
    text_gl = serializers.SerializerMethodField()

    class Meta:
        model = RecordCard
        fields = ("normalized_record_id", "text_es", "text_en", "text_gl")
        read_only_fields = fields

    def get_text_es(self, obj):
        return obj.element_detail.head_text_es

    def get_text_en(self, obj):
        return obj.element_detail.head_text_en

    def get_text_gl(self, obj):
        return obj.element_detail.head_text_gl

    def record_message(self, record, language):
        if not record.element_detail.immediate_response:
            return ""

        old_lang = translation.get_language()
        translation.activate(language)
        message = _("Please note that the incidence will be transferred to the responsible department."
                    "The deadline to resolve is {} hours. With this information we respond to your request").format(
            record.element_detail.sla_hours)
        translation.activate(old_lang)
        return message


class MessageHashCreateSerializer(AttachmentsNumberValidationMixin, MessageCreateSerializer):
    check_involved_users = False
    post_data_keys = ["attachments"]

    attachments = FileSerializer(many=True, required=False)

    class Meta:
        model = Message
        fields = ("id", "created_at", "user_id", "conversation_id", "group_id", "record_state_id", "text",
                  "attachments")
        read_only_fields = ("id", "created_at", "user_id")

    def get_serializer_group(self):
        return get_anonymous_group()

    def set_alarms(self, instance):
        """
        Set alarms depending on who has sent the message and the conversation type
        :param instance: Message created
        :return:
        """
        record_card = instance.conversation.record_card
        if instance.conversation.type == Conversation.APPLICANT:
            conversation_alarms = RecordCardConversationAlarms(record_card, [Conversation.APPLICANT])
            record_card.pend_applicant_response = conversation_alarms.pend_response_responsible
            record_card.applicant_response = True
        else:
            # instance conversation type is Conversation.EXTERNAL
            conversation_alarms = RecordCardConversationAlarms(record_card,
                                                               [Conversation.INTERNAL, Conversation.EXTERNAL])
            record_card.pend_response_responsible = conversation_alarms.pend_response_responsible
            record_card.response_to_responsible = True
        record_card.alarm = True
        record_card.save()

    def run_validation(self, data=empty):
        errors = {}
        validated_data = super().run_validation(data)

        self.check_attachments(validated_data, errors, attachments_key="attachments")

        if errors:
            raise ValidationError(errors)

        return validated_data


class MessageShortHashSerializer(ModelSerializer):
    class Meta:
        model = Message
        fields = ("text",)


class ParameterPublicSerializer(ModelSerializer):
    class Meta:
        model = Parameter
        fields = ("parameter", "valor", "description", "name")
        read_only_fields = fields


class RecordCardMinimalPublicSerializer(ModelSerializer):
    class Meta:
        model = RecordCard
        fields = ("id", "normalized_record_id")
        read_only_fields = fields
