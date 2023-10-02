from bs4 import BeautifulSoup
from django.conf import settings
from django.core.validators import RegexValidator
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from drf_chunked_upload.serializers import ChunkedUploadSerializer
from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import empty
from rest_framework.reverse import reverse

from ariadna.models import Ariadna, AriadnaRecord
from features.models import Values
from features.serializers import FeatureSerializer
from integrations.models import ExternalRecordId
from iris_masters.models import (ApplicantType, InputChannel, Reason, RecordState, ResponseChannel, Support,
                                 ResolutionType, CommunicationMedia, Parameter, InputChannelSupport)
from iris_masters.permissions import ADMIN
from iris_masters.serializers import (InputChannelSerializer, RecordStateSerializer, RecordTypeSerializer,
                                      SupportSerializer, SupportShortSerializer, InputChannelShortSerializer,
                                      CommunicationMediaSerializer, ApplicantTypeSerializer,
                                      RecordStateRegularSerializer, RecordTypeRegularSerializer,
                                      ShortRecordTypeSerializer, ResolutionTypeSerializer)
from main.api.serializers import (IrisSerializer, ManyToManyExtendedSerializer, SerializerCreateExtraMixin,
                                  SerializerUpdateExtraMixin, GetGroupFromRequestMixin)
from main.api.validators import WordsLengthValidator, WordsLengthAllowBlankValidator
from main.utils import LANGUAGES, SPANISH, ENGLISH, get_user_traceability_id
from profiles.models import GroupInputChannel, Group
from profiles.permissions import IrisPermissionChecker
from profiles.serializers import GroupShortSerializer, ResponsibleProfileRegularSerializer
from profiles.tasks import send_allocated_notification
from record_cards.permissions import (MAYORSHIP, RESP_CHANNEL_UPDATE, RESP_WORKED,
                                      RECARD_THEME_CHANGE_AREA, CITIZENS_DELETE, RECARD_MULTIRECORD,
                                      RECARD_REASSIGN_OUTSIDE)
from record_cards.record_actions.actions import RecordActions
from record_cards.record_actions.alarms import RecordCardAlarms
from record_cards.record_actions.normalized_reference import set_reference
from record_cards.record_actions.record_files import GroupManageFiles
from record_cards.record_actions.update_fields import RecordDictUpdateFields, UpdateComment
from reports.serializers import UbicationAttributeMixin
from themes.actions.possible_theme_change import PossibleThemeChange
from themes.models import ElementDetail, ElementDetailFeature
from themes.serializers import ElementDetailSerializer, ElementDetailShortSerializer, \
    ElementDetailDescriptionSerializer, ElementDetailRegularSerializer

from .models import (Applicant, ApplicantResponse, Citizen, Comment, RecordCard, RecordCardFeatures,
                     RecordCardResponse, RecordCardSpecialFeatures, Request, SocialEntity, Ubication,
                     RecordCardBlock, RecordCardTextResponse, RecordCardReasignation, Workflow, WorkflowComment,
                     WorkflowResolution, WorkflowPlan, RecordFile, RecordChunkedFile, InternalOperator,
                     RecordCardTextResponseFiles, WorkflowResolutionExtraFields)
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.response import Response

class UbicationValidationMixin:
    def run_validation(self, data=empty):
        validated_data = super().run_validation(data)

        element_detail = self.context.get("element_detail")
        if not element_detail:
            raise ValidationError({"non_field_errors": _("Element Detail is required for ubication validation")})

        data_errors = {}
        self.check_ubication_required_fields(validated_data, element_detail, data_errors)

        if data_errors:
            raise ValidationError(data_errors)

        return validated_data

    def check_ubication_required_fields(self, validated_data, element_detail, data_errors):
        """
        Check ubication required fields

        :param validated_data: Dict with validated data of the serializer
        :param element_detail: element detail to check data
        :param data_errors: dict for validation errors
        :return:
        """
        if element_detail.requires_ubication:
            self.check_requires_ubication(validated_data, data_errors)
        elif element_detail.requires_ubication_district:
            self.check_requires_district_ubication(validated_data, data_errors)

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
        if not validated_data.get("street2"):
            data_errors["street2"] = _("Street2 is required with this Element Detail")

    @staticmethod
    def check_requires_district_ubication(validated_data, data_errors):
        """
        Check ubication required fields when element detail requires district ubication

        :param validated_data: Dict with validated data of the serializer
        :param data_errors: dict for validation errors
        :return:
        """
        if not validated_data.get("district"):
            data_errors["district"] = _("District is required with this Element Detail")


class UbicationSerializer(SerializerCreateExtraMixin, UbicationValidationMixin, serializers.ModelSerializer):
    class Meta:
        model = Ubication
        fields = ("id", "via_type", "official_street_name", "street", "street2", "neighborhood", "neighborhood_b",
                  "neighborhood_id", "district", "statistical_sector", "geocode_validation", "geocode_district_id",
                  "research_zone", "stair", "floor", "door", "letter", "coordinate_x", "coordinate_y",
                  "coordinate_utm_x", "coordinate_utm_y", "latitude", "longitude", "xetrs89a", "yetrs89a",
                  "numbering_type")


class UbicationSerializerMobile(SerializerCreateExtraMixin, serializers.ModelSerializer):
    class Meta:
        model = Ubication
        fields = ("id", "via_type", "official_street_name", "street", "street2", "neighborhood", "neighborhood_b",
                  "neighborhood_id", "district", "statistical_sector", "geocode_validation", "geocode_district_id",
                  "research_zone", "stair", "floor", "door", "letter", "coordinate_x", "coordinate_y",
                  "coordinate_utm_x", "coordinate_utm_y", "latitude", "longitude", "xetrs89a", "yetrs89a",
                  "numbering_type", "letterFi", "numFi")

    def run_validation(self, data=empty):
        """
        We override the default `run_validation`, because the validation
        performed by validators and the `.validate()` method should
        be coerced into an error dictionary with a "non_fields_error" key.
        """

        return super().run_validation(data)


class UbicationShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ubication
        fields = ("id", "street", "street2", "xetrs89a", "yetrs89a", "district")
        read_only_fields = fields


class ApplicantCantDeleteMixin:
    # Mixin to control if a user can or can not delete an Applicant, Citizen or Social Entity item
    # A can_delete SerializerMethodField must be added to serializer

    def get_can_delete(self, obj):
        request = self.context.get("request")
        if not request:
            return False
        permission_checker = IrisPermissionChecker.get_for_user(request.user)
        return permission_checker.has_permission(CITIZENS_DELETE)


class CitizenSerializer(SerializerCreateExtraMixin, ApplicantCantDeleteMixin, GetGroupFromRequestMixin,
                        serializers.ModelSerializer):
    can_delete = serializers.SerializerMethodField()

    class Meta:
        model = Citizen
        fields = ("id", "user_id", "created_at", "updated_at", "name", "first_surname", "second_surname",
                  "full_normalized_name", "normalized_name", "normalized_first_surname", "normalized_second_surname",
                  "dni", "birth_year", "sex", "language", "response", "district", "doc_type", "mib_code", "blocked",
                  "can_delete")
        read_only_fields = ("id", "user_id", "created_at", "updated_at", "full_normalized_name", "normalized_name",
                            "normalized_first_surname", "normalized_second_surname", "response", "mib_code",
                            "can_delete")

    def __init__(self, instance=None, data=empty, **kwargs) -> None:
        super().__init__(instance, data, **kwargs)
        if self.instance:
            self.fields["dni"].read_only = True

    def validate(self, attrs):
        if not self.fields["dni"].read_only:
            citizen_pk = self.instance.pk if self.instance else None
            Citizen.check_no_repeat_dni(attrs.get("dni"), citizen_pk)
        return attrs

    def run_validation(self, data=empty):
        validated_data = super().run_validation(data)
        group = self.get_group_from_request(self.context["request"])
        validation_errors = {}
        if validated_data:
            dni = validated_data.get("dni")
            if dni and Applicant.is_nd_doc(dni) and not settings.CITIZEN_ND_ENABLED:
                validation_errors["dni"] = _("Citizen ND logic is not enabled, not allowed to create citizens with "
                                             "dni ND")
            if dni and Applicant.is_nd_doc(dni) and group.citizen_nd is False:
                validation_errors["dni"] = _("User group is not allowed to create citizens with dni ND")
            if not validated_data.get("language"):
                validation_errors["language"] = _("This field is required")
            if validation_errors:
                raise ValidationError(validation_errors, code="required")

        self.update_normalized_fields(validated_data)

        return validated_data

    @staticmethod
    def update_normalized_fields(validated_data):
        validated_data["normalized_name"] = validated_data.get("name", "")
        validated_data["normalized_first_surname"] = validated_data.get("first_surname", "")
        validated_data["normalized_second_surname"] = validated_data.get("second_surname", "")
        validated_data["full_normalized_name"] = "{} {} {}".format(validated_data.get("name", ""),
                                                                   validated_data.get("first_surname", ""),
                                                                   validated_data.get("second_surname", ""))


class CitizenRegularSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    first_surname = serializers.CharField()
    second_surname = serializers.CharField()
    dni = serializers.CharField()
    blocked = serializers.BooleanField()
    language = serializers.CharField()
    birth_year = serializers.IntegerField()


class SocialEntitySerializer(SerializerCreateExtraMixin, ApplicantCantDeleteMixin, serializers.ModelSerializer):
    can_delete = serializers.SerializerMethodField()

    class Meta:
        model = SocialEntity
        fields = ("id", "user_id", "created_at", "updated_at", "social_reason", "normal_social_reason", "contact",
                  "cif", "language", "response", "district", "mib_code", "blocked", "can_delete")
        read_only_fields = ("id", "user_id", "created_at", "updated_at", "normal_social_reason", "response", "mib_code",
                            "can_delete")

    def __init__(self, instance=None, data=empty, **kwargs) -> None:
        super().__init__(instance, data, **kwargs)
        if self.instance:
            self.fields["cif"].read_only = True

    def validate(self, attrs):
        if not self.fields["cif"].read_only:
            social_entity_pk = self.instance.pk if self.instance else None
            SocialEntity.check_no_repeat_cif(attrs.get("cif"), social_entity_pk)
        return attrs

    def run_validation(self, data=empty):
        validated_data = super().run_validation(data)
        if validated_data and not validated_data.get("language"):
            raise ValidationError({"language": _("This field is required")}, code="required")
        return validated_data


class SocialEntityRegularSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    cif = serializers.CharField()
    social_reason = serializers.CharField()
    blocked = serializers.BooleanField()
    language = serializers.CharField()
    contact = serializers.CharField()


class ApplicantResponseSerializer(SerializerCreateExtraMixin, serializers.ModelSerializer):
    class Meta:
        model = ApplicantResponse
        fields = "__all__"
        read_only_fields = ("id", "user_id", "created_at", "updated_at")

    @property
    def data(self):
        data = super().data
        data.update({"send_response": self.context.get("send_response", True)})
        return data


class ApplicantSerializer(SerializerCreateExtraMixin, SerializerUpdateExtraMixin, ApplicantCantDeleteMixin,
                          serializers.ModelSerializer):
    can_delete = serializers.SerializerMethodField()
    extra_actions = True

    citizen = CitizenSerializer(required=False, allow_null=True)
    social_entity = SocialEntitySerializer(required=False, allow_null=True)

    class Meta:
        model = Applicant
        fields = ("id", "user_id", "created_at", "updated_at", "flag_ca", "citizen", "social_entity", "can_delete",
                  "deleted")
        read_only_fields = ("id", "user_id", "created_at", "updated_at", "can_delete")

    def __init__(self, instance=None, data=empty, **kwargs):
        super().__init__(instance, data, **kwargs)

        if isinstance(instance, Applicant):
            self.fields["citizen"].instance = instance.citizen
            self.fields["social_entity"].instance = instance.social_entity

    def validate(self, attrs):
        Applicant.check_citizen_social_entity_assignation(attrs.get("citizen"), attrs.get("social_entity"))
        return attrs

    def do_extra_actions_on_create(self, validated_data):
        """
        Perform extra actions on create
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        self.set_citizen_social_entity(validated_data)

    def do_extra_actions_on_update(self, validated_data):
        """
        Perform extra actions on update
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        self.set_citizen_social_entity(validated_data)

    def set_citizen_social_entity(self, validated_data):
        """
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        if self.initial_data.get("citizen"):
            try:
                citizen = Citizen.objects.get(pk=self.initial_data["citizen"]["id"])
            except (Citizen.DoesNotExist, KeyError):
                citizen = Citizen()
            for field, value in validated_data["citizen"].items():
                setattr(citizen, field, value)
            citizen.save()
            validated_data["citizen"] = citizen

        if self.initial_data.get("social_entity"):
            try:
                social_entity = SocialEntity.objects.get(pk=self.initial_data["social_entity"]["id"])
            except (SocialEntity.DoesNotExist, KeyError):
                social_entity = SocialEntity()

            for field, value in validated_data["social_entity"].items():
                setattr(social_entity, field, value)
            social_entity.save()
            validated_data["social_entity"] = social_entity


class ApplicantRegularSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    flag_ca = serializers.BooleanField()
    citizen = CitizenRegularSerializer(required=False, allow_null=True)
    social_entity = SocialEntityRegularSerializer(required=False, allow_null=True)


class RequestSerializer(SerializerCreateExtraMixin, serializers.ModelSerializer):
    applicant_id = serializers.PrimaryKeyRelatedField(
        source="applicant", queryset=Applicant.objects.all(),
        error_messages={"does_not_exist": _("The selected record_type does not exist or is not enabled")})
    applicant = ApplicantSerializer(read_only=True)

    class Meta:
        model = Request
        fields = ("id", "user_id", "created_at", "updated_at", "enabled", "normalized_id", "applicant", "applicant_id",
                  "applicant_type", "application", "input_channel", "communication_media")
        read_only_fields = ("id", "user_id", "created_at", "updated_at")


class InternalOperatorSerializer(SerializerCreateExtraMixin, serializers.ModelSerializer):
    can_delete = serializers.BooleanField(source="can_be_deleted", required=False, read_only=True)

    applicant_type = ApplicantTypeSerializer(read_only=True)
    applicant_type_id = serializers.PrimaryKeyRelatedField(
        source="applicant_type", queryset=ApplicantType.objects.all(),
        error_messages={"does_not_exist": _("The selected applicant type does not exist or is not enabled")})
    input_channel = InputChannelSerializer(read_only=True)
    input_channel_id = serializers.PrimaryKeyRelatedField(
        source="input_channel", queryset=InputChannel.objects.all(),
        error_messages={"does_not_exist": _("The selected input_channel does not exist or is not enabled")})

    class Meta:
        model = InternalOperator
        fields = ("id", "user_id", "document", "applicant_type", "applicant_type_id", "input_channel",
                  "input_channel_id", "can_delete")
        read_only_fields = ("id", "user_id", "applicant_type", "input_channel", "can_delete")

    def run_validation(self, data=empty):

        try:
            validated_data = super().run_validation(data)
        except ValidationError as e:
            if self._check_unique_validation_error(e.detail.get("non_field_errors", [])):
                raise ValidationError({"non_field_errors": _("The internal operator alredy exists")})
            else:
                raise e

        validation_errors = {}
        self.check_internal_operator_repeated(validated_data, validation_errors)
        if validation_errors:
            raise ValidationError(validation_errors)
        return validated_data

    @staticmethod
    def _check_unique_validation_error(non_field_errors):
        for error in non_field_errors:
            if error.code == "unique":
                return True
        return False

    def check_internal_operator_repeated(self, validated_data, validation_errors):
        exclude_kwargs = {}
        if self.instance:
            exclude_kwargs["pk"] = self.instance.pk
        internal_operators = InternalOperator.objects.filter(
            document__iexact=validated_data["document"],
            applicant_type=validated_data["applicant_type"],
            input_channel=validated_data["input_channel"]
        )
        if internal_operators.exclude(**exclude_kwargs).exists():
            validation_errors.update({"document": _("This combination has alredy been set")})


class RecordCardFeaturesSerializer(serializers.ModelSerializer):
    description = serializers.StringRelatedField(source="feature", read_only=True)

    class Meta:
        model = RecordCardFeatures
        fields = ("feature", "value", "description")


class RecordCardSpecialFeaturesSerializer(serializers.ModelSerializer):
    description = serializers.StringRelatedField(source="feature", read_only=True)

    class Meta:
        model = RecordCardSpecialFeatures
        fields = ("feature", "value", "description")


class CommentSerializer(SerializerCreateExtraMixin, serializers.ModelSerializer):
    extra_actions = True

    class Meta:
        model = Comment
        fields = ("id", "user_id", "created_at", "updated_at", "group", "reason", "record_card", "enabled", "comment")
        read_only_fields = ("id", "user_id", "created_at", "updated_at")

    def do_extra_actions_on_create(self, validated_data):
        """
        Perform extra actions on create
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        request = self.context.get("request")
        user = request.user
        validated_data["group"] = user.usergroup.group if request and hasattr(user, "usergroup") else None


