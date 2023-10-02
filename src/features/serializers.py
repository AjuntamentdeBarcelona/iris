from django.conf import settings
from drf_yasg.utils import swagger_serializer_method
from rest_framework.exceptions import ValidationError
from rest_framework.fields import empty
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework import serializers

from django.utils.translation import gettext_lazy as _

from features.models import Feature, Mask, Values, ValuesType
from main.api.serializers import (IrisSerializer, SerializerCreateExtraMixin, SerializerUpdateExtraMixin)
from main.api.validators import BulkUniqueRelatedValidator
from main.utils import get_user_traceability_id


class ValuesSerializer(SerializerCreateExtraMixin, IrisSerializer):
    class Meta:
        model = Values
        fields = ("id", "user_id", "created_at", "updated_at", "description", "order")
        read_only_fields = ("id", "user_id", "created_at", "updated_at")


class ValuesTypeSerializer(SerializerCreateExtraMixin, SerializerUpdateExtraMixin, IrisSerializer):
    post_create_extra_actions = True

    values = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validators = [
            BulkUniqueRelatedValidator(
                main_fields=[field for field in self.get_translation_fields("description")],
                filter_fields=(), queryset=ValuesType.objects.all(),
                message=_("The description must be unique and there is another ValuesType with the same.")
            )
        ]

    class Meta:
        model = ValuesType
        fields = ("id", "description", "values", "can_delete")

    @swagger_serializer_method(serializer_or_field=serializers.ListField)
    def get_values(self, obj):
        return [ValuesSerializer(value).data for value in obj.values_set.filter(deleted__isnull=True)]

    def run_validation(self, data=empty):
        validated_data = super().run_validation(data)
        self.check_values()
        return validated_data

    def check_values(self):
        """
        Validate the list of values of the valyes type. If any is not valid, raise validationError
        :return:
        """
        values_errors = []
        raise_values_errors = False
        values_descriptions = {lang: {} for lang, name in settings.LANGUAGES}

        for value_data in self.initial_data.get("values", []):

            desc_errors = self.check_values_descriptions(value_data, values_descriptions)
            if desc_errors:
                values_errors.append(desc_errors)
                raise_values_errors = True
                continue

            try:
                value = Values.objects.get(pk=value_data.get("id"))
            except Values.DoesNotExist:
                value = None

            value_serializer = ValuesSerializer(data=value_data, context=self.context, instance=value)
            if value_serializer.is_valid():
                values_errors.append({})
            else:
                raise_values_errors = True
                values_errors.append(value_serializer.errors)
        if raise_values_errors:
            raise ValidationError({"values": values_errors})

    @staticmethod
    def check_values_descriptions(value_data, values_descriptions):
        """
        Check if the descriptions of a value has been introduced previously

        :param value_data: Value data send to the api
        :param values_descriptions: Descriptions of previous values on the data received
        :return: A dict with errors, if they exist
        """
        desc_errors = {}
        error_message = _("The description must be unique and there is another Value with the same.")

        for lang, name in settings.LANGUAGES:
            description = value_data.get("description_{}".format(lang))
            if description in values_descriptions[lang]:
                desc_errors["description_{}".format(lang)] = error_message
            else:
                values_descriptions[lang].update({description: True})
        return desc_errors

    def do_post_create_extra_actions(self, instance, validated_data):
        """
        Perform extra actions on create after the instance creation
        :param instance: Instance of the created object
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        if "values" in self.initial_data:
            self.serialize_values(instance.pk)

    def do_extra_actions_on_update(self, validated_data):
        """
        Perform extra actions on update
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        if "values" in self.initial_data:
            self.serialize_values(self.instance.pk)

    def serialize_values(self, values_type_pk):
        """
        Serialize values send to the endpoint, registering the new ones and appliying traceability if needed
        :param values_type_pk: Pk of the value type
        :return:
        """
        previous_values = Values.objects.filter(values_type_id=values_type_pk)
        values_pks = []
        for value_data in self.initial_data["values"]:
            value_data["values_type_id"] = values_type_pk
            if "request" in self.context:
                value_data["user_id"] = get_user_traceability_id(self.context["request"].user)
            else:
                value_data["user_id"] = ""

            try:
                value = Values.objects.get(pk=value_data.get("id"))
                values_pks.append(value.pk)
                if self.value_has_changed(value, value_data):
                    # If description has changed, remove the value and create a new one due to traceability
                    value.delete()
                    value_data.pop("id", None)
                    value = Values.objects.create(**value_data)
                    values_pks.append(value.pk)
            except Values.DoesNotExist:
                # if value does not exist, it will be created
                value_data.pop("id", None)
                value = Values.objects.create(**value_data)
                values_pks.append(value.pk)

        # Delete values that will not remain on the values type
        for prev_value in previous_values:
            if prev_value.pk not in values_pks:
                prev_value.delete()

    @staticmethod
    def value_has_changed(value, value_data):
        """
        Check if any of the language descriptions of the value or the order has changed
        :param value: value database object
        :param value_data: Inserted data
        :return: True if any of the language descriptions has changed else False
        """
        for lang_code, lang_desc in settings.LANGUAGES:
            description_lang_field = "description_{}".format(lang_code)
            if getattr(value, description_lang_field, None) != value_data.get(description_lang_field):
                return True
        if getattr(value, "order", None) != value_data.get("order"):
            return True
        return False


