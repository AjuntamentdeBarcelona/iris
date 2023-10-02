from django.utils.translation import ugettext_lazy as _
from drf_yasg.utils import swagger_serializer_method

from rest_framework import serializers

from iris_masters.models import (Announcement, InputChannel, InputChannelApplicantType, InputChannelSupport, Parameter,
                                 Process, RecordState, RecordType, ResponseChannel, ResponseChannelSupport, Support,
                                 District, ResolutionType, ExternalService, CommunicationMedia, MediaType, Reason,
                                 ResponseType, ApplicantType, FurniturePickUp, LetterTemplate)
from main.api.serializers import (IrisSerializer, ManyToManyExtendedSerializer, SerializerUpdateExtraMixin,
                                  SerializerCreateExtraMixin)
from main.api.validators import BulkUniqueRelatedValidator


class DummySerializer(serializers.Serializer):
    pass


def master_serializer_factory(mdl, extra_fields=None, extra_readonly_fields=None):
    class MasterSerializer(SerializerCreateExtraMixin, IrisSerializer):
        class Meta:
            model = mdl
            fields = ("id", "user_id", "created_at", "updated_at", "description")
            fields = fields + extra_fields if extra_fields else fields
            read_only_fields = ("id", "user_id", "created_at", "updated_at")
            read_only_fields = read_only_fields + extra_readonly_fields if extra_readonly_fields else read_only_fields

    MasterSerializer.__name__ = f"{mdl.__name__}Serializer"
    return MasterSerializer


MediaTypeSerializer = master_serializer_factory(MediaType)
ReasonSerializer = master_serializer_factory(Reason, ("reason_type", "can_delete"))