class RecordCardTextResponseFilesSerializer(SerializerCreateExtraMixin, serializers.ModelSerializer):
    filename = serializers.StringRelatedField(source="record_file.filename", read_only=True)
    file = serializers.FileField(source="record_file.file", read_only=True)

    class Meta:
        model = RecordCardTextResponseFiles
        fields = ("record_file", "filename", "file")


class RecordCardTextResponseSerializer(SerializerCreateExtraMixin, SerializerUpdateExtraMixin,
                                       serializers.ModelSerializer):
    post_create_extra_actions = True

    send_date = serializers.DateField(input_formats=("%Y-%m-%d",))
    notify_quality = serializers.BooleanField(default=False, required=False)
    avoid_send = serializers.BooleanField(default=False, required=False)
    record_files = ManyToManyExtendedSerializer(source="recordcardtextresponsefiles_set", required=False,
                                                **{"many_to_many_serializer": RecordCardTextResponseFilesSerializer,
                                                   "model": RecordCardTextResponseFiles,
                                                   "related_field": "text_response", "to": "record_file"})

    class Meta:
        model = RecordCardTextResponse
        fields = ("id", "user_id", "created_at", "updated_at", "record_card", "response", "send_date", "worked",
                  "notify_quality", "record_files", "avoid_send")
        read_only_fields = ("id", "user_id", "created_at", "updated_at")

    def __init__(self, instance=None, data=empty, **kwargs):
        self.record_card = None
        if data is not empty and not data.get("record_card"):
            data["record_card"] = kwargs["context"]["record_card"].pk
            self.record_card = kwargs["context"].get("record_card")
        if instance:
            self.record_card = instance.record_card
            setattr(instance, "notify_quality", self.record_card.notify_quality is True)
        if not self.record_card and data is not empty and data.get("record_card"):
            self.record_card = RecordCard.objects.get(id=data.get("record_card"))
        super().__init__(instance, data, **kwargs)

    def save(self, **kwargs):
        if self.record_card:
            self.record_card.notify_quality = self.validated_data.pop("notify_quality", False)
            self.record_card.save(update_fields=['notify_quality'])
        return super().save(**kwargs)

    def run_validation(self, data=empty):
        validated_data = super().run_validation(data)
        validation_errors = {}
        self.check_worked(validated_data, validation_errors)
        self.check_response_files(validated_data, validation_errors)
        if validation_errors:
            raise ValidationError(validation_errors, code="invalid")
        return validated_data

    def check_worked(self, validated_data, validation_errors):
        """
        Check worked field and if user has permissions to set it

        :param validated_data: Dict with validated data of the serializer
        :param validation_errors: dict for validation errors
        :return:
        """
        if validated_data.get("worked"):
            request = self.context.get("request")
            if request and not IrisPermissionChecker.get_for_user(request.user).has_permission(RESP_WORKED):
                validation_errors["worked"] = _("User has no permission to set this attribute")

    def check_response_files(self, validated_data, validation_errors):
        """
        Check response files to ensure that all are related to the same record_card

        :param validated_data: Dict with validated data of the serializer
        :param validation_errors: dict for validation errors
        :return:
        """
        record_card = validated_data["record_card"]
        text_response_files = validated_data.get("recordcardtextresponsefiles_set", [])
        if text_response_files:
            if record_card.recordcardresponse.response_channel_id not in ResponseChannel.ALLOW_ATTACHMENTS_CHANNELS:
                validation_errors["record_files"] = _("RecordCard Response Response Channel does not allow attachments")

            mr_pk = record_card.workflow.main_record_card_id if record_card.workflow_id else record_card.pk
            accepted_record_ids = [record_card.pk, mr_pk]
            for text_response_file in text_response_files:
                if text_response_file["record_file"].record_card_id not in accepted_record_ids:
                    validation_errors["record_files"] = _("All files must be related to response's RecordCard")

    def do_post_create_extra_actions(self, instance, validated_data):
        """
        Perform extra actions on create after the instance creation
        :param instance: Instance of the created object
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        self.register_response_files(instance, validated_data)

    def do_extra_actions_on_update(self, validated_data):
        """
        Perform extra actions on update

        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        self.register_response_files(self.instance, validated_data)

    def register_response_files(self, related_instance, validated_data):
        """
        Perform extra actions on create after the instance creation
        :param related_instance: related response text instance to the files
        :param validated_data: Dict with validated data of the serializer
        :return:
        """

        if "record_files" in self.initial_data:
            serializer_kwargs = {
                "many_to_many_serializer": RecordCardTextResponseFilesSerializer, "model": RecordCardTextResponseFiles,
                "related_field": "text_response", "to": "record_file", "related_instance": related_instance
            }

            ser = ManyToManyExtendedSerializer(**serializer_kwargs, source="recordcardtextresponsefiles_set",
                                               data=self.initial_data["record_files"], context=self.context)
            ser.bind(field_name="", parent=self)
            if ser.is_valid():
                ser.save()
            validated_data.pop(ser.source, None)


