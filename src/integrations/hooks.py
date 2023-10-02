"""
Hook functions for capturing important events in IRIS2 in a decoupled way.
IRIS2 core ensures that.
- If an errors is produced in one of these functions, it won't affect the normal
function of the system.
- This function won't affect significantly the performance of the operation. In
other words it will be excuted asynchroniously.

So this means that:
- Each function is responsible for tracking its errors, otherwise will be ignored.
- The function can make calls to external system or perform is tasks without caring
about the time.
"""
import logging

from integrations.services.mail.hooks import send_mail_message
from integrations.services.mail import hooks as email_hooks
from integrations.tasks import send_answer
from iris_masters.models import RecordState, ResponseChannel, Parameter
from django.conf import settings
from django.utils.module_loading import import_string

from celery import Celery

app = Celery()
logger = logging.getLogger(__name__)


def send_mail(subject, message, send_to=[], fail_silently=False):
    logger.info(f"LOGGER 1: Message {message}")
    send_mail_message(subject, message, send_to, fail_silently)


def record_card_was_created(record_card, sign_text='', letter_text=''):
    """
    Record card created actions
    :return:
    """
    logger.info("Enqueing record card create tasks {}".format(record_card.normalized_record_id))
    rc_id = record_card.recordcardresponse.get_response_channel()
    if rc_id == ResponseChannel.EMAIL:
        email_hooks.send_create_email.delay(record_card.pk)
    logger.info("Enqueued record card create tasks {}".format(record_card.normalized_record_id))


def record_card_state_was_changed(record_card):
    """
    Record card state changed actions
    :return:
    """
    logger.info("RECORD_CARD | {} | STATE CHANGE TO {} | Enqueing record card state change tasks ".format(
        record_card.normalized_record_id, record_card.record_state_id
    ))
    if record_card.record_state_id == RecordState.CLOSED:
        logger.info('RECORD CARD| {} | SEND ANSWER | ENQUEUE'.format(record_card.normalized_record_id))
        send_answer.delay(record_card.id)
        logger.info('RECORD CARD| {} | SEND ANSWER | ENQUEUED'.format(record_card.normalized_record_id))


def send_twitter(record_card, twitter_element_detail=None):
    logger.info('RECORD CARD| {} | TWITTER RECORD CREATED'.format(record_card.normalized_record_id))
    if is_twitter_record(record_card) and settings.TWITTER_ENABLED:
        twitter_text_response = get_twitter_text_message(record_card, twitter_element_detail)
        twitter_username = get_twitter_username(record_card)
        try:
            send_direct_message = import_string(settings.TWITTER_BACKEND)
            logger.info('RECORD CARD| {} | SENDING TO TWITTER | Enqueing'.format(record_card.normalized_record_id))
            send_direct_message(twitter_username, twitter_text_response)
            logger.info('RECORD CARD| {} | SENDING TO TWITTER | Enqueed'.format(record_card.normalized_record_id))
        except ImportError:
            logger.info(f"Unable to locate the module {settings.TWITTER_BACKEND}, couldn't queue record card.")


def is_twitter_record(record_card):
    twitter_input_channel_id = Parameter.get_parameter_by_key('TWITTER_INPUT_CHANNEL', None)
    return record_card.input_channel.id == int(twitter_input_channel_id)


def get_twitter_username(record_card):
    twitter_attribute_pk = Parameter.get_parameter_by_key('TWITTER_ATTRIBUTE', None)
    return record_card.recordcardfeatures_set.get(feature_id=twitter_attribute_pk).value


def get_twitter_text_message(record_card, twitter_element_detail):
    twitter_text_response = Parameter.get_parameter_by_key('TWITTER_RESPONSE_TEXT', None)
    return twitter_text_response.format(twitter_element_detail)


def opendata_getvalues():
    from integrations.services.batch_processes.tools import FilesTools as ft
    from integrations.services.batch_processes.opendata.queryset import OpenDataQuerySets
    from datetime import datetime
    month = datetime.now().month
    get_trimester = {1: 4, 2: 4, 3: 4, 4: 1, 5: 1, 6: 1, 7: 2, 8: 2, 9: 2, 10: 3, 11: 3, 12: 3}
    trimester = get_trimester.get(month)
    year = datetime.now().year
    if trimester == 4:
        year = year - 1
    path = 'iris/OpenData_Trimestre_' + str(trimester) + '_' + str(year) + '.csv'
    od = OpenDataQuerySets(year=year, trimester=trimester)
    ft(od, call=False).file_writer(path, 'file_open_data', ',', add_headers=True, lineterminator=True,
                                   encoding='utf-8', xml=False)


def opendata_validate(year=2020, trimester=1):
    from integrations.services.batch_processes.tools import FilesTools as ft
    from integrations.services.batch_processes.opendata.queryset import OpenDataQuerySets
    path = 'iris/OpenData_Trimestre' + str(trimester) + '_' + str(year) + '.csv'
    od = OpenDataQuerySets(year=year, trimester=trimester)
    ft(od, call=False).file_writer(path, 'validation', ',', add_headers=True, lineterminator=True,
                                   encoding='utf-8', xml=True)
