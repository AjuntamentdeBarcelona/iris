import pytest

from public_external_processing.serializers import ExternalProcessedSerializer
from record_cards.tests.utils import CreateRecordCardMixin


@pytest.mark.django_db
class TestExternalProcessedSerializer(CreateRecordCardMixin):

    @pytest.mark.parametrize("comment,valid", (
            ("Comentari de prova", True),
            ("Test", False),
            ("pro va", False),
            ("", False),
    ))
    def test_external_processed_serializer(self, comment, valid):
        data = {"comment": comment}

        ser = ExternalProcessedSerializer(data=data)
        assert ser.is_valid() is valid, "External Processed serializer fails"
        assert isinstance(ser.errors, dict)