class RecordCardResponseValidationMixin:

    def run_validation(self, data=empty):
        """
        Validate a simple representation and return the internal value.

        The provided data may be `empty` if no representation was included
        in the input.

        May raise `SkipField` if the field should not be included in the
        validated data.
        """
        validated_data = super().run_validation(data)
        response_channel_id = validated_data["response_channel"].pk
        validation_errors = {}

        if self.context.get("record_card_check", False):
            # Check RecordCard only during record creation or update
            record_card = validated_data.get("record_card")
            if not record_card:
                raise ValidationError({"record_card": _("RecordCard is required")})

            self.check_language(response_channel_id, record_card, validated_data, validation_errors)

            is_intenal_operator, send_response = self.check_applicant_send_response(record_card, validated_data)
            if is_intenal_operator:
                self.check_internal_operator_response_channels(send_response, validated_data, validation_errors)
            if send_response:
                self.check_record_card(record_card, validated_data, validation_errors)

        self.check_response_fields(response_channel_id, validated_data, validation_errors)

        if validation_errors:
            raise ValidationError(validation_errors, code="invalid")

        return validated_data

    @staticmethod
    def check_language(response_channel_id, record_card, validated_data, validation_errors):
        # If response channel is none or inmmediate, there's no reason to check the language
        if response_channel_id in ResponseChannel.NON_RESPONSE_CHANNELS:
            return

        language = validated_data.get("language")
        if language:
            if language == ENGLISH and not record_card.element_detail.allow_english_lang:
                validation_errors["language"] = _("RecordCard Theme does not allow english language at response")

    def check_response_channel(self, response_channel_id, response_channels, validation_errors):
        """
        Check response channels

        :param response_channel_id: Response Channel id of record card response
        :param response_channels: Element detaul Response channels manager
        :param validation_errors: dict for validation errors
        :return:
        """
        if response_channel_id is None:
            validation_errors["response_channel"] = _("This field is required")

        response_channels_themes_ids = response_channels.filter(
            enabled=True, responsechannel__enabled=True).values_list("responsechannel_id", flat=True)
        if response_channel_id not in response_channels_themes_ids:
            validation_errors["response_channel"] = _("This response channel is not allowed for this record card theme")

    def check_record_card(self, record_card, validated_data, validation_errors):
        """
        Check record card response channels

        :param record_card: record card instance
        :param validated_data: Dict with validated data of the serializer
        :param validation_errors: dict for validation errors
        :return:
        """

        response_channel_id = validated_data["response_channel"].pk
        if not record_card.element_detail.immediate_response:
            self.check_response_channel(response_channel_id,
                                        record_card.element_detail.elementdetailresponsechannel_set,
                                        validation_errors)
        else:
            if response_channel_id not in ResponseChannel.IMMEDAIATE_RESPONSE_CHANNELS:
                validation_errors["response_channel"] = _("Response Channel not allowed for immediate response")
            validated_data['response_channel'] = ResponseChannel.objects.get(pk=ResponseChannel.IMMEDIATE)

    @staticmethod
    def check_applicant_send_response(record_card, validated_data):
        """
        If applicant is an internal operator, send response depends on applicant type

        If applicant document is ND (applicant generic) response channel must be ResponseChannel.None and
        send response must be set to False

        :param record_card: record card instance
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        if not record_card.request.applicant:
            return
        is_internal_operator = False
        send_response = True
        if record_card.request.applicant.is_internal_operator(record_card.applicant_type_id,
                                                              record_card.input_channel_id):
            is_internal_operator = True
            send_response = ApplicantType.get_send_response(record_card.applicant_type_id)

        if record_card.request.applicant.document == settings.CITIZEN_ND:
            validated_data["response_channel"] = ResponseChannel.objects.get(pk=ResponseChannel.NONE)
            send_response = False

        return is_internal_operator, send_response

    @staticmethod
    def check_internal_operator_response_channels(send_response, validated_data, validation_errors):
        """
        If record card applicant is internal operator:
        - if response has not to be sent response channel must be ResponseChannel.NONE
        - if response has to be sent, response channel could not be None

        :param send_response: boolean to indicate if the response has to be sent
        :param validated_data: Dict with validated data of the serializer
        :param validation_errors: dict for validation errors
        :return:
        """
        if not send_response:
            validated_data["response_channel"] = ResponseChannel.objects.get(pk=ResponseChannel.NONE)
        else:
            if validated_data["response_channel"].pk == ResponseChannel.NONE:
                validation_errors["response_channel"] = _("Response Channel can not be 'None' because applicant "
                                                          "is an internal operator that requires the response")

    def check_response_fields(self, response_channel_id, validated_data, validation_errors):
        raise NotImplementedError


class RecordCardResponseSerializer(SerializerCreateExtraMixin, RecordCardResponseValidationMixin,
                                   serializers.ModelSerializer):
    record_card = serializers.PrimaryKeyRelatedField(
        queryset=RecordCard.objects.filter(enabled=True),
        error_messages={
            "does_not_exist": _("The selected RecordCard does not exist or is not enabled"),
        },
        required=False, allow_null=True
    )

    language = serializers.ChoiceField(choices=LANGUAGES, required=False)

    class Meta:
        model = RecordCardResponse
        fields = ("id", "user_id", "created_at", "updated_at", "address_mobile_email", "number", "municipality",
                  "province", "postal_code", "answered", "enabled", "via_type", "via_name", "floor", "door", "stair",
                  "correct_response_data", "response_channel", "record_card", "language")
        read_only_fields = ("id", "user_id", "created_at", "updated_at")

    def __init__(self, instance=None, data=empty, **kwargs):
        self.multirecord_response_channel = kwargs.pop("multirecord_response_channel", None)
        super().__init__(instance, data, **kwargs)

    def check_response_fields(self, response_channel_id, validated_data, validation_errors):
        """
        Check response fields

        :param response_channel_id: Response Channel id of record card response
        :param validated_data: Dict with validated data of the serializer
        :param validation_errors: dict for validation errors
        :return:
        """
        if response_channel_id == ResponseChannel.EMAIL:
            if not validated_data.get("address_mobile_email"):
                validation_errors["address_mobile_email"] = _("This field is mandatory for giving an answer by email.")
        elif response_channel_id == ResponseChannel.SMS or response_channel_id == ResponseChannel.TELEPHONE:
            if not validated_data.get("address_mobile_email"):
                validation_errors["address_mobile_email"] = _("This field is mandatory for giving an answer"
                                                              " by SMS or Telephone.")
        elif response_channel_id == ResponseChannel.LETTER:
            self.check_letter_fields(validated_data, validation_errors)

    @staticmethod
    def check_letter_fields(validated_data, validation_errors):
        """
        Check letter fields

        :param validated_data: Dict with validated data of the serializer
        :param validation_errors: dict for validation errors
        :return:
        """
        error_message = _("This field is mandatory for giving an answer by Letter.")
        if not validated_data.get("address_mobile_email"):
            validation_errors["address_mobile_email"] = error_message
        if not validated_data.get("municipality"):
            validation_errors["municipality"] = error_message
        if not validated_data.get("province"):
            validation_errors["province"] = error_message
        if not validated_data.get("postal_code"):
            validation_errors["postal_code"] = error_message

    def check_response_channel(self, response_channel_id, response_channels, validation_errors):
        """
        Check response channels

        :param response_channel_id: Response Channel id of record card response
        :param response_channels: Element detaul Response channels manager
        :param validation_errors: dict for validation errors
        :return:
        """
        if response_channel_id is None:
            validation_errors["response_channel"] = _("This field is required")

        response_channels_themes_ids = response_channels.filter(
            enabled=True, responsechannel__enabled=True).values_list("responsechannel_id", flat=True)

        if self.invalid_response_channel(response_channel_id, response_channels_themes_ids):
            validation_errors["response_channel"] = _("This response channel is not allowed for this record card theme")

    def invalid_response_channel(self, response_channel_id, response_channels_themes_ids):
        if self.multirecord_response_channel:
            if response_channel_id != self.multirecord_response_channel \
                    and response_channel_id not in response_channels_themes_ids:
                return True
        else:
            if response_channel_id not in response_channels_themes_ids:
                return True
        return False


class RecordCardBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecordCardBlock
        fields = ("user_id", "record_card", "expire_time")
        read_only = fields


class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = AriadnaRecord
        fields = ("code",)


class RecordFeaturesBaseSerializer(serializers.ModelSerializer):
    features = ManyToManyExtendedSerializer(source="recordcardfeatures_set", required=False,
                                            **{"many_to_many_serializer": RecordCardFeaturesSerializer,
                                               "model": RecordCardFeatures, "related_field": "record_card",
                                               "to": "feature", "extra_values_params": ["value"],
                                               "extra_query_fields": {"is_theme_feature": True}})

    special_features = ManyToManyExtendedSerializer(source="recordcardspecialfeatures_set", required=False,
                                                    **{"many_to_many_serializer": RecordCardSpecialFeaturesSerializer,
                                                       "model": RecordCardSpecialFeatures, "to": "feature",
                                                       "related_field": "record_card", "extra_values_params": ["value"],
                                                       "extra_query_fields": {"is_theme_feature": True}})

    class Meta:
        model = RecordCard
        fields = ("features", "special_features")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validation_errors = {}

    def run_validation(self, data=empty):
        validated_data = super().run_validation(data)
        self.check_features(validated_data)
        return validated_data

    def set_features(self, validated_data, related_instance=None):
        """
        Set features from RecordCard
        :param validated_data: Dict with validated data of the serializer
        :param related_instance: record card instance for RecordCardFeatures/SpecialFeatures creation
        :return:
        """
        if "features" in self.initial_data:
            serializer_kwargs = {
                "many_to_many_serializer": RecordCardFeaturesSerializer, "model": RecordCardFeatures,
                "related_field": "record_card", "to": "feature", "extra_values_params": ["value"],
                "extra_data_params": ["feature__description", "feature__values_type", "is_theme_feature"]
            }
            if related_instance:
                serializer_kwargs["related_instance"] = related_instance

            ser = self.get_features_serializer_class()(**serializer_kwargs, source="recordcardfeatures_set",
                                                       data=self.initial_data["features"], context=self.context)
            ser.bind(field_name="", parent=self)
            if ser.is_valid():
                ser.save()
            validated_data.pop(ser.source, None)

    def set_special_features(self, validated_data, related_instance=None):
        """
        Set special features from RecordCard
        :param validated_data: Dict with validated data of the serializer
        :param related_instance: record card instance for RecordCardFeatures/SpecialFeatures creation
        :return:
        """

        if "special_features" in self.initial_data:
            serializer_kwargs = {
                "many_to_many_serializer": RecordCardSpecialFeaturesSerializer, "model": RecordCardSpecialFeatures,
                "related_field": "record_card", "to": "feature", "extra_values_params": ["value"],
                "extra_data_params": ["feature__description", "feature__values_type", "is_theme_feature"]
            }
            if related_instance:
                serializer_kwargs["related_instance"] = related_instance
            ser = self.get_features_serializer_class()(**serializer_kwargs, source="recordcardspecialfeatures_set",
                                                       data=self.initial_data["special_features"], context=self.context)
            ser.bind(field_name="", parent=self)
            if ser.is_valid():
                ser.save()
            validated_data.pop(ser.source, None)

    def check_features(self, validated_data):
        """
        Check record card features
        :param validated_data: Dict with validated data from the serializer
        :return:
        """

        if "features" in self.fields or "special_features" in self.fields:
            self._validate_features(validated_data)

    def _validate_features(self, validated_data):
        element_detail = validated_data.get("element_detail") or self.instance.element_detail
        features_to_check = self.initial_data.get("features", []) + self.initial_data.get("special_features", [])

        element_detail_features = element_detail.feature_configs.filter(
            enabled=True, feature__deleted__isnull=True).select_related("feature")
        if self._features_are_valid_for_theme(element_detail, element_detail_features, features_to_check):
            self._check_feature_values(element_detail_features, features_to_check)

    def _features_are_valid_for_theme(self, element_detail, element_detail_features, features_to_check):
        mandatory_features = [f for f in element_detail_features if f.is_mandatory or f.feature.is_special]
        if len(features_to_check) < len(mandatory_features):
            error_message = _("The number of features is not the required at the ElementDetail")
            self.validation_errors["features"] = error_message
            self.validation_errors["special_features"] = error_message
            return False
        else:
            # Check that all the features set on the record card are related to the element detail
            features_pks = element_detail.feature_configs.get_features_pk()
            errors_feature_list = self._check_features_related_to_detail(features_pks, "features")
            errors_specialfeature_list = self._check_features_related_to_detail(features_pks, "special_features")

            if errors_feature_list or errors_specialfeature_list:
                self.send_features_errors(errors_feature_list, errors_specialfeature_list)
                return
        return True

    def _check_feature_values(self, element_detail_features, features_to_check):
        errors_feature_list = []
        errors_specialfeature_list = []
        for elem_feature in element_detail_features:
            found = False
            for feature_dict in features_to_check:
                if int(feature_dict["feature"]) == elem_feature.feature.pk:
                    found = True
                    if elem_feature.is_mandatory and not feature_dict["value"]:
                        error_message = _("This feature is mandatory. Value must be set.")
                        self.set_feature_error(elem_feature, errors_feature_list, errors_specialfeature_list,
                                               error_message)
                    break
            if not found and (elem_feature.is_mandatory or elem_feature.feature.is_special):
                error_message = _("This feature must be set.")
                self.set_feature_error(elem_feature, errors_feature_list, errors_specialfeature_list, error_message)

        self.send_features_errors(errors_feature_list, errors_specialfeature_list)

    def _check_features_related_to_detail(self, features_pks, feature_field):
        errors_feature_list = []
        for characteristic in self.initial_data.get(feature_field, []):
            if int(characteristic["feature"]) not in features_pks:
                errors_feature_list.append({characteristic["feature"]: _("Characteristic not related to the detail")})
        return errors_feature_list

    def send_features_errors(self, errors_feature_list, errors_specialfeature_list):
        """
        Raise features errors if they exist
        :param errors_feature_list: list of feature errors
        :param errors_specialfeature_list: list of special features errors
        :return:
        """
        if errors_feature_list:
            self.validation_errors["features"] = errors_feature_list
        if errors_specialfeature_list:
            self.validation_errors["special_features"] = errors_specialfeature_list

    @staticmethod
    def set_feature_error(elem_feature, errors_feature_list, errors_specialfeature_list, error_message):
        """
        Register feature error
        :param elem_feature: elementFeature with error
        :param errors_feature_list: list of feature errors
        :param errors_specialfeature_list: list of special features errors
        :param error_message: Error message
        :return:
        """
        feature_error = {elem_feature.feature_id: error_message}
        if elem_feature.feature.is_special:
            errors_specialfeature_list.append(feature_error)
        else:
            errors_feature_list.append(feature_error)

    @staticmethod
    def get_features_serializer_class():
        """
        :return: Features serializer class
        """
        return ManyToManyExtendedSerializer


class RecordCardBaseSerializer(RecordFeaturesBaseSerializer, serializers.ModelSerializer):
    ubication = UbicationSerializer(required=False)

    recordcardresponse = RecordCardResponseSerializer()

    class Meta:
        model = RecordCard
        fields = ("ubication", "features", "special_features", "recordcardresponse")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.permission_checker = self.get_user_permission_checker()
        if "ubication" in self.fields:
            self.fields["ubication"].context.update(self.context)

    def get_user_permission_checker(self):
        """
        Get the permission checker object for the user
        :return: Permission Checke class
        """
        user = getattr(self.context.get("request"), "user", None)
        return IrisPermissionChecker.get_for_user(user) if user else None

    def set_ubication(self, validated_data):
        """
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        element_detail = self.context.get("element_detail")
        if not element_detail:
            raise ValidationError({"non_field_errors": _("Element Detail is required for ubication validation")})

        initial_ubication = self.initial_data.get("ubication")
        if element_detail.requires_ubication or element_detail.requires_ubication_district:
            if not initial_ubication:
                raise ValidationError({"ubication": _("Address is required with this Element Detail")})

        if initial_ubication:
            try:
                ubication = Ubication.objects.get(pk=initial_ubication["id"], enabled=True)
                ubication_serializer = UbicationSerializer(instance=ubication, data=initial_ubication,
                                                           context=self.context)
            except (Ubication.DoesNotExist, KeyError):
                ubication_serializer = UbicationSerializer(data=initial_ubication, context=self.context)
            ubication_serializer.is_valid(raise_exception=True)
            validated_data["ubication"] = ubication_serializer.save()


