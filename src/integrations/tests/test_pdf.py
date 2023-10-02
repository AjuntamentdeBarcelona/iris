import pytest
from integrations.tasks import generate_record_card_response_letter, send_answer
from iris_masters.models import ResponseChannel
from record_cards.tests.utils import CreateRecordCardMixin
from unittest.mock import Mock
from django.test import override_settings

dummy_create_pdf = Mock()
dummy_create_pdf2 = Mock()

@pytest.mark.django_db
class TestPdf(CreateRecordCardMixin):

    @pytest.mark.unit_test
    @override_settings(PDF_BACKEND='integrations.tests.test_pdf.dummy_create_pdf')
    def test_pdf_generate_record_card_response_letter(self):
        record_card = self.create_record_card()

        generate_record_card_response_letter(record_card.id, None)

        dummy_create_pdf.assert_called_once_with(record_card.id, None)

    @pytest.mark.unit_test
    @override_settings(PDF_BACKEND='integrations.tests.test_pdf.dummy_create_pdf2')
    @override_settings(LETTER_RESPONSE_ENABLED=True)
    def test_pdf_send_answer(self):
        record_card = self.create_record_card(create_record_card_response=True)
        record_card.recordcardresponse.response_channel_id = ResponseChannel.LETTER
        record_card.recordcardresponse.save()

        send_answer(record_card.id)

        dummy_create_pdf2.assert_called_once_with(record_card.pk)


