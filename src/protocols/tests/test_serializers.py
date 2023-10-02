import pytest

from protocols.serializers import ProtocolsSerializer


@pytest.mark.django_db
class TestProtocolsSerializer:

    @pytest.mark.parametrize("protocol_id,description,short_description,valid", (
            ("123", "description", "short_description", True),
            (None, "description", "short_description", False),
            ("123", None, "short_description", False),
            ("123", "description", "", False),
    ))
    def test_protocols_serializer(self, protocol_id, description, short_description, valid):
        data = {
            "protocol_id": protocol_id,
            "description": description,
            "short_description": short_description,
        }
        ser = ProtocolsSerializer(data=data)
        assert ser.is_valid() is valid, "Protocols Serializer fails"
        assert isinstance(ser.errors, dict)
