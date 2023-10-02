from django.utils.functional import cached_property
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import empty

from django.utils.translation import ugettext_lazy as _
from rest_framework.validators import UniqueValidator

from iris_masters.models import ResponseType
from iris_masters.serializers import ResponseTypeShortSerializer
from iris_templates.models import IrisTemplate, IrisTemplateRecordTypes
from iris_templates.template_params import get_required_params, get_appointment_text, APPOINTMENT_TEMPLATE
from main.api.serializers import ManyToManyExtendedSerializer, SerializerCreateExtraMixin, SerializerUpdateExtraMixin


class IrisTemplateRecordTypesSerializer(serializers.ModelSerializer):
    description = serializers.StringRelatedField(source='record_type', read_only=True)

    class Meta:
        model = IrisTemplateRecordTypes
        fields = ('record_type', 'description')


class IrisTemplateSerializer(SerializerCreateExtraMixin, SerializerUpdateExtraMixin, serializers.ModelSerializer):
    post_create_extra_actions = True

    description = serializers.CharField(validators=[UniqueValidator(queryset=IrisTemplate.objects.all(),
                                                                    lookup='iexact')])
    can_delete = serializers.BooleanField(source='can_be_deleted', required=False, read_only=True)
    response_type_id = serializers.PrimaryKeyRelatedField(
        queryset=ResponseType.objects.all(), source='response_type',
        error_messages={"does_not_exist": _("The selected ResponseType does not exists")})
    response_type = ResponseTypeShortSerializer(read_only=True)

    record_types = ManyToManyExtendedSerializer(source='iristemplaterecordtypes_set', required=False,
                                                **{'many_to_many_serializer': IrisTemplateRecordTypesSerializer,
                                                   'model': IrisTemplateRecordTypes, 'related_field': 'iris_template',
                                                   'to': 'record_type'})

    class Meta:
        model = IrisTemplate
        fields = ('id', 'user_id', 'created_at', 'updated_at', 'description', 'response_type', 'response_type_id',
                  'write_medium_catalan', 'write_medium_spanish', 'write_medium_english',
                  'sms_medium_catalan', 'sms_medium_spanish', 'sms_medium_english', 'can_delete', 'record_types')
        read_only_fields = ('id', 'user_id', 'created_at', 'updated_at', 'can_delete')

    def run_validation(self, data=empty):
        validated_data = super().run_validation(data)
        validation_errors = {}

        self.check_write_medium_fields(validated_data, validation_errors)
        self.check_sms_medium_fields(validated_data, validation_errors)

        self.check_record_types_unique_template_by_response_type(validated_data, validation_errors)

        if validation_errors:
            raise ValidationError(validation_errors)

        return validated_data

    def check_record_types_unique_template_by_response_type(self, validated_data, validation_errors):
        """

        :param validated_data: dict with validated data
        :param validation_errors: dict with validation errors
        :return:
        """
        if 'record_types' in self.initial_data:
            record_types_errors = []
            iris_template_pk = self.instance.pk if self.instance else None
            add_record_types_error = False
            for record_type in self.initial_data['record_types']:

                record_type_error = {}

                IrisTemplateRecordTypes.check_unique_response_type_for_record_type(
                    record_type['record_type'], validated_data['response_type'].pk, iris_template_pk, record_type_error)
                if record_type_error:
                    add_record_types_error = True
                record_types_errors.append(record_type_error)

            if add_record_types_error:
                validation_errors['record_types'] = record_types_errors

    @staticmethod
    def check_write_medium_fields(validated_data, validation_errors):
        """
        Check that if one field of write medium is filled, the other is filled too

        :param validated_data: dict with validated data
        :param validation_errors: dict with validation errors
        :return:
        """
        IrisTemplate.check_language_field(
            validated_data.get('write_medium_catalan'), validated_data.get('write_medium_spanish'),
            'write_medium_catalan', 'write_medium_spanish', validation_errors)
        IrisTemplate.check_language_field(
            validated_data.get('write_medium_spanish'), validated_data.get('write_medium_catalan'),
            'write_medium_spanish', 'write_medium_catalan', validation_errors)

    @staticmethod
    def check_sms_medium_fields(validated_data, validation_errors):
        """
        Check that if one field of sms medium is filled, the other is filled too
        :param validated_data: dict with validated data
        :param validation_errors: dict with validation errors
        :return:
        """
        IrisTemplate.check_language_field(
            validated_data.get('sms_medium_catalan'), validated_data.get('sms_medium_spanish'), 'sms_medium_catalan',
            'sms_medium_spanish', validation_errors)
        IrisTemplate.check_language_field(
            validated_data.get('sms_medium_spanish'), validated_data.get('sms_medium_catalan'), 'sms_medium_spanish',
            'sms_medium_catalan', validation_errors)

    def do_post_create_extra_actions(self, instance, validated_data):
        """
        Perform extra actions on create after the instance creation
        :param instance: Instance of the created object
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        self.set_record_types(validated_data, instance)

    def do_extra_actions_on_update(self, validated_data):
        """
        Perform extra actions on update
        :param validated_data: Dict with validated data of the serializer
        :return:
        """

        self.set_record_types(validated_data, self.instance)

    def set_record_types(self, validated_data, instance):
        """

        :param validated_data: Dict with validated data of the serializer
        :param instance: Instance of the template object
        :return:
        """

        if 'record_types' in self.initial_data:
            ser = ManyToManyExtendedSerializer(**{'many_to_many_serializer': IrisTemplateRecordTypesSerializer,
                                                  'model': IrisTemplateRecordTypes, 'related_field': 'iris_template',
                                                  'to': 'record_type', 'related_instance': instance},
                                               source='iristemplaterecordtypes_set',
                                               data=self.initial_data['record_types'])
            ser.bind(field_name='', parent=self)
            if ser.is_valid():
                ser.save()
            validated_data.pop(ser.source, None)


class IrisTemplateShortSerializer(IrisTemplateSerializer):
    response_type = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = IrisTemplate
        fields = ('id', 'user_id', 'created_at', 'updated_at', 'description', 'response_type', 'write_medium_catalan',
                  'write_medium_spanish', 'sms_medium_catalan', 'sms_medium_spanish')
        read_only_fields = fields


class IrisRecordTextSerializer(IrisTemplateShortSerializer):
    text = serializers.SerializerMethodField()
    original_text = serializers.SerializerMethodField()
    is_own = serializers.SerializerMethodField()
    is_group = serializers.SerializerMethodField()
    is_default = serializers.SerializerMethodField()
    text_attribute = serializers.SerializerMethodField()

    class Meta:
        model = IrisTemplate
        fields = ('id', 'user_id', 'created_at', 'updated_at', 'description', 'response_type', 'text', 'original_text',
                  'is_own', 'is_group', 'text_attribute', 'is_default')
        read_only_fields = fields

    def get_original_text(self, obj):
        if self.is_sms() or self.get_is_group(obj):
            return getattr(obj, self.context['rendered_template_attribute'])
        return '<p>{},</p><p></p>'.format(self.extra_template_params.get('greeting')) \
               + getattr(obj, self.context['rendered_template_attribute']) \
               + '<p></p><p>{}</p>'.format(self.appointment_text) \
               + '<p></p><p>{}</p>'.format(self.extra_template_params.get('goodbye'))

    @property
    def record_card(self):
        return self.context.get('record_card')

    @property
    def appointment_text(self):
        if self.is_appointment:
            return get_appointment_text(self.resolution, self.extra_template_params.get('appointment_text'))
        return ''

    @cached_property
    def resolution(self):
        """
        :return: True if the record card has an appointment set, in which case must be included in the email
        """
        if hasattr(self.record_card, "workflow"):
            return getattr(self.record_card.workflow, "workflowresolution", None)

    @cached_property
    def is_appointment(self) -> bool:
        """
        :return: True if the record card has an appointment set, in which case must be included in the email
        """
        return self.resolution.is_appointment if self.resolution else False

    @cached_property
    def extra_template_params(self):
        return get_required_params(self.context.get('language'), {
            'greeting': 'TEXTCARTACAP',
            'goodbye': 'TEXTCARTAFI',
            'signature_bcn': 'TEXTCARTASIGNATURA',
            "ans_exceeded_text": "DISCULPES_RETARD",
            "appointment_text": APPOINTMENT_TEMPLATE,
        })

    def is_sms(self):
        return self.context.get('is_sms', False)

    def get_text(self, obj):
        if not self.context['rendered_template_attribute']:
            return ''
        return self.context['template_renderer'].render(self.get_original_text(obj))

    def get_is_own(self, obj):
        return getattr(obj, 'is_own', False)

    def get_is_group(self, obj):
        return getattr(obj, 'is_group_template', False)

    def get_is_default(self, obj):
        return getattr(obj, 'is_default', False)

    def get_text_attribute(self, obj):
        return self.context.get('rendered_template_attribute')


class VariableSerializer(serializers.Serializer):
    name = serializers.CharField()


class ApplicantCommunicationTextSerializer(serializers.Serializer):
    header = serializers.CharField()
    answer_body = serializers.CharField()
    simple_body = serializers.CharField()
    footer = serializers.CharField()
    answer_tag = serializers.CharField()


class SaveForRecordSerializers(serializers.ModelSerializer):
    class Meta:
        model = IrisTemplate
        fields = ('id', 'description', 'write_medium_catalan', 'write_medium_spanish', 'write_medium_english',
                  'sms_medium_catalan', 'sms_medium_spanish', 'sms_medium_english', 'group',)
        read_only_fields = ('id', 'group')
