from unittest.mock import Mock

import pytest

from iris_masters.models import ResponseChannel
from record_cards.tests.utils import CreateRecordCardMixin
from integrations.tasks import send_answer
from django.test import override_settings

dummy_send_sms = Mock()


@pytest.mark.unit_test
@pytest.mark.django_db
class TestHooks(CreateRecordCardMixin):

    @override_settings(SMS_BACKEND='integrations.tests.test_sms.dummy_send_sms')
    def test_sms_send_answer(self):
        record_card = self.create_record_card(create_record_card_response=True)
        record_card.recordcardresponse.response_channel_id = ResponseChannel.SMS
        record_card.recordcardresponse.address_mobile_email = '1'*9
        record_card.recordcardresponse.save()

        send_answer(record_card.id)

        dummy_send_sms.assert_called_once_with(record_card.id, send_real_sms=False)

