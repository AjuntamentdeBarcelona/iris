import pytest
from integrations.services.mail.hooks import send_mail_message, send_create_email
from record_cards.tests.utils import CreateRecordCardMixin
from record_cards.models import RecordState
from django.core import mail
from communications.tests.utils import load_missing_data
from iris_masters.models import Parameter


@pytest.mark.django_db
class TestHooks(CreateRecordCardMixin):
    def test_record_card_closed_email(self):
        load_missing_data()
        record_card = self.create_record_card(create_record_card_response=True, record_state_id=RecordState.CLOSED)
        send_mail_message(record_card_id=record_card.pk, sender='Test@iris.net')
        assert len(mail.outbox) == 1

    def test_record_card_opened_email(self):
        load_missing_data()
        if not Parameter.objects.filter(parameter='URL_RECLAMA_QUEIXES_CA'):
            param = Parameter(parameter='URL_RECLAMA_QUEIXES_CA', valor='test_reclama')
            param.save()
        if not Parameter.objects.filter(parameter='URL_RECLAMA_QUEIXES_ES'):
            url_reclama_queixes = Parameter(parameter='URL_RECLAMA_QUEIXES_ES', valor='test')
            url_reclama_queixes.save()
        record_card = self.create_record_card(create_record_card_response=True,
                                              record_state_id=RecordState.PENDING_VALIDATE)
        send_create_email(record_card_id=record_card.pk)
        assert len(mail.outbox) == 1