class RecordCardSerializer(SerializerCreateExtraMixin, SerializerUpdateExtraMixin, GetGroupFromRequestMixin,
                           RecordCardBaseSerializer, IrisSerializer):
    extra_actions = True
    post_create_extra_actions = True
    post_data_keys = ["recordcardresponse", "register_code"]

    record_type_id = serializers.PrimaryKeyRelatedField(
        source="record_type", read_only=True,
        error_messages={"does_not_exist": _("The selected record_type does not exist")})
    record_type = RecordTypeSerializer(read_only=True)

    input_channel_id = serializers.PrimaryKeyRelatedField(
        source="input_channel", queryset=InputChannel.objects.filter(visible=True),
        error_messages={"does_not_exist": _("The selected input_channel does not exist or is not enabled")})
    input_channel = InputChannelSerializer(read_only=True)

    support_id = serializers.PrimaryKeyRelatedField(
        source="support", queryset=Support.objects.all(),
        error_messages={"does_not_exist": _("The selected support does not exist or is not enabled")})
    support = SupportSerializer(read_only=True)

    element_detail_id = serializers.PrimaryKeyRelatedField(
        source="element_detail",
        queryset=ElementDetail.objects.filter(**ElementDetail.ENABLED_ELEMENTDETAIL_FILTERS),
        error_messages={"does_not_exist": _("The selected element_detail does not exist")})

    element_detail = ElementDetailSerializer(read_only=True)

    applicant_id = serializers.SerializerMethodField()

    request = RequestSerializer(read_only=True)

    record_state_id = serializers.PrimaryKeyRelatedField(
        source="record_state", read_only=True,
        error_messages={"does_not_exist": _("The selected record_state does not exist or is not enabled")},
    )
    record_state = RecordStateSerializer(read_only=True)

    communication_media_id = serializers.PrimaryKeyRelatedField(
        source="communication_media", queryset=CommunicationMedia.objects.all(), required=False,
        error_messages={"does_not_exist": _("The selected Communication Media does not exist or is not enabled")})
    communication_media = CommunicationMediaSerializer(read_only=True)

    comments = serializers.SerializerMethodField()

    applicant_type_id = serializers.PrimaryKeyRelatedField(
        source="applicant_type", queryset=ApplicantType.objects.all(),
        error_messages={"does_not_exist": _("The selected applicant type does not exist or is not enabled")})
    applicant_type = ApplicantTypeSerializer(read_only=True)

    blocked = serializers.SerializerMethodField()

    actions = serializers.SerializerMethodField()
    group_can_answer = serializers.SerializerMethodField()
    without_applicant = serializers.BooleanField(required=False, default=False)
    wont_tramit = serializers.BooleanField(required=False, default=False)

    multirecord_from = serializers.PrimaryKeyRelatedField(
        queryset=RecordCard.objects.filter(enabled=True), required=False, allow_null=True,
        error_messages={"does_not_exist": _("The selected RecordCard does not exist or is not enabled")})
    multirecord_copy_responsechannel = serializers.BooleanField(required=False)
    files = serializers.SerializerMethodField()
    register_code = serializers.CharField(validators=[RegexValidator(regex=r"^([0-9]){4}\/([0-9]){6}")], required=False)

    full_detail = serializers.SerializerMethodField()
    alarms = serializers.SerializerMethodField()

    creation_department = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = RecordCard
        fields = ("id", "user_id", "created_at", "updated_at", "description", "responsible_profile", "process",
                  "enabled", "mayorship", "normalized_record_id", "alarm", "auxiliary", "closing_date",
                  "ans_limit_date", "urgent", "communication_media_detail", "communication_media_date",
                  "record_parent_claimed", "reassignment_not_allowed", "page_origin", "email_external_derivation",
                  "user_displayed", "historicized", "allow_multiderivation", "start_date_process", "appointment_time",
                  "similar_process", "response_state", "notify_quality", "multi_complaint", "lopd",
                  "citizen_alarm", "ci_date", "support_numbers", "element_detail", "element_detail_id", "request",
                  "applicant_id", "ubication", "record_state", "record_state_id", "record_type", "record_type_id",
                  "applicant_type", "applicant_type_id", "communication_media", "communication_media_id", "support",
                  "support_id", "input_channel", "input_channel_id", "features", "special_features", "actions",
                  "alarms", "ideal_path", "current_step", "comments", "recordcardresponse", "blocked", "full_detail",
                  "multirecord_from", "is_multirecord", "multirecord_copy_responsechannel", "files", "register_code",
                  "group_can_answer", "creation_department", "without_applicant", "organization", "wont_tramit")
        read_only_fields = ("id", "user_id", "created_at", "updated_at", "normalized_record_id",
                            "ans_limit_date", "user_displayed", "record_state_id", "applicant_type", "record_type_id",
                            "actions", "ideal_path", "comments", "record_state", "responsible_profile", "alarms",
                            "start_date_process", "appointment_time", "current_step", "blocked", "is_multirecord")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance is None and hasattr(self, "initial_data"):
            if "applicant_id" in self.fields:
                self.fields["applicant_id"] = serializers.PrimaryKeyRelatedField(
                    queryset=Applicant.objects.all(), required=False,
                    error_messages={"does_not_exist": _("The selected applicant does not exist or is not enabled")})
            if self.initial_data.get("multirecord_from"):
                self.fields["input_channel_id"].required = False
                self.fields["input_channel_id"].queryset = InputChannel.objects.all()
                self.fields["support_id"].required = False
                self.fields["applicant_type_id"].required = False
                self.fields["recordcardresponse"] = RecordCardResponseSerializer(
                    multirecord_response_channel=self.get_multirecord_respchannel())
        self.ariadna = None

    def get_multirecord_respchannel(self):
        try:
            multirecord_from = RecordCard.objects.get(pk=self.initial_data["multirecord_from"])
            if hasattr(multirecord_from, "recordcardresponse"):
                return multirecord_from.recordcardresponse.response_channel_id
            else:
                return None
        except RecordCard.DoesNotExist:
            return None

    @swagger_serializer_method(serializer_or_field=RecordCardBlockSerializer)
    def get_blocked(self, obj):
        current_block = obj.current_block
        return RecordCardBlockSerializer(current_block).data if current_block else None

    @swagger_serializer_method(serializer_or_field=serializers.BooleanField)
    def get_full_detail(self, obj):
        return True

    @swagger_serializer_method(serializer_or_field=serializers.DictField)
    def get_alarms(self, obj):
        request = self.context.get("request")
        group = self.get_group_from_request(request)
        return RecordCardAlarms(obj, group).alarms

    @swagger_serializer_method(serializer_or_field=serializers.IntegerField)
    def get_applicant_id(self, obj):
        return obj.request.applicant.pk

    @swagger_serializer_method(serializer_or_field=serializers.ListField)
    def get_comments(self, obj):
        return [CommentSerializer(comment).data for comment in obj.comments.filter(enabled=True)]

    @swagger_serializer_method(serializer_or_field=serializers.DictField)
    def get_actions(self, obj):
        request = self.context.get("request")
        if request:
            return RecordActions(obj, request.user).actions()
        return {}

    @swagger_serializer_method(serializer_or_field=serializers.BooleanField)
    def get_group_can_answer(self, obj):
        request = self.context.get("request")
        if not request:
            return {"can_answer": False, "reason": _("Request not detected")}
        group = self.get_group_from_request(request)
        return obj.group_can_answer(group)

    @swagger_serializer_method(serializer_or_field=serializers.ListField)
    def get_files(self, obj):
        return [RecordFileShortSerializer(record_file).data for record_file in obj.recordfile_set.all()]

    def run_validation(self, data=empty):
        validated_data = super().run_validation(data)

        element_detail = validated_data.get("element_detail")
        if element_detail and self.context.get('validate_theme_active', True):
            if not element_detail.is_active:
                self.validation_errors["element_detail_id"] = _("Element Detail can not be used because is not active")

        self.check_communication_media(validated_data)
        self.check_input_channel(validated_data)
        self.check_mayorship(validated_data)
        self.check_applicant_in_record_creation(validated_data)
        self.check_citizen_nd(validated_data)
        self.check_register_code(validated_data)
        self.check_multirecord_from(validated_data)

        if self.context.get("request"):
            self.check_request_usergroup(validated_data)

        if self.validation_errors:
            raise ValidationError(self.validation_errors, code="invalid")

        return validated_data

    def check_input_channel(self, validated_data):
        """
        Check that input channel is not Quiosc
        If mayorshipt is set to True, check if input_channel allows mayorship flag

        :param validated_data: Dict with validated data from the serializer
        :return:
        """
        if validated_data.get("multirecord_from"):
            # If a multirecord card is being created, the input channel will be of the multirecord from
            return

        # View can skip this check for custom creation endpoints like surveys
        if not self.context.get('validate_group_input_channel', True):
            return
        input_channel = validated_data.get("input_channel")
        if input_channel:
            if input_channel.pk == InputChannel.QUIOSC:
                self.validation_errors["input_channel_id"] = _("Input Channel 'QUIOSC' can not be used in a "
                                                               "record creation/update")

            input_channel_pks = GroupInputChannel.objects.get_input_channels_from_group(
                self.context["request"].user.usergroup.group)
            if input_channel.pk not in input_channel_pks:
                self.validation_errors["input_channel_id"] = _("Input Channel is not allowed for user group")

            support = validated_data.get("support")
            if not InputChannelSupport.objects.filter(input_channel=input_channel, support=support).exists():
                self.validation_errors["support_id"] = _("Support is not allowed for the selected input channel")

            if validated_data.get("mayorship"):
                if not input_channel.can_be_mayorship:
                    self.validation_errors["mayorship"] = _("If input channel does not allow mayorship, "
                                                            "this can not be set to True")

    def check_communication_media(self, validated_data):
        """
        Check communication media data when support is "Communication Media"
        :param validated_data: Dict with validated data from the serializer
        :return:
        """
        support = validated_data.get("support")
        if support and support.pk == Support.COMMUNICATION_MEDIA:
            if not validated_data.get("communication_media"):
                self.validation_errors["communication_media"] = _("If support Communication Media has been selected, a "
                                                                  "comunication media has to be set")
            if not validated_data.get("communication_media_date"):
                self.validation_errors["communication_media_date"] = _("If support Communication Media has been "
                                                                       "selected, a the publish date has to be set")

    def check_register_code(self, validated_data):
        """
        Check ariadna's register code
        :param validated_data: Dict with validated data from the serializer
        :return:
        """
        if "register_code" not in validated_data:
            # There¡'s not register code to check
            return

        support = validated_data.get("support")
        register_code = validated_data.get("register_code")
        if support and support.register_required and not register_code:
            self.validation_errors["support_id"] = _("Register code is required for the selected support")

        try:
            self.ariadna = Ariadna.objects.get(code=register_code)
        except Ariadna.DoesNotExist:
            self.validation_errors["register_code"] = _("Register Code selected does not exist")

    def check_multirecord_from(self, validated_data):
        """
        Check the multirecord data
        :param validated_data: Dict with validated data from the serializer
        :return:
        """
        record_card_from = validated_data.get("multirecord_from")
        if record_card_from and not self.permission_checker.has_permission(RECARD_MULTIRECORD):
            raise ValidationError({'detail': _("User's group is not allowed to create multirecords")})

        if record_card_from and record_card_from.multirecord_from:
            self.validation_errors["multirecord_from"] = _("The RecordCard selected has alredy a multirecord")

    def check_applicant_in_record_creation(self, validated_data):
        """
        Check the required applicant id field on write operations

        :param validated_data: Dict with validated data from the serializer
        :return:
        """
        without_applicant = validated_data.pop("without_applicant", False)
        self.wont_tramit = validated_data.pop("wont_tramit", False)
        if without_applicant:
            return
        if isinstance(self.fields.get("applicant_id"), serializers.PrimaryKeyRelatedField):
            if self.instance is None and not validated_data.get("applicant_id"):
                self.validation_errors["applicant_id"] = _("Applicant id must be set")

            no_block_theme_pk = int(Parameter.get_parameter_by_key("TEMATICA_NO_BLOQUEJADA", 392))
            applicant = validated_data.get("applicant_id")
            if not applicant:
                self.validation_errors["applicant_id"] = _("Applicant is required")
                return
            element_detail = validated_data.get("element_detail")
            if applicant.blocked and no_block_theme_pk != element_detail.pk:
                self.validation_errors["applicant_id"] = _("Applicant can not be used to create a record because "
                                                           "it's blocked")

    def check_mayorship(self, validated_data):
        """
        Check that the user has permissions to set mayorship to true

        :param validated_data: Dict with validated data from the serializer
        :return:
        """

        if validated_data.get("mayorship") and not self.permission_checker.has_permission(MAYORSHIP):
            self.validation_errors["mayorship"] = _("User's group is not allowed to set mayorship")

    def check_request_usergroup(self, validated_data):
        """
        Check the configurations of the user's group
        :param validated_data: Dict with validated data from the serializer
        :return:
        """
        if not hasattr(self.context["request"].user, "usergroup"):
            self.validation_errors["non_field_errors"] = _("User without an assigned group can not create RecordCards")
            return

        if self.context["request"].user.usergroup.group.is_anonymous:
            self.validation_errors[
                "non_field_errors"] = _("User assigned to Anonymoys Group can not create RecordCards")

        if not validated_data.get("multirecord_from") and self.context.get('validate_group_input_channel', True):
            # The check has only to be done if the RecordCard is not a multirecord because
            # a multirecord card will have the same input channel that its parent record
            input_channels_group = GroupInputChannel.objects.get_input_channels_from_group(
                self.context["request"].user.usergroup.group)
            if validated_data.get("input_channel") and validated_data["input_channel"].pk not in input_channels_group:
                self.validation_errors["input_channel_id"] = _("InputChannel is not allowed to user's group")

    def check_citizen_nd(self, validated_data):
        """
        Check citizen ND configs
        :param validated_data: Dict with validated data from the serializer
        :return:
        """
        applicant = validated_data.get("applicant_id")
        if not applicant:
            # There's not applicant to check
            return

        if applicant.citizen and Applicant.is_nd_doc(applicant.citizen.dni):
            if not settings.CITIZEN_ND_ENABLED:
                self.validation_errors["applicant_id"] = _("Citizen ND logic not enabled, not allowed to create"
                                                           "a record card with a citizen with dni ND")
                return

            if validated_data.get("multirecord_from"):
                support = validated_data["multirecord_from"].support
            else:
                support = validated_data.get("support")
            if not support.allow_nd:
                self.validation_errors["applicant_id"] = _("The selected support does not allow the creation of "
                                                           "a record card with a citizen with dni ND")
                return

            group = self.get_group_from_request(self.context["request"])

            if group and not group.citizen_nd:
                self.validation_errors["applicant_id"] = _("The user group does not allow the creation of a "
                                                           "record card with a citizen with dni ND")

    def do_extra_actions_on_create(self, validated_data):
        """
        Perform extra actions on create
        :param validated_data: Dict with validated data from the serializer
        :return:
        """
        self.set_ubication(validated_data)

        applicant = validated_data.pop("applicant_id", None)

        if self.context.get("request") and hasattr(self.context["request"], "application"):
            application = self.context["request"].application
        else:
            application = None

        user_group = self.context["request"].user.usergroup.group
        if validated_data["input_channel"].can_be_mayorship and validated_data.get("mayorship", False):
            # If we can't identify the mayorship group, the RecordCard will be assigned to DAIR
            param = Parameter.get_parameter_by_key("PERFIL_DERIVACIO_ALCALDIA", None)
            try:
                group = Group.objects.get(pk=param)
            except Group.DoesNotExist:
                group = Group.get_dair_group()

            validated_data["responsible_profile"] = group
        else:
            validated_data["responsible_profile"] = Group.get_initial_group_for_record()
        validated_data["request"] = Request.objects.create(
            applicant=applicant, applicant_type=validated_data["applicant_type"],
            input_channel=validated_data["input_channel"],
            communication_media=validated_data.get("communication_media"),
            application=application, normalized_id=set_reference(Request, "normalized_id"))

        validated_data["creation_group"] = user_group

        self.multirecord_actions(validated_data)

    def do_post_create_extra_actions(self, instance, validated_data):
        """
        Perform extra actions on create after the instance creation
        :param instance: Instance of the created object
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        request = self.context.get("request")
        # register the initial state change
        initial_state = RecordState.PENDING_VALIDATE
        wont_tramit = self.wont_tramit or instance.element_detail.requires_citizen
        if wont_tramit and not instance.request.applicant:
            initial_state = RecordState.NO_PROCESSED
            instance.record_state_id = initial_state
            instance.save()
        instance.set_record_state_history(initial_state, request.user if request else None,
                                          previous_state_code=initial_state, automatic=True)

        self.set_record_card_response(instance, validated_data)
        self.set_features(validated_data, related_instance=instance)
        self.set_special_features(validated_data, related_instance=instance)
        self.set_register_code(instance)

        # If the theme of the RecordCard is configurate to autovalidate records on creation
        if instance.record_can_be_autovalidated():
            user = request.user if request else None
            instance.autovalidate_record(request.user.imi_data.get('dptcuser'), user, perform_derivation=False)

        if not validated_data["input_channel"].can_be_mayorship or not validated_data.get("mayorship", False):
            instance.derivate(user_id=get_user_traceability_id(request.user), reason=Reason.INITIAL_ASSIGNATION)

    def set_record_card_response(self, record_card, validated_data):
        """
        Set record card response

        :param record_card: record card created
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        if record_card.request.applicant:
            recordcard_response = self.initial_data["recordcardresponse"]
            applicant = record_card.request.applicant.citizen or record_card.request.applicant.social_entity
            recordcard_response.update({"record_card": record_card.pk})
            if "language" not in recordcard_response:
                recordcard_response["language"] = applicant.language if applicant.language else SPANISH
            serializer_context = self.context
            serializer_context.update({"record_card_check": True})
            multirecord_response_channel = None
            if validated_data.get("multirecord_from"):
                try:
                    resp_channel = validated_data["multirecord_from"].recordcardresponse
                    multirecord_response_channel = resp_channel.response_channel_id
                except AttributeError:
                    multirecord_response_channel = None
            record_card_response_serializer = RecordCardResponseSerializer(
                data=recordcard_response, context=serializer_context,
                multirecord_response_channel=multirecord_response_channel)
            if record_card_response_serializer.is_valid(raise_exception=True):
                record_card_response_serializer.save()
        else:
            RecordCardResponse.objects.create(response_channel_id=ResponseChannel.NONE, record_card=record_card)

    def set_register_code(self, instance):
        # If register code from Ariadna has been validated, the Ariadna Record has to be created
        if "register_code" in self.initial_data:
            AriadnaRecord.objects.create(record_card_id=instance.pk, code=self.initial_data["register_code"])
            self.ariadna.used = True
            self.ariadna.save()

    def multirecord_actions(self, validated_data):
        """
        Perform multirecord actions, if needed
        :param validated_data: Dict with validated data from the serializer
        :return:
        """
        # Set MultiRecord flags
        record_card_from = validated_data.get("multirecord_from")
        if record_card_from:
            validated_data["is_multirecord"] = True
            record_card_from.is_multirecord = True
            record_card_from.save()
            # A multirecord card will have the same input channel, applicant_type and support that its parent record
            validated_data["input_channel"] = record_card_from.input_channel
            validated_data["support"] = record_card_from.support
            validated_data["applicant_type"] = record_card_from.applicant_type
            if validated_data.get("multirecord_copy_responsechannel"):
                response_channel_id = ResponseChannel.NONE
                if hasattr(record_card_from, "recordcardresponse"):
                    response_channel_id = record_card_from.recordcardresponse.response_channel_id
                self.initial_data["recordcardresponse"]["response_channel"] = response_channel_id

        # multirecord_copy_responsechannel is not a RecordCard model field, so it has to be deleted from validated_data
        validated_data.pop("multirecord_copy_responsechannel", None)