class ApplicantTypeSerializer(SerializerCreateExtraMixin, IrisSerializer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validators = [
            BulkUniqueRelatedValidator(
                main_fields=["description"], filter_fields=(), queryset=ApplicantType.objects.all(),
                message=_("The description must be unique and there is another ApplicantType with the same.")
            )
        ]

    class Meta:
        model = ApplicantType
        fields = ("id", "user_id", "created_at", "updated_at", "description", "order", "send_response", "can_delete")
        read_only_fields = ("id", "user_id", "created_at", "updated_at", "can_delete")


class ResponseTypeSerializer(SerializerCreateExtraMixin, IrisSerializer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validators = [
            BulkUniqueRelatedValidator(
                main_fields=["description"], filter_fields=(), queryset=ResponseType.objects.all(),
                message=_("The description must be unique and there is another ResponseType with the same.")
            )
        ]

    class Meta:
        model = ResponseType
        fields = ("id", "user_id", "created_at", "updated_at", "description", "can_delete")
        read_only_fields = ("id", "user_id", "created_at", "updated_at", "can_delete")


class ResponseTypeShortSerializer(ResponseTypeSerializer):
    class Meta:
        model = ResponseType
        fields = ("id", "user_id", "created_at", "updated_at", "description")
        read_only_fields = ("id", "user_id", "created_at", "updated_at")


class RecordTypeSerializer(SerializerCreateExtraMixin, IrisSerializer):
    templates = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validators = [
            BulkUniqueRelatedValidator(
                main_fields=[field for field in self.get_translation_fields("description")],
                filter_fields=(), queryset=RecordType.objects.all(),
                message=_("The description must be unique and there is another RecordType with the same.")
            )
        ]

    class Meta:
        model = RecordType
        fields = ("id", "user_id", "created_at", "updated_at", "description", "tri", "trt", "templates", "can_delete")
        read_only_fields = ("id", "user_id", "created_at", "updated_at", "templates", "can_delete")

    @swagger_serializer_method(serializer_or_field=serializers.ListField)
    def get_templates(self, obj):
        return [template_rec.iris_template.description for template_rec in obj.iristemplaterecordtypes_set.filter(
            enabled=True).select_related("iris_template")]


class ShortRecordTypeSerializer(RecordTypeSerializer):
    class Meta:
        model = RecordType
        fields = ("id", "user_id", "created_at", "updated_at", "description", "tri", "trt", "can_delete")
        read_only_fields = fields


class ReassignationReasonSerializer(ReasonSerializer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validators = [
            BulkUniqueRelatedValidator(
                main_fields=["description"], filter_fields=(), queryset=Reason.objects.all(),
                message=_("The description must be unique and there is another RecordType with the same.")
            )
        ]


class CancelReasonSerializer(ReassignationReasonSerializer):
    """
    CancelReason must define additional information about which field require in order to perform the cancel.
    """
    require_applicant_record_card = serializers.SerializerMethodField(
        help_text="When a record card is cancelled due to duplicity, another record card from the same "
                  "applicant must be given."
    )

    def get_require_applicant_record_card(self, obj):
        duplicity_repetition_reason_id = int(Parameter.get_parameter_by_key("DEMANAR_FITXA", 1))
        return obj.id == duplicity_repetition_reason_id

    class Meta(ReasonSerializer.Meta):
        fields = ReasonSerializer.Meta.fields + ("require_applicant_record_card",)


class CommunicationMediaSerializer(SerializerCreateExtraMixin, serializers.ModelSerializer):
    can_delete = serializers.BooleanField(source="can_be_deleted", required=False, read_only=True)

    media_type_id = serializers.PrimaryKeyRelatedField(
        source="media_type",
        queryset=MediaType.objects.filter(enabled=True),
        error_messages={
            "does_not_exist": _("The selected Media Type does not exists"),
        }
    )
    media_type = MediaTypeSerializer(read_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validators = [
            BulkUniqueRelatedValidator(
                main_fields=["description"], filter_fields=(), queryset=CommunicationMedia.objects.all(),
                message=_("The description must be unique and there is another CommunicationMedia with the same.")
            )
        ]

    class Meta:
        model = CommunicationMedia
        fields = ("id", "user_id", "created_at", "updated_at", "description", "media_type", "media_type_id",
                  "can_delete")
        read_only_fields = ("id", "user_id", "created_at", "updated_at", "can_delete")


class RecordStateSerializer(SerializerCreateExtraMixin, serializers.ModelSerializer):
    class Meta:
        model = RecordState
        fields = ("id", "user_id", "description", "acronym", "enabled")


class ResponseChannelSerializer(SerializerCreateExtraMixin, serializers.ModelSerializer):
    class Meta:
        model = ResponseChannel
        fields = ("id", "name",)


class AnnouncementSerializer(SerializerCreateExtraMixin, IrisSerializer):
    seen = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = ("id", "user_id", "created_at", "updated_at", "description", "title", "expiration_date", "important",
                  "seen", "xaloc", "can_delete")
        read_only_fields = ("id", "user_id", "created_at", "updated_at")

    def get_seen(self, obj):
        if not hasattr(obj, "is_seen"):
            user = self.context["request"].user
            return obj.seen(user)
        return obj.is_seen


class ParameterSerializer(SerializerCreateExtraMixin, serializers.ModelSerializer):
    class Meta:
        model = Parameter
        fields = "__all__"
        read_only_fields = ("id", "user_id", "created_at", "updated_at", "parameter", "name",
                            "original_description", "show", "data_type", "visible", "category")

    def save(self, **kwargs):
        try:
            # Only parameter with show=True can be updated
            parameter = Parameter.objects.get(pk=self.initial_data["id"], show=True)
        except Parameter.DoesNotExist:
            return
        for attr, value in self.validated_data.items():
            setattr(parameter, attr, value)
        parameter.save()
        self.instance = parameter
        return parameter


class ParameterRegularSerializer(serializers.Serializer):
    parameter = serializers.CharField()
    valor = serializers.CharField()


class InputChannelSupportSerializer(serializers.ModelSerializer):
    description = serializers.StringRelatedField(source="support", read_only=True)
    communication_media_required = serializers.SerializerMethodField()
    register_required = serializers.SerializerMethodField()
    allow_nd = serializers.SerializerMethodField()

    class Meta:
        model = InputChannelSupport
        fields = ("support", "order", "description", "communication_media_required", "register_required", "allow_nd")

    def get_communication_media_required(self, obj):
        return obj.support.communication_media_required

    def get_register_required(self, obj):
        return obj.support.register_required

    def get_allow_nd(self, obj):
        return obj.support.allow_nd


class InputChannelApplicantTypeSerializer(serializers.ModelSerializer):
    description = serializers.StringRelatedField(source="applicant_type", read_only=True)

    class Meta:
        model = InputChannelApplicantType
        fields = ("applicant_type", "order", "description")


class InputChannelSerializer(SerializerCreateExtraMixin, SerializerUpdateExtraMixin, IrisSerializer):
    post_create_extra_actions = True

    supports = ManyToManyExtendedSerializer(source="inputchannelsupport_set", required=False,
                                            **{"many_to_many_serializer": InputChannelSupportSerializer,
                                               "model": InputChannelSupport, "related_field": "input_channel",
                                               "to": "support", "extra_values_params": ["order"]})

    applicant_types = ManyToManyExtendedSerializer(source="inputchannelapplicanttype_set", required=False,
                                                   **{"many_to_many_serializer": InputChannelApplicantTypeSerializer,
                                                      "model": InputChannelApplicantType,
                                                      "related_field": "input_channel",
                                                      "to": "applicant_type",
                                                      "extra_values_params": ["order"]})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validators = [
            BulkUniqueRelatedValidator(
                main_fields=["description"], filter_fields=(), queryset=InputChannel.objects.all(),
                message=_("The description must be unique and there is another CommunicationMedia with the same.")
            )
        ]

    class Meta:
        model = InputChannel
        fields = ("id", "user_id", "created_at", "updated_at", "description", "order", "visible", "supports",
                  "applicant_types", "can_delete", "can_be_mayorship")
        read_only_fields = ("id", "user_id", "created_at", "updated_at")

    def do_post_create_extra_actions(self, instance, validated_data):
        """
        Perform extra actions on create after the instance creation
        :param instance: Instance of the created object
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        self.set_supports(validated_data, related_instance=instance)
        self.set_applicant_types(validated_data, related_instance=instance)

    def do_extra_actions_on_update(self, validated_data):
        """
        Perform extra actions on update
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        self.set_supports(validated_data)
        self.set_applicant_types(validated_data)

    def set_supports(self, validated_data, related_instance=None):
        """
        Set related supports to input channel
        :param validated_data: Dict with validated data of the serializer
        :param related_instance: record card instance for RecordCardFeatures/SpecialFeatures creation
        :return:
        """
        if "supports" in self.initial_data:
            serializer_kwargs = {"many_to_many_serializer": InputChannelSupportSerializer,
                                 "model": InputChannelSupport, "related_field": "input_channel",
                                 "to": "support", "extra_values_params": ["order"]}
            if related_instance:
                serializer_kwargs["related_instance"] = related_instance
            ser = ManyToManyExtendedSerializer(source="inputchannelsupport_set", data=self.initial_data["supports"],
                                               **serializer_kwargs)
            ser.bind(field_name="", parent=self)
            if ser.is_valid():
                ser.save()
            validated_data.pop(ser.source, None)

    def set_applicant_types(self, validated_data, related_instance=None):
        """
        Set related applicant_types to input channel
        :param validated_data: Dict with validated data of the serializer
        :param related_instance: record card instance for RecordCardFeatures/SpecialFeatures creation
        :return:
        """
        if "applicant_types" in self.initial_data:

            serializer_kwargs = {"many_to_many_serializer": InputChannelApplicantTypeSerializer,
                                 "model": InputChannelApplicantType, "related_field": "input_channel",
                                 "to": "applicant_type",
                                 "extra_values_params": ["order"]}
            if related_instance:
                serializer_kwargs["related_instance"] = related_instance

            ser = ManyToManyExtendedSerializer(source="inputchannelapplicanttype_set",
                                               data=self.initial_data["applicant_types"],
                                               **serializer_kwargs)
            ser.bind(field_name="", parent=self)
            if ser.is_valid():
                ser.save()
            validated_data.pop(ser.source, None)


class InputChannelShortSerializer(InputChannelSerializer):
    class Meta:
        model = InputChannel
        fields = ("id", "user_id", "created_at", "updated_at", "description", "order", "can_delete")
        read_only_fields = fields


class InputChannelExcelSerializer(InputChannelSerializer):
    visible = serializers.SerializerMethodField()
    permet_gabinet_alcaldia = serializers.SerializerMethodField()

    class Meta:
        model = InputChannel
        fields = ("description", "order", "visible", "permet_gabinet_alcaldia")
        read_only_fields = fields

    def get_visible(self, obj):
        return "Si" if obj.visible else "No"

    def get_permet_gabinet_alcaldia(self, obj):
        return "Si" if obj.can_be_mayorship else "No"


class InputChannelSupportRegularSerializer(serializers.Serializer):
    support = serializers.IntegerField(source="support_id")
    order = serializers.IntegerField()
    description = serializers.CharField(source="support.description")
    communication_media_required = serializers.BooleanField(source="support.communication_media_required")
    register_required = serializers.BooleanField(source="support.register_required")
    allow_nd = serializers.BooleanField(source="support.allow_nd")


class InputChannelApplicantTypeRegularSerializer(serializers.Serializer):
    applicant_type = serializers.IntegerField(source="applicant_type_id")
    order = serializers.IntegerField()
    description = serializers.CharField(source="applicant_type.description")


class InputChannelRegularSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    user_id = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    description = serializers.CharField()
    order = serializers.IntegerField()
    visible = serializers.BooleanField()
    supports = InputChannelSupportRegularSerializer(source="inputchannelsupport_set", many=True)
    applicant_types = InputChannelApplicantTypeRegularSerializer(source="inputchannelapplicanttype_set", many=True)
    can_be_mayorship = serializers.BooleanField()


class ResponseChannelSupportSerializer(serializers.ModelSerializer):
    description = serializers.StringRelatedField(source="response_channel", read_only=True)

    class Meta:
        model = ResponseChannelSupport
        fields = ("response_channel", "description")


class SupportSerializer(SerializerCreateExtraMixin, SerializerUpdateExtraMixin, IrisSerializer):
    response_channels = ManyToManyExtendedSerializer(source="responsechannelsupport_set", required=False,
                                                     **{"many_to_many_serializer": ResponseChannelSupportSerializer,
                                                        "model": ResponseChannelSupport, "related_field": "support",
                                                        "to": "response_channel"})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validators = [
            BulkUniqueRelatedValidator(
                main_fields=["description"], filter_fields=(), queryset=Support.objects.all(),
                message=_("The description must be unique and there is another Support with the same.")
            )
        ]

    class Meta:
        model = Support
        fields = ("id", "user_id", "created_at", "updated_at", "description", "order", "response_channels",
                  "allow_nd", "communication_media_required", "register_required", "can_delete")
        read_only_fields = ("id", "user_id", "created_at", "updated_at")

    def do_extra_actions_on_update(self, validated_data):
        """
        Perform extra actions on update
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        if "response_channels" in self.initial_data:
            ser = ManyToManyExtendedSerializer(source="responsechannelsupport_set",
                                               data=self.initial_data["response_channels"],
                                               **{"many_to_many_serializer": ResponseChannelSupportSerializer,
                                                  "model": ResponseChannelSupport, "related_field": "support",
                                                  "to": "response_channel"})
            ser.bind(field_name="", parent=self)
            if ser.is_valid():
                ser.save()
            validated_data.pop(ser.source, None)


class SupportShortSerializer(SupportSerializer):
    class Meta:
        model = Support
        fields = ("id", "description", "order", "allow_nd")
        read_only_fields = fields


class SupportExcelSerializer(SupportSerializer):
    permet_ciutada_nd = serializers.SerializerMethodField()
    requireix_mitja_comunicacio = serializers.SerializerMethodField()
    requereix_codi_registre = serializers.SerializerMethodField()

    class Meta:
        model = Support
        fields = ("description", "order", "permet_ciutada_nd", "requireix_mitja_comunicacio", "requereix_codi_registre")
        read_only_fields = fields

    def get_permet_ciutada_nd(self, obj):
        return "Si" if obj.allow_nd else "No"

    def get_requireix_mitja_comunicacio(self, obj):
        return "Si" if obj.communication_media_required else "No"

    def get_requereix_codi_registre(self, obj):
        return "Si" if obj.register_required else "No"


class ProcessSerializer(serializers.ModelSerializer):
    description = serializers.CharField(read_only=True, source="__str__")

    class Meta:
        model = Process
        fields = ("id", "description", "requires", "disabled")


class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        fields = "__all__"


class ResolutionTypeSerializer(SerializerCreateExtraMixin, IrisSerializer):
    description = serializers.CharField(max_length=40, min_length=3)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validators = [
            BulkUniqueRelatedValidator(
                main_fields=["description"], filter_fields=(), queryset=ResolutionType.objects.all(),
                message=_("The description must be unique and there is another ResolutionType with the same.")
            )
        ]

    class Meta:
        model = ResolutionType
        fields = ("id", "user_id", "created_at", "updated_at", "description", "order", "can_claim_inside_ans",
                  "can_delete")
        read_only_fields = ("id", "user_id", "created_at", "updated_at", "can_delete")


class ExternalServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalService
        fields = ("id", "sender_uid", "name", "active")


class FurniturePickUpSerializer(serializers.ModelSerializer):
    class Meta:
        model = FurniturePickUp
        fields = ("street_code", "number", "service_type", "service_description", "enterprise_name")


class LetterTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LetterTemplate
        fields = ("id", "user_id", "created_at", "updated_at", "description", "name", "enabled", "order")
        read_only_fields = fields


class RecordStateRegularSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    description = serializers.CharField()
    acronym = serializers.CharField()


class RecordTypeRegularSerializer(serializers.Serializer):
    description = serializers.CharField()
