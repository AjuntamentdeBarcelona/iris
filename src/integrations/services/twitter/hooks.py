from integrations.services.twitter.services import TwitterServices
from rest_framework.exceptions import ValidationError
from integrations.services.twitter.config import message_error
import logging

logger = logging.getLogger(__name__)


def send_direct_message(username, text):
    logger.info('TWITTER|SENDING MESSAGE TO|ID={}|WITH TEXT: {}'.format(username, text))
    result = TwitterServices().send_direct_message(username, text)
    if result.status_code != 200:
        raise ValidationError({'global': message_error})
    logger.info('TWITTER|SEND MESSAGE TO|ID={}|WITH TEXT: {}'.format(username, text))
    return result