class RecordCardFeaturesDetailSerializer(serializers.ModelSerializer):
    feature = FeatureSerializer()
    order = serializers.IntegerField()

    class Meta:
        model = RecordCardFeatures
        fields = ("feature", "value", "is_theme_feature", "order")
        read_only_fields = ("is_theme_feature",)


class RecordCardSpecialFeaturesDetailSerializer(serializers.ModelSerializer):
    feature = FeatureSerializer()
    order = serializers.IntegerField()

    class Meta:
        model = RecordCardSpecialFeatures
        fields = ("feature", "value", "is_theme_feature", "order")
        read_only_fields = ("is_theme_feature",)


class WorkflowCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowComment
        fields = ("task", "comment")


class UnirecordListSerializer(RecordCardSerializer):
    """
    Returns the important information of a Record for writting its answer.
    This serializer is used for returning the set of records unified under a same process.
    """
    response = serializers.SerializerMethodField()

    class Meta:
        model = RecordCard
        fields = ("id", "normalized_record_id", "recordcardresponse", "request", "group_can_answer", "response",
                  "actions", "created_at", "description")

    def get_response(self, obj):
        res = obj.recordcardtextresponse_set.filter(enabled=True).order_by("created_at").first()
        return RecordCardTextResponseSerializer(res).data


class RecordCardWorkflowSerializer(serializers.ModelSerializer):
    """
    Workflow information with the different answers given for the records. In addition to the answer info,
    the record card response configuration will be returned as well. This way, the different clients in charge of
    writing answers can present the interface and group the different answers.
    """
    comments = WorkflowCommentSerializer(source="workflowcomment_set", many=True)
    records = serializers.SerializerMethodField()

    class Meta:
        model = Workflow
        fields = ["id", "comments", "main_record_card_id", "records"]

    def get_records(self, obj):
        qs = obj.recordcard_set.select_related("recordcardresponse", "request", "request__applicant")
        return UnirecordListSerializer(qs, many=True, context=self.context).data


class ExternalIDSerializer(serializers.ModelSerializer):
    service_name = serializers.SerializerMethodField()

    class Meta:
        model = ExternalRecordId
        fields = ["external_code", "service_name"]

    def get_service_name(self, obj):
        return obj.service.name


class RecordCardElementDetailSerializer(ElementDetailDescriptionSerializer):
    class Meta(ElementDetailDescriptionSerializer.Meta):
        fields = ("id", "description", "element", "external_protocol_id",
                  "allow_multiderivation_on_reassignment")


class RecordCardDetailSerializer(RecordCardSerializer):
    extra_actions = False
    post_create_extra_actions = False

    features = serializers.SerializerMethodField()
    special_features = serializers.SerializerMethodField()

    element_detail = RecordCardElementDetailSerializer(read_only=True)
    input_channel = InputChannelShortSerializer(read_only=True)
    support = SupportShortSerializer(read_only=True)
    workflow = RecordCardWorkflowSerializer(read_only=True)
    recordplan = serializers.SerializerMethodField()
    recordcardresolution = serializers.SerializerMethodField()
    responsible_profile = GroupShortSerializer()
    external_ids = ExternalIDSerializer(many=True, read_only=True)
    registers = RegisterSerializer(many=True, read_only=True)
    claims_links = serializers.SerializerMethodField()
    creation_group = GroupShortSerializer()
    record_type = ShortRecordTypeSerializer()

    class Meta:
        model = RecordCard
        fields = ("id", "user_id", "created_at", "updated_at", "description", "responsible_profile", "process",
                  "mayorship", "normalized_record_id", "alarm", "auxiliary", "closing_date",
                  "ans_limit_date", "urgent", "communication_media_detail", "communication_media_date",
                  "record_parent_claimed", "reassignment_not_allowed", "page_origin", "email_external_derivation",
                  "user_displayed", "historicized", "allow_multiderivation", "start_date_process", "appointment_time",
                  "similar_process", "response_state", "notify_quality", "multi_complaint", "lopd", "citizen_alarm",
                  "ci_date", "support_numbers", "element_detail", "element_detail_id", "request_id", "ubication",
                  "record_state", "record_state_id", "record_type", "record_type_id", "applicant_type", "request",
                  "communication_media", "support", "support_id", "input_channel", "input_channel_id", "features",
                  "special_features", "actions", "alarms", "ideal_path", "current_step", "next_step_code", "comments",
                  "recordcardresponse", "recordplan", "recordcardresolution", "workflow", "blocked", "multirecord_from",
                  "is_multirecord", "external_ids", "files", "registers", "full_detail", "claimed_from",
                  "claims_number", "claims_links", "group_can_answer", "organization", "creation_group")
        read_only_fields = fields

    def __init__(self, *args, **kwargs):
        self.detail_features_order = {}
        super().__init__(*args, **kwargs)
        if self.instance:
            el_features = ElementDetailFeature.objects.filter(
                enabled=True, element_detail_id=self.instance.element_detail_id).values("feature_id", "order")
            self.detail_features_order = {el_feature["feature_id"]: el_feature["order"] for el_feature in el_features}

    @swagger_serializer_method(serializer_or_field=serializers.ListField)
    def get_features(self, obj):
        filters_kwargs = {"enabled": True, "feature__deleted__isnull": True}
        record_features = obj.recordcardfeatures_set.filter(**filters_kwargs).select_related("feature")
        for record_feature in record_features:
            record_feature.order = self.detail_features_order.get(record_feature.feature_id, 100)
        return [RecordCardFeaturesDetailSerializer(record_card_feature).data for record_card_feature in record_features]

    @swagger_serializer_method(serializer_or_field=serializers.ListField)
    def get_special_features(self, obj):
        filters_kwargs = {"enabled": True, "feature__deleted__isnull": True}
        record_features = obj.recordcardspecialfeatures_set.filter(**filters_kwargs).select_related("feature")
        for record_feature in record_features:
            record_feature.order = self.detail_features_order.get(record_feature.feature_id, 100)
        return [RecordCardSpecialFeaturesDetailSerializer(record_card_feature).data for record_card_feature in
                record_features]

    def get_recordcardresolution(self, obj):
        try:
            return WorkflowResolutionSerializer(instance=WorkflowResolution.objects.get(workflow=obj.workflow)).data
        except WorkflowResolution.DoesNotExist:
            return

    def get_recordplan(self, obj):
        try:
            return WorkflowPlanReadSerializer(instance=WorkflowPlan.objects.get(workflow=obj.workflow)).data
        except WorkflowPlan.DoesNotExist:
            return

    def get_claims_links(self, obj):
        claims = []
        if not obj.claims_number:
            return claims

        base_normalized_record_id = obj.normalized_record_id.split("-")[0]
        for claim_number in range(obj.claims_number):
            if not claim_number:
                normalized_record_id = base_normalized_record_id
            elif claim_number < 10:
                normalized_record_id = "{}-0{}".format(base_normalized_record_id, claim_number + 1)
            else:
                normalized_record_id = "{}-{}".format(base_normalized_record_id, claim_number + 1)

            claims.append({
                "normalized_record_id": normalized_record_id,
                "url": reverse("private_api:record_cards:recordcard-detail", kwargs={"reference": normalized_record_id})
            })
        return claims


class RecordCardListSerializer(RecordCardSerializer):
    extra_actions = False
    post_create_extra_actions = False
    responsible_profile = GroupShortSerializer()
    element_detail = ElementDetailDescriptionSerializer(read_only=True)
    ubication = UbicationShortSerializer()

    support = SupportShortSerializer(read_only=True)

    class Meta:
        model = RecordCard
        fields = ("id", "user_id", "created_at", "updated_at", "description", "responsible_profile", "process",
                  "mayorship", "normalized_record_id", "alarm", "ans_limit_date", "urgent",
                  "element_detail", "record_state", "actions", "alarms", "full_detail", "ubication", "user_displayed",
                  "record_type")
        read_only_fields = fields

    @swagger_serializer_method(serializer_or_field=serializers.DictField)
    def get_actions(self, obj):
        request = self.context.get("request")
        if request:
            return RecordActions(obj, request.user, detail_mode=False).actions()
        return {}


class UbicationRegularSerializer(serializers.Serializer):
    street = serializers.CharField()
    street2 = serializers.CharField()
    district = serializers.IntegerField(source="district_id")


class RecordCardBaseListRegularSerializer(GetGroupFromRequestMixin, serializers.Serializer):
    id = serializers.IntegerField()
    user_id = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    responsible_profile = ResponsibleProfileRegularSerializer()
    process = serializers.CharField(source="process_id")
    mayorship = serializers.BooleanField()
    normalized_record_id = serializers.CharField()
    alarm = serializers.BooleanField()
    ans_limit_date = serializers.DateTimeField()
    urgent = serializers.BooleanField()
    element_detail = ElementDetailRegularSerializer()
    record_state = RecordStateRegularSerializer()
    actions = serializers.SerializerMethodField()
    alarms = serializers.SerializerMethodField()
    full_detail = serializers.SerializerMethodField()
    ubication = UbicationRegularSerializer()
    user_displayed = serializers.CharField()
    record_type = RecordTypeRegularSerializer()

    @swagger_serializer_method(serializer_or_field=serializers.BooleanField)
    def get_full_detail(self, obj):
        return False

    @swagger_serializer_method(serializer_or_field=serializers.DictField)
    def get_actions(self, obj):
        request = self.context.get("request")
        if request:
            return RecordActions(obj, request.user, detail_mode=False).actions()
        return {}

    @swagger_serializer_method(serializer_or_field=serializers.DictField)
    def get_alarms(self, obj):
        request = self.context.get("request")
        group = self.get_group_from_request(request)
        return RecordCardAlarms(obj, group).alarms


class RecordCardListRegularSerializer(RecordCardBaseListRegularSerializer):
    description = serializers.CharField()


