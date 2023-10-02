from ariadna.models import Ariadna
from main.api.serializers import SerializerCreateExtraMixin
from rest_framework.serializers import ModelSerializer
from django.utils.translation import ugettext_lazy as _
from rest_framework import validators
from rest_framework import serializers


class AriadnaSerializer(SerializerCreateExtraMixin, ModelSerializer):
    
    APP_TYPE_P = "P"
    APP_TYPE_E = "E"

    def __init__(self, *args, **kwargs):
        self.TYPE = None
        super().__init__(*args, **kwargs)
        message = _("The year/input_number must be unique and there is another register with the same combination.")
        self.validators = [validators.UniqueTogetherValidator(queryset=Ariadna.objects.all(),
                                                              fields=["input_number", "year"],
                                                              message=message)]

    class Meta:
        model = Ariadna
        fields = "__all__"
        read_only_fields = ("id", "user_id", "created_at", "updated_at", "code", "deleted")

    def validate(self, data):
        data["presentation_date"] = data["date_us"].date()
        message = list()
        if data["applicant_type"].upper() == self.APP_TYPE_P:
            if "applicant_name" not in data:
                message.append(f"Para applicant_type {self.APP_TYPE_P} es necesario un applicant_name")
            if "applicant_surnames" not in data:
                message.append(f"Para applicant_type {self.APP_TYPE_P} es necesario un applicant_surnames")
        elif data["applicant_type"].upper() == self.APP_TYPE_E:
            if "social_reason" not in data:
                message.append(f"Para applicant_type {self.APP_TYPE_E} es necesario un social_reason")
        if len(message) != 0:
            raise serializers.ValidationError(message)
        else:
            return data

    def validate_applicant_type(self, value):
        if value.upper() == self.APP_TYPE_P:
            self.TYPE = value.upper()
            return value
        elif value.upper() == self.APP_TYPE_E:
            self.TYPE = value.upper()
            return value
        else:
            raise serializers.ValidationError(f"El campo applicant_type debe de ser {self.APP_TYPE_P} "
                                              f"para persona o {self.APP_TYPE_E} para entidad")

    def validate_applicant_name(self, value):
        if self.TYPE == self.APP_TYPE_E:
            return None
        elif self.TYPE == self.APP_TYPE_P:
            if value is not None:
                return value
            else:
                raise serializers.ValidationError("El campo applicant_name no puede ser nulo")

    def validate_applicant_surnames(self, value):
        if self.TYPE == self.APP_TYPE_E:
            return None
        elif self.TYPE == self.APP_TYPE_P:
            if value is not None:
                return value
            else:
                raise serializers.ValidationError("El campo applicant_surnames no puede ser nulo")

    def validate_social_reason(self, value):
        if self.TYPE == self.APP_TYPE_P:
            return None
        elif self.TYPE == self.APP_TYPE_E:
            if value is not None:
                return value
            else:
                raise serializers.ValidationError("El campo social_reason no puede ser nulo")

    def validate_contact(self, value):
        if self.TYPE == self.APP_TYPE_P:
            return None
        elif self.TYPE == self.APP_TYPE_E:
            if value is None:
                return "Ariadna"
            else:
                return value
