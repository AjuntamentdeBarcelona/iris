import pytest

from features.models import Feature
from integrations.hooks import send_twitter
from iris_masters.models import Parameter, InputChannel
from record_cards.tests.utils import CreateRecordCardMixin
from unittest.mock import Mock
from django.test import override_settings
from integrations.hooks import get_twitter_username, get_twitter_text_message

dummy_send_direct_message = Mock()


@pytest.mark.django_db
class TestTwitter(CreateRecordCardMixin):

    @pytest.mark.unit_test
    @override_settings(TWITTER_ENABLED=True)
    @override_settings(TWITTER_BACKEND='integrations.tests.test_twitter.dummy_send_direct_message')
    def test_twitter_send_twitter(self):
        twitter_id = 10
        input_channel_id = 76
        if not InputChannel.objects.filter(id=input_channel_id):
            input_channel = InputChannel(id=input_channel_id)
            input_channel.save()
        else:
            input_channel = InputChannel.objects.get(id=input_channel_id)
        if not Parameter.objects.filter(parameter='TWITTER_INPUT_CHANNEL'):
            param = Parameter(parameter='TWITTER_INPUT_CHANNEL', valor=input_channel_id)
            param.save()
        if not Parameter.objects.filter(parameter='TWITTER_ATTRIBUTE'):
            param = Parameter(parameter='TWITTER_ATTRIBUTE', valor=twitter_id)
            param.save()
        if not Parameter.objects.filter(parameter='TWITTER_RESPONSE_TEXT'):
            param = Parameter(parameter='TWITTER_RESPONSE_TEXT', valor='test')
            param.save()
        feature = Feature(id=twitter_id)
        feature.save()
        record_card = self.create_record_card(input_channel=input_channel, input_channel_description='TWITTER', features=[feature])
        element_detail = 123
        result = send_twitter(record_card, element_detail)
        if result:
            result = True
        else:
            result = False
        username = get_twitter_username(record_card)
        message = get_twitter_text_message(record_card, element_detail)
        dummy_send_direct_message.assert_called_once_with(username, message)
        assert result is False

