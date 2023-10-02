import pytest
from integrations.tasks import generate_record_card_response_letter
from record_cards.tests.utils import CreateRecordCardMixin
from django.core.files.storage import default_storage
from record_cards.models import RecordCardTextResponse
from model_mommy import mommy


@pytest.mark.external_integration_test
@pytest.mark.django_db
class TestHooks(CreateRecordCardMixin):

    def test_send_pdf_to_minio(self):
        record_card = self.create_record_card(create_record_card_response=True)
        mommy.make(RecordCardTextResponse, record_card=record_card, user_id='test')
        generate_record_card_response_letter(record_card.id, file_name='TEST.pdf')
        assert default_storage.exists('TEST.pdf') is True
