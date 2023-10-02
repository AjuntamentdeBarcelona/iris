import logging

from main.celery import app as celery_app
from django.conf import settings
from record_cards.models import RecordCard
from integrations.services.sms.services import SmsServices
from record_cards.templates import render_record_response
from record_cards.models import RecordCardResponse

logger = logging.getLogger(__name__)


@celery_app.task(queue=settings.CELERY_HIGH_QUEUE_NAME, max_retries=5)
def sms_send(record_card_id, send_real_sms=False, buroSMS='false', application='IRIS',  destination='ajunt BCN',
             user=''):

    logger.info('SMS|RECORD-CARD-STATE-CLOSED|START SENT|ID={}'.format(record_card_id))
    record_card = RecordCard.objects.get(pk=record_card_id)
    message = render_record_response(record_card)
    telephone = record_card.recordcardresponse.address_mobile_email
    logger.info('SMS|RECORD-CARD-STATE-CLOSED|RENDERED MESSAGE|ID={}'.format(record_card_id))
    result = SmsServices().send_sms(message, telephone, application=application,
                                    simulation='true' if not send_real_sms else 'false',
                                    user=user, buroSMS=buroSMS, destination=destination)
    logger.info('SMS|RECORD-CARD-STATE-CLOSED|SENT|ID={}'.format(record_card_id))
    return result


def sms_sending_pendents():
    record_cards = RecordCardResponse.objects.raw("""
    SELECT f1.id, f1.record_card_id, f2.normalized_record_id, f2.closing_date, f1.address_mobile_email
    from record_cards_recordcardresponse f1
    join record_cards_recordcard f2 on f2.id=f1.record_card_id
    where (f2.closing_date between '2021-02-08' and '2021-03-19 12:12:09')
    and f1.response_channel_id=1
    """)
    for record in record_cards:
        sms_send.delay(record.record_card_id, send_real_sms=True)