class RecordCardUpdateSerializer(RecordCardBaseSerializer, SerializerUpdateExtraMixin, GetGroupFromRequestMixin,
                                 serializers.ModelSerializer):
    post_update_extra_actions = True

    admin_close_update_fields = ["recordcardresponse"]

    class Meta:
        model = RecordCard
        fields = ("description", "mayorship", "features", "special_features", "ubication", "recordcardresponse")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.old_ubication = None
        self.fields["description"].required = False
        self.fields["recordcardresponse"].required = False
        if isinstance(self.instance, RecordCard):
            self.initial_values = RecordDictUpdateFields(self.instance).record_update_fields()

    def run_validation(self, data=empty):
        self.check_fields_changed()
        validated_data = super().run_validation(data)
        self.check_recordcardresponse(validated_data)

        if self.validation_errors:
            raise ValidationError(self.validation_errors, code="invalid")

        self.old_ubication = getattr(self.instance, 'ubication')

        return validated_data

    def check_fields_changed(self):
        """
        Check if fields can be updated depending on record state and user permissions.
        If record state is cancelled or closed, only an admin can change the recordcardresponse,

        :return:
        """
        if self.instance.record_state_id in RecordState.CLOSED_STATES:
            permission_errors = {}
            has_admin_permission = self.permission_checker.has_permission(ADMIN)
            for field_key in self.fields:
                if field_key in self.initial_data:
                    if field_key not in self.admin_close_update_fields:
                        permission_errors[field_key] = _("{} can not be changed because record card is closed or "
                                                         "cancelled".format(field_key))
                    elif not has_admin_permission:
                        permission_errors[field_key] = _(
                            "{} can not be changed because user has not admin permission".format(field_key))
            if permission_errors:
                raise ValidationError(permission_errors)

    def check_recordcardresponse(self, validated_data):
        """
        Check that the user has permissions to change recordcard response channel

        :param validated_data: Dict with validated data from the serializer
        :return:
        """
        has_permission = self.permission_checker.has_permission(RESP_CHANNEL_UPDATE)
        update_recordcardresponse = validated_data.get("recordcardresponse")
        if not has_permission and update_recordcardresponse:
            current_response_channel = self.instance.recordcardresponse.response_channel
            update_response_channel = update_recordcardresponse["response_channel"]
            if "recordcardresponse" in validated_data and current_response_channel != update_response_channel:
                self.validation_errors["recordcardresponse"] = _("User's group is not allowed to change recordcard "
                                                                 "response channel")

    def do_extra_actions_on_update(self, validated_data):
        """
        Perform extra actions on update

        :param validated_data: Dict with validated data of the serializer
        :return:
        """

        self.set_ubication(validated_data)
        self.set_features(validated_data)
        self.set_special_features(validated_data)
        self.set_recordcard_response(validated_data)

    def set_ubication(self, validated_data):
        self.old_ubication = getattr(self.instance, 'ubication')
        return super().set_ubication(validated_data)

    def set_recordcard_response(self, validated_data):
        """
        Update record card response
        :param validated_data: Dict with validated data of the serializer
        :return:
        """

        recordcard_response = self.initial_data.get("recordcardresponse")
        if recordcard_response:
            recordcard_response.update({"record_card": self.instance.pk})

            if hasattr(self.instance, "recordcardresponse"):
                record_card_response_serializer = RecordCardResponseSerializer(
                    instance=self.instance.recordcardresponse, data=recordcard_response,
                    context={"record_card_check": True})
            else:
                record_card_response_serializer = RecordCardResponseSerializer(data=recordcard_response,
                                                                               context={"record_card_check": True})
            if record_card_response_serializer.is_valid(raise_exception=True):
                validated_data["recordcardresponse"] = record_card_response_serializer.save()

    def do_post_update_extra_actions(self, previous_instance, validated_data):
        """
        Perform extra actions on create after the instance creation
        :param previous_instance: Copy of the instance before the update operation
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        response_channel_id = self.instance.recordcardresponse.get_response_channel()
        if self.instance.pending_answer_has_toclose_automatically(response_channel_id):
            self.instance.pending_answer_change_state(self.instance.record_state_id,
                                                      self.context["request"].user,
                                                      self.context["request"].user.imi_data.get('dptcuser'),
                                                      automatic=True)

        if self.ubication_has_change():
            self.instance.derivate(user_id=get_user_traceability_id(self.context["request"].user))
        updated_fields = RecordDictUpdateFields(self.instance).record_update_fields()
        update_comment = UpdateComment(self.initial_values, updated_fields).get_update_comment()
        if update_comment:
            group = self.get_group_from_request(self.context["request"])
            Comment.objects.create(record_card=self.instance, comment=update_comment, group=group,
                                   reason_id=Reason.RECORDCARD_UPDATED,
                                   user_id=get_user_traceability_id(self.context["request"].user))

    def ubication_has_change(self):
        if 'ubication' not in self.data or not self.old_ubication:
            return False
        new = self.validated_data.get('ubication')
        if new != self.old_ubication and (not self.old_ubication or not new):
            return True
        elif not self.old_ubication:
            return False
        new_ubication = Ubication(**new)
        new_ubication.adjust_coordinates()
        return self.old_ubication.is_different_location(new_ubication)

    @staticmethod
    def get_features_serializer_class():
        return ManyToManyFeaturesSerializerMany


class RecordCardExportSerializer(UbicationAttributeMixin, serializers.Serializer):
    identificador = serializers.CharField(source="normalized_record_id", label=_('Record'))
    tipusfitxa = serializers.CharField(source="record_type.description", label=_('Record type'))
    data_alta = serializers.SerializerMethodField(label=_('Creation date'))
    data_tancament = serializers.SerializerMethodField(label=_('Closing date'))
    dies_oberta = serializers.SerializerMethodField(label=_('Days opened'))
    antiguitat = serializers.SerializerMethodField(label=_('Days from creation'))
    tipus_solicitant = serializers.SerializerMethodField(label='Tipus_Sol·licitant')
    solicitant = serializers.SerializerMethodField(label='Sol·licitant')
    districte = serializers.SerializerMethodField(label=_('District'))
    barri = serializers.SerializerMethodField(label=_('Neighborhood'))
    tipus_via = serializers.SerializerMethodField(label=_('Street type'))
    carrer = serializers.SerializerMethodField(label=_('Street'))
    numero = serializers.SerializerMethodField(label=_('Number'))
    area = serializers.CharField(source="element_detail.element.area.description", label=_('Area'))
    element = serializers.CharField(source="element_detail.element.description", label=_('Element'))
    detall = serializers.CharField(source="element_detail.description", label=_('Element Detail'))
    carac_especial_desc = serializers.SerializerMethodField(label=_('Special attributes (desc)'))
    carac_especial = serializers.SerializerMethodField(label=_('Special attibuttes'))
    descripcio = serializers.CharField(source="description", label=_("Description"))
    estat = serializers.CharField(source="record_state.description", label=_('State'))
    perfil_responsable = serializers.CharField(source="responsible_profile.description", label=_('Responsible profile'))
    tipus_resposta = serializers.SerializerMethodField(label=_('Answer type'))
    resposta_feta = serializers.SerializerMethodField(label=_('Answer'))
    comentari_qualitat = serializers.SerializerMethodField(label=_('Quality comment'))

    def get_data_alta(self, record):
        return record.created_at.strftime("%d/%m/%Y %H:%M:%S")

    def get_data_tancament(self, record):
        return record.closing_date.strftime("%d/%m/%Y %H:%M:%S") if record.closing_date else ""

    def get_districte(self, record):
        return record.ubication.district.name if record.ubication and record.ubication.district else ""

    def get_barri(self, record):
        return self.get_ubication_attribute(record, "neighborhood")

    def get_tipus_via(self, record):
        return self.get_ubication_attribute(record, "via_type")

    def get_carrer(self, record):
        return self.get_ubication_attribute(record, "street")

    def get_numero(self, record):
        return self.get_ubication_attribute(record, "street2")

    def get_solicitant(self, record):
        if record.request.applicant:
            if record.request.applicant.citizen:
                return ' '.join([
                    record.request.applicant.citizen.name,
                    record.request.applicant.citizen.first_surname,
                    record.request.applicant.citizen.second_surname,
                ])
            else:
                return record.request.applicant.social_entity.social_reason
        return ""

    def get_tipus_solicitant(self, record):
        return record.applicant_type.description

    def get_dies_oberta(self, record):
        if record.closing_date:
            return max((record.closing_date - record.created_at).days, 1)
        return ''

    def get_antiguitat(self, record):
        return max((timezone.now() - record.created_at).days, 1)

    def get_resposta_feta(self, record):
        text_responses = record.recordcardtextresponse_set.all()
        if text_responses:
            return BeautifulSoup(text_responses[0].response, "html.parser").get_text()
        return ""

    def get_special_feature(self, record):
        specials_features = record.recordcardspecialfeatures_set.filter(is_theme_feature=True)
        return specials_features[0] if specials_features else ""

    def get_carac_especial_desc(self, record):
        special_feature = self.get_special_feature(record)
        return special_feature.feature.description if special_feature else ""

    def get_carac_especial(self, record):
        special_feature = self.get_special_feature(record)
        return special_feature.label_value if special_feature else ""

    def get_tipus_resposta(self, record):
        if hasattr(record, "recordcardresponse"):
            return record.recordcardresponse.response_channel.get_id_display()
        return ""

    def get_comentari_qualitat(self, record):
        return ""


class RecordCardThemeChangeSerializer(SerializerUpdateExtraMixin, GetGroupFromRequestMixin, RecordCardBaseSerializer,
                                      RecordFeaturesBaseSerializer, serializers.ModelSerializer):
    post_update_extra_actions = True

    element_detail_id = serializers.PrimaryKeyRelatedField(
        source="element_detail",
        queryset=ElementDetail.objects.filter(**ElementDetail.ENABLED_ELEMENTDETAIL_FILTERS),
        error_messages={"does_not_exist": _("The selected element_detail does not exist")})
    perform_derivation = serializers.BooleanField(required=False, default=True)

    class Meta:
        model = RecordCard
        fields = ("element_detail_id", "features", "special_features", "perform_derivation", "ubication")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def run_validation(self, data=empty):
        try:
            self.fields['ubication'].context.update({
                'element_detail': ElementDetail.objects.get(pk=data.get('element_detail_id')),
            })
        except ElementDetail.DoesNotExist:
            pass
        validated_data = super().run_validation(data)
        self.check_validated_record()
        self.check_element_detail(validated_data)

        if self.validation_errors:
            raise ValidationError(self.validation_errors, code="invalid")
        return validated_data

    def check_validated_record(self):
        """
        Only the element detail of record card on THEME_CHANGE_STATES can be changed

        :return:
        """
        THEME_CHANGE_STATES = [RecordState.CLOSED, RecordState.PENDING_VALIDATE, RecordState.EXTERNAL_RETURNED,
                               RecordState.IN_RESOLUTION]
        if self.instance.record_state_id not in THEME_CHANGE_STATES:
            self.validation_errors["element_detail_id"] = _("Element Detail can not be changed because RecordCard "
                                                            "has been validated")

    def check_element_detail(self, validated_data):
        """
        Check that:
         - element detail has been changed
         - the selected element detail is one of the change possibilites
         - if a derivation will cause a derivation outside group"s ambit
         - if user has not RECARD_THEME_CHANGE_AREA permission, element detail change does not go outside area
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        new_element_detail = validated_data.get("element_detail")
        request = self.context["request"]
        group = self.get_group_from_request(request)

        if not self.instance.element_detail != new_element_detail:
            self.validation_errors["element_detail_id"] = _("Element Detail has not been changed")

        possible_themes_change = PossibleThemeChange(self.instance, group).themes_to_change()
        if new_element_detail not in possible_themes_change:
            self.validation_errors["element_detail_id"] = _("Element Detail is not one of the change possibilities")

        if not IrisPermissionChecker.get_for_user(request.user).has_permission(RECARD_THEME_CHANGE_AREA):
            if self.instance.element_detail.element.area_id != new_element_detail.element.area_id:
                self.validation_errors["element_detail_id"] = _(
                    "Element Detail can not been changed because user has not permission to change elementdetail to "
                    "a different area")

    def do_extra_actions_on_update(self, validated_data):
        """
        Perform extra actions on update

        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        self.set_ubication(validated_data)
        self.set_features(validated_data, self.instance)
        self.set_special_features(validated_data, self.instance)
        self.set_process_autovalidated_themes(validated_data)

    def set_process_autovalidated_themes(self, validated_data):
        """
        Perform extra actions on update

        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        new_element_detail = validated_data["element_detail"]
        if self.instance.record_can_be_autovalidated(new_element_detail=new_element_detail):
            validated_data["process_id"] = new_element_detail.process_id
            if self.instance.record_state_id == RecordState.EXTERNAL_RETURNED:
                validated_data["workflow"] = None
                validated_data["record_state_id"] = RecordState.PENDING_VALIDATE

    def do_post_update_extra_actions(self, previous_instance, validated_data):
        theme_changed = self.instance.element_detail != previous_instance.element_detail
        if theme_changed:
            self.instance.update_ans_limits()
            self.instance.update_detail_info()
            request = self.context["request"]

            if self.instance.workflow:
                self.instance.workflow.element_detail_modified = True
                self.instance.workflow.save()
            group = self.get_group_from_request(request)
            message = _("Theme changed from '{}' to '{}'.").format(
                previous_instance.element_detail.description, validated_data.get("element_detail").description)
            reason_theme_change_id = int(Parameter.get_parameter_by_key("CANVI_DETALL_MOTIU", 19))
            Comment.objects.create(record_card=self.instance, comment=message, group=group,
                                   reason_id=reason_theme_change_id,
                                   user_id=get_user_traceability_id(self.context["request"].user))

            if self.instance.record_can_be_autovalidated():
                user = request.user if request else None
                self.instance.autovalidate_record(request.user.imi_data.get('dptcuser', ''), user,
                                                  perform_derivation=validated_data.get("perform_derivation"))
            else:
                if validated_data.get("perform_derivation"):
                    self.instance.derivate(get_user_traceability_id(self.context["request"].user))

    @staticmethod
    def get_features_serializer_class():
        """
        :return: Features serializer class
        """
        return ManyToManyFeaturesSerializerMany


class MinimalRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Request
        fields = ("applicant_type",)
        read_only_fields = fields


class RecordCardRestrictedSerializer(RecordCardDetailSerializer):
    registers = RegisterSerializer(many=True, read_only=True)
    responsible_profile = GroupShortSerializer()

    full_detail = serializers.SerializerMethodField(default=False)

    @swagger_serializer_method(serializer_or_field=serializers.BooleanField)
    def get_full_detail(self, obj):
        return False

    class Meta:
        model = RecordCard
        fields = ("id", "user_id", "created_at", "updated_at", "normalized_record_id", "record_type", "input_channel",
                  "element_detail", "record_state", "responsible_profile", "support", "registers", "full_detail")
        read_only_fields = fields


class RecordCardRestrictedListSerializer(RecordCardRestrictedSerializer):
    class Meta:
        model = RecordCard
        fields = ("id", "user_id", "created_at", "updated_at", "normalized_record_id", "record_type", "input_channel",
                  "element_detail", "record_state", "responsible_profile", "support", "description",
                  "full_detail")
        read_only_fields = fields


class ClaimShortSerializer(RecordCardSerializer):
    class Meta:
        model = RecordCard
        fields = ("id", "user_id", "created_at", "updated_at", "normalized_record_id")
        read_only_fields = fields


class ClaimDescriptionSerializer(serializers.Serializer):
    description = serializers.CharField()
    email = serializers.CharField(default=None)


class RecordCardApplicantListSerializer(serializers.ModelSerializer):
    element_detail = serializers.SerializerMethodField()

    class Meta:
        model = RecordCard
        fields = ("id", "created_at", "normalized_record_id", "element_detail", "description")
        read_only_fields = fields

    def get_element_detail(self, obj):
        return obj.element_detail.description


