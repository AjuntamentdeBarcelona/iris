from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from rest_framework.exceptions import ValidationError
from rest_framework.fields import empty
from rest_framework.reverse import reverse
from drf_chunked_upload.serializers import ChunkedUploadSerializer
from rest_framework import serializers

from main.api.fields import CustomBase64File
from main.api.serializers import SerializerCreateExtraMixin, GetGroupFromRequestMixin
from record_cards.serializers import CheckFileExtensionsMixin
from support_info.models import SupportInfo, SupportChunkedFile


class SupportInfoSerializer(SerializerCreateExtraMixin, serializers.ModelSerializer):
    file = CustomBase64File(required=False, allow_null=True)

    class Meta:
        model = SupportInfo
        fields = ("id", "user_id", "created_at", "updated_at", "title", "description", "type", "category", "file",
                  "link")
        read_only_fields = ("id", "user_id", "created_at", "updated_at", "file")


class SupportInfoShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportInfo
        fields = ("id", "user_id", "created_at", "title", "type")


class SupportChunkedFileSerializer(SerializerCreateExtraMixin, GetGroupFromRequestMixin, CheckFileExtensionsMixin,
                                   ChunkedUploadSerializer):
    support_info_id = serializers.PrimaryKeyRelatedField(
        source="support_info", queryset=SupportInfo.objects.all(),
        error_messages={"does_not_exist": _("The selected Support Info does not exist")})
    support_info = SupportInfoShortSerializer(read_only=True)

    class Meta:
        model = SupportChunkedFile
        fields = ("id", "created_at", "status", "completed_at", "support_info_id", "support_info", "file", "filename",
                  "offset", "url")

    def run_validation(self, data=empty):
        validated_data = super().run_validation(data)
        if validated_data["support_info"].type != SupportInfo.DOCUMENTATION:
            raise ValidationError({"support_info_id": _("Support info must be documentation type")}, code="invalid")
        return validated_data

    def get_url(self, obj):
        url = reverse("private_api:support_info:support_info_file_upload_chunk",
                      kwargs={"pk": obj.id}, request=self.context["request"])
        # todo: workaround of X-FORWARDED-PROTO incorrect in enviroments
        if not settings.DEBUG:
            url = url.replace("http://", "https://")
        return url