class ValuesTypeShortSerializer(ValuesTypeSerializer):
    class Meta:
        model = ValuesType
        fields = ("id", "description", "can_delete")
        read_only_fields = fields


class MaskSerializer(IrisSerializer):
    class Meta:
        model = Mask
        fields = ("id", "description")
        read_only_fields = fields


class FeatureSerializer(SerializerCreateExtraMixin, IrisSerializer):
    mask_id = PrimaryKeyRelatedField(
        source="mask", queryset=Mask.objects.all(),
        error_messages={"does_not_exist": _("The selected Mask does not exist")}, required=False, allow_null=True)
    mask = MaskSerializer(read_only=True)
    values_type_id = PrimaryKeyRelatedField(
        source="values_type", queryset=ValuesType.objects.all(), required=False, allow_null=True,
        error_messages={"does_not_exist": _("The selected values_type does not exist")})

    values_type = ValuesTypeSerializer(read_only=True)

    explanatory_text = serializers.CharField(required=False, allow_null=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validators = [
            BulkUniqueRelatedValidator(
                main_fields=[field for field in self.get_translation_fields("description")],
                filter_fields=(), queryset=Feature.objects.all(),
                message=_("The description must be unique and there is another Feature with the same.")
            )
        ]

    class Meta:
        model = Feature
        fields = ("id", "description", "values_type_id", "values_type", "is_special", "mask_id", "mask",
                  "explanatory_text", "can_delete", "editable_for_citizen", "visible_for_citizen", "codename",
                  "codename_iris")

    def run_validation(self, data=empty):
        validated_data = super().run_validation(data)

        if validated_data.get("mask") and validated_data.get("values_type"):
            error_message = _("Mask and ValuesType can not be assigned at the same time")
            raise ValidationError({"mask_id": error_message, "values_type_id": error_message})

        if not validated_data.get("mask") and not validated_data.get("values_type"):
            error_message = _("Mask or ValuesType must be assigned")
            raise ValidationError({"mask_id": error_message, "values_type_id": error_message})

        return validated_data


class FeatureShortSerializer(IrisSerializer):
    class Meta:
        model = Feature
        fields = ("id", "description", "is_special")
        read_only_fields = fields


class ValuesRegularSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    description = serializers.CharField()
    order = serializers.IntegerField()


class ValuesTypeRegularSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    description = serializers.CharField()
    values = serializers.SerializerMethodField()

    def get_values(self, obj):
        return [ValuesRegularSerializer(instance=value).data for value in obj.values_set.filter(deleted__isnull=True)]


class MaskRegularSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    description = serializers.CharField()


class FeatureRegularSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    description = serializers.CharField()
    values_type_id = serializers.IntegerField()
    values_type = ValuesTypeRegularSerializer()
    is_special = serializers.BooleanField()
    mask_id = serializers.IntegerField()
    codename = serializers.CharField()
    codename_iris = serializers.CharField()
    mask = MaskRegularSerializer()
    explanatory_text = serializers.CharField()