class ManyToManyFeaturesSerializerMany(GetGroupFromRequestMixin, ManyToManyExtendedSerializer):

    def disable_registers(self, active_registers, validated_data):
        """
        Disable features that are not send to the api, taking in account that if the theme has changed
        the previos features must not be disabled--
        :param active_registers: Current active to_registers
        :param validated_data: Validated data send to the api
        :return:
        """
        theme_changed = self.parent.instance.element_detail != self.parent.validated_data.get("element_detail")
        element_detail = self.parent.validated_data.get("element_detail")
        if element_detail:
            detail_features = element_detail.feature_configs.filter(
                enabled=True, feature__deleted__isnull=True).values_list("feature_id", flat=True)
        else:
            detail_features = []

        validated_features = {item[self.to].pk: item for item in validated_data}
        if theme_changed and self.parent.validated_data.get("element_detail"):
            self._check_theme_features_after_change(detail_features, active_registers, validated_features)
        else:
            self._check_theme_features(active_registers, validated_features)

    def _check_theme_features(self, active_registers, validated_features):
        disable_ids = []
        for active_register in active_registers:
            if active_register["is_theme_feature"]:
                if active_register[self.to] not in validated_features or self.change_extra_values(
                        active_register, validated_features[active_register[self.to]]
                ):
                    disable_ids.append(active_register["id"])
        self._do_updates(disable_ids, themes_features=None, no_themes_features=None, unvisible_features=None)

    def _check_theme_features_after_change(self, detail_features, active_registers, validated_features):
        no_themes_features = []
        themes_features = []
        unvisible_features = []
        disable_ids = []
        for active_register in active_registers:
            if active_register[self.to] not in detail_features:
                # If theme has changed and the feature is not from this theme,
                # we have to register is_theme_feature as False
                no_themes_features.append(active_register["id"])
                unvisible_features.append({"description": active_register["feature__description"],
                                           "value_type": active_register["feature__values_type"],
                                           "value": active_register["value"]})
            else:
                themes_features.append(active_register["id"])
                if active_register[self.to] not in validated_features or \
                        self.change_extra_values(active_register, validated_features[active_register[self.to]]):
                    disable_ids.append(active_register["id"])
        self._do_updates(disable_ids, themes_features, no_themes_features, unvisible_features)

    def _do_updates(self, disable_ids, themes_features, no_themes_features, unvisible_features):
        if disable_ids:
            self.model.objects.filter(id__in=disable_ids).update(enabled=False)
        if themes_features:
            self.model.objects.filter(id__in=themes_features).update(is_theme_feature=True)
        if no_themes_features:
            self.model.objects.filter(id__in=no_themes_features).update(is_theme_feature=False)
            self.set_features_novisible_comment(unvisible_features)

    def set_features_novisible_comment(self, unvisible_features):
        """
        Create the traceability comment for unvisible features
        :param unvisible_features: List of features that are set to invisible for the new theme
        :return:
        """
        features_changed = ""
        for feature in unvisible_features:
            features_changed += "{} = {}, ".format(feature["description"], self.get_feature_value(feature))
        group = self.get_group_from_request(self.context["request"])
        if unvisible_features:
            message = _("Features {} will not be taken into account").format(features_changed)
            Comment.objects.create(record_card=self.parent.instance, comment=message, group=group,
                                   reason_id=Reason.FEATURES_THEME_NO_VISIBLES,
                                   user_id=get_user_traceability_id(self.context["request"].user))

    @staticmethod
    def get_feature_value(feature_dict):
        if feature_dict.get("value_type"):
            value_pk = feature_dict.get("value")
            try:
                return Values.objects.get(pk=int(value_pk)).description if value_pk else ""
            except Values.DoesNotExist:
                return ""
        else:
            return feature_dict.get("value")


class LocationSerializer(UbicationSerializer):
    class Meta(UbicationSerializer.Meta):
        fields = ("xetrs89a", "yetrs89a")


class RecordUbicationListSerializer(RecordCardListSerializer):
    ubication = LocationSerializer()

    class Meta(RecordCardListSerializer.Meta):
        fields = ('id', 'normalized_record_id', 'ubication', 'record_type_id', 'record_state')


class RecordCardShortListSerializer(RecordCardListSerializer):
    applicant_document = serializers.SerializerMethodField()
    short_address = serializers.SerializerMethodField()

    class Meta:
        model = RecordCard
        fields = ("id", "description", "normalized_record_id", "applicant_document", "short_address")
        read_only_fields = fields

    def get_applicant_document(self, obj):
        if obj.request and not obj.request.applicant:
            return
        if obj.request and obj.request.applicant.citizen:
            return obj.request.applicant.citizen.dni
        elif obj.request and obj.request.applicant.social_entity:
            return obj.request.applicant.social_entity.cif
        return

    def get_short_address(self, obj):
        if obj.ubication:
            return obj.ubication.short_address
        return


class RecordCardCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecordCard
        fields = ("id", "description", "normalized_record_id")
        read_only_fields = fields


class RecordCardShortNotificationsSerializer(RecordCardSerializer):
    class Meta:
        model = RecordCard
        fields = ("id", "description", "normalized_record_id")
        read_only_fields = fields


class RecordCardMultiRecordstListSerializer(serializers.ModelSerializer):
    element_detail = ElementDetailShortSerializer(read_only=True)
    record_state = RecordStateSerializer(read_only=True)

    class Meta:
        model = RecordCard
        fields = ("id", "normalized_record_id", "multirecord_from", "created_at", "element_detail", "record_state",
                  "description")
        read_only_fields = fields


class RecordCardUrgencySerializer(GetGroupFromRequestMixin, serializers.ModelSerializer):
    class Meta:
        model = RecordCard
        fields = ("id", "urgent")

    def save(self, **kwargs):
        with transaction.atomic():
            self.instance = super().save(**kwargs)
            group = self.get_group_from_request(self.context["request"])
            if self.instance.urgent:
                message = _("RecordCard set to urgent")
                self.instance.alarm = True
                self.instance.save()
            else:
                message = _("RecordCard set to NO urgent")
                if not RecordCardAlarms(self.instance, group).check_alarms(["urgent"]):
                    self.instance.alarm = False
                    self.instance.save()
            Comment.objects.create(record_card=self.instance, comment=message, group=group,
                                   reason_id=Reason.RECORDCARD_URGENCY_CHANGE,
                                   user_id=get_user_traceability_id(self.context["request"].user))
            return self.instance


class RecordCardReasignableSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecordCard
        fields = ("id", "reassignment_not_allowed")


class RecordManagementIndicatorsBaseSerializer(serializers.Serializer):
    pending_validation = serializers.IntegerField()
    processing = serializers.IntegerField()
    expired = serializers.IntegerField()
    near_expire = serializers.IntegerField()


class RecordManagementChildrenIndicatorsSerializer(RecordManagementIndicatorsBaseSerializer):
    group_id = serializers.IntegerField()
    group_name = serializers.CharField()


class RecordCardManagementAmbitIndicatorsSerializer(RecordManagementIndicatorsBaseSerializer):
    childrens = RecordManagementChildrenIndicatorsSerializer(many=True)


class RecordCardManagementIndicatorsSerializer(RecordManagementIndicatorsBaseSerializer):
    urgent = serializers.IntegerField()


class RecordCardMonthIndicatorsSerializer(serializers.Serializer):
    pending_validation = serializers.IntegerField()
    processing = serializers.IntegerField()
    closed = serializers.IntegerField()
    cancelled = serializers.IntegerField()
    external_processing = serializers.IntegerField()
    pending_records = serializers.IntegerField()
    average_close_days = serializers.IntegerField()
    average_age_days = serializers.IntegerField()
    entries = serializers.IntegerField()


class RecordCardTraceabilitySerializer(serializers.Serializer):
    TYPE_STATE = "state_history"
    TYPE_REC_COMMENT = "record_comment"
    TYPE_WKF_COMMENT = "worflow_comment"
    TYPE_REASIGN = "reasignation"

    type = serializers.ChoiceField(choices=[TYPE_STATE, TYPE_REC_COMMENT, TYPE_WKF_COMMENT])
    created_at = serializers.DateTimeField()
    user_id = serializers.CharField()
    group_name = serializers.CharField(allow_null=True)

    previous_state = serializers.IntegerField(required=False)
    next_state = serializers.IntegerField(required=False)
    automatic = serializers.BooleanField(required=False)
    reason = serializers.IntegerField(required=False, allow_null=True)
    comment = serializers.CharField(required=False)
    task = serializers.CharField(required=False)
    previous_responsible = serializers.CharField(required=False)
    next_responsible = serializers.CharField(required=False)


class RecordCardCheckSerializer(serializers.Serializer):
    can_confirm = serializers.BooleanField()
    reason = serializers.CharField(allow_null=True, allow_blank=True)
    next_state = serializers.PrimaryKeyRelatedField(
        queryset=RecordState.objects.filter(enabled=True),
        error_messages={
            "does_not_exist": _("The selected RecordState does not exist or is not enabled"),
        })
    next_group = GroupShortSerializer()
    different_ambit = serializers.BooleanField()


class RecordCardValidateCheckSerializer(RecordCardCheckSerializer):
    possible_similar = RecordCardCodeSerializer(many=True)
    send_external = serializers.BooleanField(default=False, required=False)


class RecordCardClaimCheckSerializer(RecordCardCheckSerializer):
    claim_type = serializers.CharField(allow_null=True)
    reason_comment_id = serializers.IntegerField(required=False)


class RecordCardCancelSerializer(serializers.Serializer):
    reason = serializers.PrimaryKeyRelatedField(
        queryset=Reason.objects.filter(reason_type=Reason.TYPE_1),
        error_messages={
            "does_not_exist": _("The selected Reason does not exist or is not enabled"),
        })
    comment = serializers.CharField(validators=[WordsLengthValidator(words=2, words_length=4)])
    duplicated_record_card = serializers.CharField(required=False, allow_blank=True)

    def run_validation(self, data=empty):
        """
        We override the default `run_validation`, because the validation
        performed by validators and the `.validate()` method should
        be coerced into an error dictionary with a "non_fields_error" key.
        """
        validated_data = super().run_validation(data)
        reason_id = validated_data["reason"].pk

        if "group" not in self.context:
            raise ValidationError({"reason": _("Group is needed for data validation")})

        duplicity_repetition_reason_id = int(Parameter.get_parameter_by_key("DEMANAR_FITXA", 1))
        expiration_reason_id = int(Parameter.get_parameter_by_key("REABRIR_CADUCIDAD", 17))

        if reason_id == Reason.VALIDATION_BY_ERROR:
            self.check_validation_error_reason()
        elif reason_id == expiration_reason_id:
            self.check_expiration_reason()
        elif reason_id == duplicity_repetition_reason_id:
            self.check_duplicity_cancel_reason(validated_data)

        return validated_data

    def check_validation_error_reason(self):
        """
        Method to check validation by error reason on RecordCard Cancel
        """
        record_card = self.context["record_card"]
        if not record_card.is_validated:
            raise ValidationError({"reason": _("A RecordCard pending to validate can not be cancelled with "
                                               "Reason 'Validation By Error ({})'").format(Reason.VALIDATION_BY_ERROR)})
        elif record_card.has_expired(self.context["group"]):
            expiration_reason_id = Parameter.get_parameter_by_key("REABRIR_CADUCIDAD", 17)
            raise ValidationError({"reason": _("A RecordCard that has expired can not be cancelled with "
                                               "Reason 'Validation By Error ({})'. RecordCard must be cancelled by "
                                               "Reason 'Expiration ({})'").format(
                Reason.VALIDATION_BY_ERROR, expiration_reason_id)})
        elif self.context["group"] not in record_card.responsible_profile.get_ancestors(include_self=True):
            raise ValidationError({"reason": _("The group {} is not allowed to cancel the RecordCard by "
                                               "'Validation by Error' because it's not its responsible profile "
                                               "or a superior of it")})
        elif self.exceed_max_days_in_ambit(record_card):
            raise ValidationError({"reason": _("RecordCard can not be cancelled by 'Validation by Error' because it"
                                               " has exceeded the maximum number of days on it's ambit")})

    def check_expiration_reason(self):
        """
        Method to check expiration reason on RecordCard Cancel
        """
        record_card = self.context["record_card"]
        if not record_card.has_expired(self.context["group"]):
            expiration_reason_id = Parameter.get_parameter_by_key("REABRIR_CADUCIDAD", 17)
            raise ValidationError({"reason": _("A RecordCard that has not expired can not be cancelled with "
                                               "Reason 'Cancelled because expiration ({})'").format(
                expiration_reason_id)})

    def check_duplicity_cancel_reason(self, validated_data):
        """
        Method to check duplicity reason on RecordCard Cancel
        """
        if not validated_data.get("duplicated_record_card"):
            raise ValidationError({
                "duplicated_record_card": _("Duplicated record card is mandatory for cancel by duplicity.")
            })
        try:
            duplicated_record_card = RecordCard.objects.get(
                normalized_record_id=validated_data.get("duplicated_record_card"))
        except RecordCard.DoesNotExist:
            raise ValidationError({"duplicated_record_card": _("RecordCard with code {} does not exist").format(
                validated_data.get("duplicated_record_card"))})

        if self.different_applicant(duplicated_record_card):
            raise ValidationError(
                {"duplicated_record_card": _("RecordCard can not be cancelled because of duplicity reason"
                                             " due to different applicants")})
        if duplicated_record_card.record_state_id == RecordState.CANCELLED:
            raise ValidationError(
                {"duplicated_record_card": _("RecordCard can not be cancelled because of duplicity due to "
                                             "duplicated record card has been cancelled previously")})
        if duplicated_record_card.pk == self.context["record_card"].pk:
            raise ValidationError(
                {"duplicated_record_card": _("RecordCard can not be cancelled because of duplicity due to "
                                             "duplicated record card code is its own one")})

    def different_applicant(self, duplicated_record_card):
        """

        :param duplicated_record_card:
        :return: True if applicants are different, False if applicant are the same
        """
        record_applicant = self.context["record_card"].request.applicant
        duplicated_record_applicant = duplicated_record_card.request.applicant
        if record_applicant.citizen and duplicated_record_applicant.citizen:
            return record_applicant.citizen.legal_id != duplicated_record_applicant.citizen.legal_id
        elif record_applicant.social_entity and duplicated_record_applicant.social_entity:
            return record_applicant.social_entity.legal_id != duplicated_record_applicant.social_entity.legal_id
        else:
            return True

    @staticmethod
    def exceed_max_days_in_ambit(record_card):
        """
        Check if a record card has exceeded the max days in ambit to be cancelled

        :param record_card: record being cancelled
        :return: True if record has exceeded the max days in ambit to be cancelled. Else False
        """
        cancel_ambit_value = int(Parameter.get_parameter_by_key("ANULACION_AMBIT_VALUE", 10))
        if cancel_ambit_value == -1:
            return False
        return record_card.days_in_ambit > cancel_ambit_value

    @staticmethod
    def lower_than_min_days_in_ambit(record_card):
        """

        :param record_card: record being cancelled
        :return: True if record has been less than the limit in ambit to be cancelled. Else False
        """
        min_days_in_ambit = int(Parameter.get_parameter_by_key("DIES_PER_VALIDACIO", 1))
        if min_days_in_ambit == -1:
            return False
        return record_card.days_in_ambit > min_days_in_ambit


