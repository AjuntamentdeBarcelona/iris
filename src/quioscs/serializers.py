from rest_framework import serializers

from django.utils.translation import ugettext_lazy as _
from rest_framework.exceptions import ValidationError
from rest_framework.fields import empty

from features.models import Feature, ValuesType, Mask, Values
from features.serializers import FeatureSerializer, ValuesTypeSerializer, MaskSerializer, ValuesSerializer
from iris_masters.models import Application, District
from main.api.serializers import ManyToManyExtendedSerializer
from public_api.serializers import (RecordFeatureCreatePublicSerializer, FeaturesValidationMixin,
                                    AttachmentsNumberValidationMixin, Base64AttachmentSerializer)
from record_cards.models import RecordCard, Citizen
from record_cards.serializers import UbicationValidationMixin
from themes.models import ElementDetail, ElementDetailFeature, ElementDetailResponseChannel
from themes.serializers import ElementDetailResponseChannelSerializer, ElementDetailFeatureListSerializer


class ValuesQuioscSerializer(ValuesSerializer):
    class Meta:
        model = Values
        fields = ("id", "description")
        read_only_fields = fields


class ValuesTypeQuioscSerializer(ValuesTypeSerializer):
    class Meta:
        model = ValuesType
        fields = ("id", "description", "values")
        read_only_fields = fields

    def get_values(self, obj):
        return [ValuesQuioscSerializer(value).data for value in obj.values_set.filter(deleted__isnull=True)]


class MaskQuioscSerializer(MaskSerializer):
    class Meta:
        model = Mask
        fields = ("id", "description", "type")
        read_only_fields = fields


class FeatureQuioscSerializer(FeatureSerializer):
    values_type = ValuesTypeQuioscSerializer(read_only=True)
    mask = MaskQuioscSerializer(read_only=True)

    class Meta:
        model = Feature
        fields = ("id", "description", "values_type", "mask", "explanatory_text")
        read_only_fields = fields


class ElementDetailFeatureQuioscSerializer(ElementDetailFeatureListSerializer):
    feature = FeatureQuioscSerializer()

    class Meta:
        model = ElementDetailFeature
        fields = ("feature", "order", "is_mandatory")
        read_only_fields = fields


class ElementDetailQuioscsSerializer(serializers.ModelSerializer):
    area_id = serializers.SerializerMethodField()
    area_description = serializers.SerializerMethodField()
    element_id = serializers.SerializerMethodField()
    element_description = serializers.SerializerMethodField()
    record_type = serializers.SerializerMethodField()
    features = ManyToManyExtendedSerializer(source="feature_configs", required=False,
                                            **{"many_to_many_serializer": ElementDetailFeatureQuioscSerializer,
                                               "model": ElementDetailFeature, "related_field": "element_detail",
                                               "to": "feature", "extra_values_params": ["order", "is_mandatory"],
                                               "extra_query_fields": {"feature__visible_for_citizen": True,
                                                                      "feature__editable_for_citizen": True}})
    response_channels = ManyToManyExtendedSerializer(
        source="elementdetailresponsechannel_set", required=False,
        **{"many_to_many_serializer": ElementDetailResponseChannelSerializer,
           "model": ElementDetailResponseChannel, "related_field": "elementdetail", "to": "responsechannel",
           "extra_query_fields": {"application_id": Application.IRIS_PK}})

    class Meta:
        model = ElementDetail
        fields = ("id", "description", "area_id", "area_description", "element_id", "element_description",
                  "record_type", "features", "response_channels", "requires_ubication", "immediate_response")
        read_only_fields = fields

    def get_area_id(self, obj):
        return obj.element.area.pk

    def get_area_description(self, obj):
        return obj.element.area.description

    def get_element_id(self, obj):
        return obj.element.pk

    def get_element_description(self, obj):
        return obj.element.description

    def get_record_type(self, obj):
        return obj.record_type.description if obj.record_type else ""


class UbicationQuioscsSerializer(UbicationValidationMixin, serializers.Serializer):
    geocode = serializers.CharField(required=False, allow_blank=True)
    via_type = serializers.CharField(max_length=120, required=False, allow_blank=True)
    street = serializers.CharField(max_length=120, required=False, allow_blank=True)
    number = serializers.CharField(max_length=60, required=False, allow_blank=True)
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
        if not validated_data.get("via_type"):
            data_errors["via_type"] = _("Via type is required with this Element Detail")
        if not validated_data.get("street"):
            data_errors["street"] = _("Street is required with this Element Detail")
        if not validated_data.get("number"):
            data_errors["number"] = _("Number is required with this Element Detail")


class RecordCardCreateQuioscsSerializer(FeaturesValidationMixin, AttachmentsNumberValidationMixin,
                                        serializers.Serializer):
    description = serializers.CharField()
    document_type = serializers.ChoiceField(choices=Citizen.DOC_TYPES)
    document = serializers.CharField()
    email = serializers.EmailField(allow_blank=True, required=False, allow_null=True)
    element_detail_id = serializers.PrimaryKeyRelatedField(
        queryset=ElementDetail.objects.filter(**ElementDetail.ENABLED_ELEMENTDETAIL_FILTERS),
        error_messages={"does_not_exist": _("The selected element detail does not exist or is not enabled")})
    features = RecordFeatureCreatePublicSerializer(many=True, required=False)
    location = UbicationQuioscsSerializer(required=False)
    pictures = Base64AttachmentSerializer(many=True, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["location"].context.update(self.context)

    def run_validation(self, data=empty):
        errors = {}
        validated_data = super().run_validation(data)
        self.features_validation(validated_data, "element_detail_id", "features", errors)
        self.check_attachments(validated_data, errors)

        element_detail = validated_data["element_detail_id"]
        if element_detail.requires_ubication or element_detail.requires_ubication_district:
            if not validated_data.get("location"):
                errors['location'] = _("Address is required with this Element Detail")
        if errors:
            raise ValidationError(errors)

        return validated_data


class RecordCardQuioscSerializer(serializers.ModelSerializer):
    element_detail = serializers.SerializerMethodField()
    resolution_time = serializers.SerializerMethodField()

    class Meta:
        model = RecordCard
        fields = ("id", "element_detail", "description", "normalized_record_id", "resolution_time")
        read_only_fields = fields

    def get_element_detail(self, obj):
        return obj.element_detail.description

    def get_resolution_time(self, obj):
        if obj.element_detail.immediate_response:
            return None
        return obj.ans_limit_date if obj.ans_limit_date else None
