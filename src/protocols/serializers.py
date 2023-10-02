from main.api.serializers import SerializerCreateExtraMixin
from protocols.models import Protocols
from rest_framework import serializers


class ProtocolsSerializer(SerializerCreateExtraMixin, serializers.ModelSerializer):

    can_delete = serializers.BooleanField(source="can_be_deleted", required=False, read_only=True)

    class Meta:
        model = Protocols
        fields = ("id", "user_id", "created_at", "updated_at", "protocol_id", "description", "short_description",
                  "can_delete")
        read_only_fields = ("id", "user_id", "created_at", "updated_at", "can_delete")