class RecordCardReasignationSerializer(SerializerCreateExtraMixin, serializers.ModelSerializer):
    extra_actions = True
    post_create_extra_actions = True
    post_data_keys = ["allow_multiderivation"]

    allow_multiderivation = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = RecordCardReasignation
        fields = ("id", "user_id", "created_at", "updated_at", "record_card", "group", "previous_responsible_profile",
                  "next_responsible_profile", "reason", "comment", "allow_multiderivation")
        read_only_fields = ("id", "user_id", "created_at", "updated_at", "group", "previous_responsible_profile")

    def validate(self, attrs):
        request = self.context.get("request")
        record_card = attrs.get("record_card")
        RecordCardReasignation.check_different_responsible_profiles(record_card.responsible_profile_id,
                                                                    attrs.get("next_responsible_profile").pk)
        RecordCardReasignation.check_recordcard_reasignment_not_allowed(record_card)
        if request:
            if not hasattr(request.user, "usergroup"):
                raise ValidationError({"group": _("User has to be asigned to a group to be able to do a reasignation")})

            outside_ambit_perm = IrisPermissionChecker.get_for_user(request.user).has_permission(
                RECARD_REASSIGN_OUTSIDE
            )
            RecordCardReasignation.check_reasignation_in_allowed_reasignations(
                record_card, attrs.get("next_responsible_profile"), self.context["request"].user.usergroup.group,
                outside_perm=outside_ambit_perm
            )

        return attrs

    def run_validation(self, data=empty):
        validated_data = super().run_validation(data)
        element_detail = validated_data["record_card"].element_detail
        if validated_data.get("allow_multiderivation") and not element_detail.allow_multiderivation_on_reassignment:
            raise ValidationError({"allow_multiderivation": _(
                "Allow multiderivation can not be set because record's theme does not allow it")})
        return validated_data

    def do_extra_actions_on_create(self, validated_data):
        """
        Perform extra actions on create
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        # request check at validate method
        validated_data["group"] = self.context["request"].user.usergroup.group
        validated_data["previous_responsible_profile"] = validated_data["record_card"].responsible_profile

    def do_post_create_extra_actions(self, instance, validated_data):
        """
        After register the reasignation, we reasign the record_card amd mark it as reasgined
        :param instance: Instance of the created object
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        record_card = instance.record_card
        instance.record_card.responsible_profile = instance.next_responsible_profile
        filter_kwargs = {'id': instance.record_card_id}
        # If record belongs to a workflow, we have to reassign all the record from the workflow
        if record_card.workflow:
            filter_kwargs = {'workflow_id': record_card.workflow_id}
        with transaction.atomic():
            records = RecordCard.objects.filter(**filter_kwargs)
            # Create a reassignation entry for every extra record in the workflow
            extra_reassignations = [RecordCardReasignation(**{
                **validated_data,
                'record_card_id': rc.pk,
            }) for rc in records if rc.pk != record_card.pk]
            RecordCardReasignation.objects.bulk_create(extra_reassignations)
            # When the responsible profile change, all RecordCardConversations have to be closed
            records.update(
                responsible_profile_id=instance.next_responsible_profile_id,
                user_displayed="",
                allow_multiderivation=self.initial_data.get("allow_multiderivation", False),
                reasigned=True,
                alarm=True,
            )
            for record in records:
                record.close_record_conversations()
        # Allocate notifications outside the transaction since they are not critical
        for record in records:
           send_allocated_notification.delay(instance.next_responsible_profile_id, record.pk)


class CheckFileExtensionsMixin:

    @staticmethod
    def allowed_files_extensions():
        return Parameter.get_parameter_by_key("EXTENSIONS_PERMESES_FITXERS",
                                              "jpg,jpeg,png,pdf,docx,xls,odt,xlsx,ods").split(",")

    def run_validation(self, data=empty):
        validated_data = super().run_validation(data)
        file_extension = validated_data.get("filename", "").split(".")[-1]
        if file_extension.lower() not in self.allowed_files_extensions():
            raise ValidationError({"filename": _("File extension is not allowed")}, code="invalid")

        return validated_data


class RecordChunkedFileSerializer(SerializerCreateExtraMixin, GetGroupFromRequestMixin, CheckFileExtensionsMixin,
                                  ChunkedUploadSerializer):
    record_card_id = serializers.PrimaryKeyRelatedField(
        source="record_card", queryset=RecordCard.objects.filter(enabled=True),
        error_messages={"does_not_exist": _("The selected record card does not exist or is not enabled")})
    record_file_id = serializers.SerializerMethodField()
    record_card = RecordCardShortListSerializer(read_only=True)

    class Meta:
        model = RecordChunkedFile
        fields = ("id", "created_at", "status", "completed_at", "record_card_id",
                  "record_card", "file", "filename", "offset", "url", "record_file_id", "file_type")
        read_only_fields = ("id", "created_at", "status", "completed_at", "md5", "record_file_id")

    def get_url(self, obj):
        url = reverse("private_api:record_cards:record_card_file_upload_chunk",
                      kwargs={"pk": obj.id}, request=self.context["request"])
        # todo: workaround of X-FORWARDED-PROTO incorrect in enviroments
        if not settings.DEBUG:
            url = url.replace("http://", "https://")
        return url

    def get_record_file_id(self, obj):
        return getattr(obj, "record_file_id", None)

    def run_validation(self, data=empty):
        validated_data = super().run_validation(data)
        errors = {}
        user_group = self.get_group_from_request(self.context.get("request"))
        if not GroupManageFiles(validated_data["record_card"], user_group,
                                self.context["request"].user).group_can_add_file():
            errors["record_card"] = _("Only the responsible profile of the Record Card can upload a file")

        self.check_record_number_files(validated_data, errors)

        if errors:
            raise ValidationError(errors, code="invalid")

        return validated_data

    @staticmethod
    def check_record_number_files(validated_data, errors):
        record_card = validated_data.get("record_card")
        record_files = record_card.recordfile_set.count()
        max_files = int(Parameter.get_parameter_by_key("API_MAX_FILES", 5))
        if record_files >= max_files:
            errors["record_card"] = _("The file can not be uploaded because the record has the "
                                      "maximum number of files {}").format(max_files)


class RecordFileShortSerializer(serializers.ModelSerializer):
    can_delete = serializers.BooleanField(source="can_be_deleted", required=False, read_only=True)

    class Meta:
        model = RecordFile
        fields = ("id", "file", "filename", "file_type", "delete_url", "can_delete", "created_at")
        read_only_fields = fields


class WorkflowSerializer(RecordCardWorkflowSerializer):
    record_cards = RecordCardShortListSerializer(many=True, source="recordcard_set")

    class Meta:
        model = Workflow
        fields = ("id", "user_id", "created_at", "updated_at", "main_record_card", "state", "close_date", "visual_user",
                  "element_detail_modified", "comments", "record_cards")
        read_only_fields = ("id", "user_id", "created_at", "updated_at")


class WorkflowPlanSerializer(serializers.Serializer):
    responsible_profile = serializers.CharField(required=False, allow_blank=True)
    start_date_process = serializers.DateField(required=False, allow_null=True)
    comment = serializers.CharField(validators=[WordsLengthAllowBlankValidator(words=2, words_length=4)])
    action_required = serializers.BooleanField(default=True, required=False)


class WorkflowPlanReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowPlan
        fields = ("responsible_profile", "start_date_process", "action_required")
        read_only_fields = ("responsible_profile", "start_date_process", "action_required")


class WorkflowResoluteExtraFieldsSerializer(serializers.ModelSerializer):
    workflow_resolution_id = serializers.IntegerField(required=True)
    resolution_date_end = serializers.DateTimeField(required=False, allow_null=True)
    ubication_start = UbicationSerializerMobile(required=False)
    ubication_end = UbicationSerializerMobile(required=False)

    class Meta:
        model = WorkflowResolutionExtraFields
        fields = ("workflow_resolution_id", "resolution_date_end", "ubication_start", "ubication_end")

    def save_ubication(self, ubication_dict):
        ubication_ser = UbicationSerializerMobile
        ubication = ubication_ser(data=ubication_dict)
        if ubication.is_valid():
            ub = ubication.save()
            return ub
        else:
            return Response({"detail": "The ubication is not valid", "errors": ubication.errors},
                            status=HTTP_400_BAD_REQUEST)


class WorkflowResoluteSerializer(serializers.Serializer):
    service_person_incharge = serializers.CharField(required=False, allow_blank=True, default="")
    resolution_type = serializers.IntegerField()
    resolution_date = serializers.DateTimeField(input_formats=("%Y-%m-%d %H:%M",), required=False, allow_null=True)
    resolution_comment = serializers.CharField(required=True, allow_blank=False,
                                               validators=[WordsLengthValidator(words=2, words_length=4)])

    class Meta:
        fields = ("service_person_incharge", "resolution_type", "resolution_date", "resolution_comment")

    def run_validation(self, data=empty):
        """
        We override the default `run_validation`, because the validation
        performed by validators and the `.validate()` method should
        be coerced into an error dictionary with a "non_fields_error" key.
        """
        resolution_types_enabled_ids = ResolutionType.objects.all().values_list("id", flat=True)
        if data.get("resolution_type") not in resolution_types_enabled_ids:
            raise ValidationError({"resolution_type": _("Incorrect value. Choose an enabled Resolution Type")})

        requires_appointment = self.context["record_card"].element_detail.requires_appointment
        if requires_appointment:

            if not data.get("resolution_date"):
                raise ValidationError(
                    {"resolution_date": _("A RecordCard that requires an appointment needs the "
                                          "appointment date&time")})

            if not data.get("service_person_incharge"):
                raise ValidationError(
                    {"service_person_incharge": _("A RecordCard that requires an appointment needs "
                                                  "the appointment person")})

        return super().run_validation(data)


class WorkflowResoluteDraftSerializer(serializers.Serializer):
    service_person_incharge = serializers.CharField(required=False)
    resolution_type = serializers.IntegerField(required=False)
    resolution_date = serializers.DateTimeField(input_formats=("%Y-%m-%d %H:%M",), required=False, allow_null=True)
    resolution_comment = serializers.CharField(required=False, allow_blank=False,
                                               validators=[WordsLengthValidator(words=2, words_length=4)])

    class Meta:
        fields = ("service_person_incharge", "resolution_type", "resolution_date", "resolution_comment")

    def run_validation(self, data=empty):
        """
        We override the default `run_validation`, because the validation
        performed by validators and the `.validate()` method should
        be coerced into an error dictionary with a "non_fields_error" key.
        """
        if "resolution_type" in data:
            resolution_types_enabled_ids = ResolutionType.objects.all().values_list("id", flat=True)
            if data.get("resolution_type") not in resolution_types_enabled_ids:
                raise ValidationError({"resolution_type": _("Incorrect value. Choose an enabled Resolution Type")})

        return super().run_validation(data)


class WorkflowResolutionSerializer(IrisSerializer, serializers.ModelSerializer):
    class Meta:
        model = WorkflowResolution
        fields = ("service_person_incharge", "resolution_type", "resolution_date", "is_appointment", "can_delete")
        read_only = ("service_person_incharge", "resolution_type", "resolution_date", "is_appointment", "can_delete")


class RecordCardWillBeSolvedSerializer(serializers.Serializer):
    applicant = serializers.IntegerField()

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass

    class Meta:
        fields = ("applicant",)


class WorkflowResoluteSimpleSerializer(serializers.Serializer):
    service_person_incharge = serializers.CharField(required=False, allow_blank=True, default="")
    resolution_type = ResolutionTypeSerializer()
    resolution_date = serializers.DateTimeField(input_formats=("%Y-%m-%d %H:%M",), required=False, allow_null=True)

    class Meta:
        fields = ("service_person_incharge", "resolution_type", "resolution_date")


class WorkflowFieldsSerializer(RecordCardWorkflowSerializer):
    workflow_resolute = WorkflowResoluteSimpleSerializer(source="workflowresolution")
    workflowresolutionextrafields = serializers.SerializerMethodField()

    class Meta:
        model = Workflow
        fields = ("id", "main_record_card", "state", "comments", "workflow_resolute", "workflowresolutionextrafields")
        read_only_fields = ("id", "user_id", "created_at", "updated_at")

    def get_workflowresolutionextrafields(self, workflow):
        try:
            obj = WorkflowResolutionExtraFields.objects.get(workflow_resolution=workflow.workflowresolution)
            return WorkflowResoluteExtraFieldsSerializer(obj).data
        except Exception as e:
            return None


class TwitterRecordSerializer(RecordCardSerializer):
    description = serializers.CharField(required=False, default='', allow_blank=True)
