from django.conf import settings
from django.utils import translation
from django.utils.translation import gettext_lazy as _
import django.core.mail.backends.smtp

from emails.emails import RecordCardAnswer, CreateRecordCardEmail
from iris_masters.models import Reason
from record_cards.models import RecordCard, RecordState, RecordCardTextResponse, Comment
import logging
from integrations.services.mail.mails import CloseRecordEmail
from main.celery import app as celery_app

logger = logging.getLogger(__name__)

class LoggingBackend(django.core.mail.backends.smtp.EmailBackend):

  def send_messages(self, email_messages):
    for email_message in email_messages:
        logger.info(f"LOGGER 2: {email_message.body}")
    try:
        for msg in email_messages:
            logger.info(u"Sending message '%s' to recipients: %s", msg.subject, msg.to)
    except:
        logger.exception("Problem logging recipients, ignoring")

    return super(LoggingBackend, self).send_messages(email_messages)


@celery_app.task(queue=settings.CELERY_LOW_QUEUE_NAME, max_retries=5)
def send_create_email(record_card_id):
    logger.info('IRIS|RECORD {} | CREATE MAIL'.format(record_card_id))
    record_card = RecordCard.objects.get(pk=record_card_id)
    old_lang = translation.get_language()
    translation.activate(record_card.language)
    CreateRecordCardEmail(record_card).send()
    translation.activate(old_lang)
    logger.info('IRIS|RECORD {} | CREATE MAIL'.format(record_card_id))


@celery_app.task(queue=settings.CELERY_LOW_QUEUE_NAME, max_retries=5)
def send_mail_message(record_card_id, sender=''):
    """
    @todo set the correct email
    :param record_card_id:
    :param sender:
    :return:
    """
    if not sender:
        sender = settings.DEFAULT_FROM_EMAIL

    record_card = RecordCard.objects.get(pk=record_card_id)
    old_lang = translation.get_language()
    translation.activate(record_card.language)
    receiver = [record_card.recordcardresponse.address_mobile_email]
    if record_card.record_state_id == RecordState.CLOSED:
        logger.info('IRIS|RECORD CLOSED MAIL to {}'.format(receiver)+' with sender {}'.format(sender))
        email = CloseRecordEmail(record_state='tancament', record_id=record_card.normalized_record_id)
        email.send(from_email=sender, to=receiver,)
    translation.activate(old_lang)


@celery_app.task(queue=settings.CELERY_LOW_QUEUE_NAME, max_retries=5)
def send_answer_email(record_card_id, sender=''):
    logger.info('IRIS|RECORD CLOSED MAIL RECORD_ID={}'.format(record_card_id))
    record_card = RecordCard.objects.get(pk=record_card_id)
    logger.info(f"RECORD_CARD OBJECT {record_card}")
    old_lang = translation.get_language()
    translation.activate(record_card.language)
    email = RecordCardAnswer(record_card)
    from_mail = email.get_from_email()
    logger.info('IRIS|RECORD CLOSED ENQUEUING MAIL RECORD_ID={}, TO={}, FROM={}'.format(
        record_card_id, email.applicant_email, from_mail
    ))

    attachments = []
    text_response = RecordCardTextResponse.objects.filter(record_card_id=record_card.pk).order_by("created_at").first()
    logger.info(f"TEXT RESPONSE {text_response}")
    logger.info(f"TEXT RESPONSE ENABLED {text_response.enabled_record_files}")

    if text_response:
        for attachment in text_response.enabled_record_files:
            attachments.append({"filename": attachment.filename, "attachment": attachment.file.read()})
    logger.info(f"EMAIL: {email}")

    email.send(attachments=attachments)
    logger.info('IRIS|RECORD CLOSED ENQUEUED MAIL RECORD_ID={}, TO={}, FROM={}'.format(
        record_card_id, email.applicant_email, from_mail
    ))
    translation.activate(old_lang)


@celery_app.task(queue=settings.CELERY_LOW_QUEUE_NAME, max_retries=5)
def avoid_answer(record_card_id, sender=''):
    logger.info('IRIS| RECORD AVOID ANSWER RECORD_ID={}'.format(record_card_id))
    old_lang = translation.get_language()
    translation.activate(settings.LANGUAGE)
    rc = RecordCard.objects.only('responsible_profile_id').get(pk=record_card_id)
    Comment.objects.create(record_card_id=record_card_id, group_id=rc.responsible_profile_id,
                           reason_id=Reason.RECORDCARD_NO_ANSWER,
                           comment=_('Record has been marked for not sending answer.'))
    translation.activate(old_lang)
