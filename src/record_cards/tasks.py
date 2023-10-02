import logging
from datetime import timedelta

from django.conf import settings
from django.core.management import call_command
from django.core.paginator import Paginator
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from iris_masters.models import Reason
from main.celery import app as celery_app
from profiles.models import Group
from record_cards.anonymize.citizen_anonymize import CitizenAnonymize
from record_cards.models import RecordCard, Applicant, Comment, Citizen, Request, Ubication
from record_cards.record_actions.copy_minio_files import CopyMinioFiles
from record_cards.record_actions.month_group_indicators import MonthGroupIndicators
from record_cards.record_actions.recover_ans_limits import RecoverAnsLimits
from record_cards.record_actions.recover_claims_closingdate import RecoverClaimsClosingDate
from record_cards.record_actions.recover_claims_recordcardresponse import RecoverClaimsRecordCardResponse
from record_cards.applicant_sources.applicant_source import IrisSource
from record_cards.record_actions.recover_close_user_audit import RecoverCloseUserAudit
from record_cards.record_actions.recover_theme_changed_info import RecoverThemeChangedInfo
from record_cards.record_actions.set_record_audits import SetRecordsAudits
from record_cards.record_actions.geocode import get_geocoder_class

from minio import __version__

logger = logging.getLogger(__name__)


@celery_app.task(queue=settings.CELERY_HIGH_QUEUE_NAME, max_retries=5)
def register_possible_similar_records(record_card_pk):
    """
    Task to register possible similar records for a created record card
    :return:
    """
    record_card = RecordCard.objects.get(pk=record_card_pk)
    record_card.set_similar_records()


@celery_app.task(queue=settings.CELERY_LOW_QUEUE_NAME)
def delete_chuncked_files():
    """
    Execute the delete_chuncked_files command.
    :return:
    """

    call_command('delete_chuncked_files')


@celery_app.task(queue=settings.CELERY_HIGH_QUEUE_NAME, max_retries=5)
def save_last_applicant_response(applicant_pk, recordcard_response_pk, authorization=True):
    """
    Task to save last applicant response information

    :return:
    """
    # Desactivat temporalment
    pass



@celery_app.task(queue=settings.CELERY_LOW_QUEUE_NAME, max_retries=5)
def calculate_last_month_indicators():
    """
    Task to calculate last month indicators for all the (no anonymous) groups.
    It will be called every first day of the months night

    :return:
    """
    last_month_day = timezone.now() - timedelta(days=1)
    MonthGroupIndicators(last_month_day.year, last_month_day.month).register_month_indicators()


@celery_app.task(queue=settings.CELERY_LOW_QUEUE_NAME, max_retries=5)
def calculate_month_indicators(year, month):
    """
    Task to calculate a month-year indcators for all the (no anonymous) groups.

    :param year: year to calculate the indicators
    :param month: month to calculate the indicators
    :return:
    """
    MonthGroupIndicators(year, month).register_month_indicators()


@celery_app.task(queue=settings.CELERY_LOW_QUEUE_NAME, max_retries=5)
def copy_record_files(origin_record_pk, destination_record_pk, group_pk):
    """
    Task to copy files from a record card to another

    :param origin_record_pk: ID of the source record card
    :param destination_record_pk: ID of the destination record card
    :param group_pk: ID of the group that does the action
    :return:
    """
    source_record = RecordCard.objects.get(pk=origin_record_pk)
    destination_record = RecordCard.objects.get(pk=destination_record_pk)
    group = Group.objects.get(pk=group_pk)
    try:
        logger.info('Minio version {}'.format(__version__))
        CopyMinioFiles(source_record, destination_record, group).copy_files()
    except Exception as e:
        logger.exception(e)
        comment = _("Files from record {} could not be copied").format(source_record.normalized_record_id)
        Comment.objects.create(record_card=destination_record, reason_id=Reason.RECORDFILE_COPIED,
                               group=group, comment=comment)
    Comment.objects.filter(record_card=destination_record, reason=Reason.COPY_FILES).delete()


@celery_app.task(queue=settings.CELERY_LOW_QUEUE_NAME, max_retries=5)
def sync_applicant_to_source(applicant_pk):
    """
    Task for sending the applicant to its outer origins.
    :param applicant_pk:
    """
    applicant = Applicant.objects.get(pk=applicant_pk)
    IrisSource().sync_to_origin(applicant)


@celery_app.task(queue=settings.CELERY_LOW_QUEUE_NAME, max_retries=5)
def set_record_card_audits():
    """
    Task for set record card audits
    """
    SetRecordsAudits().set_audits()


@celery_app.task(queue=settings.CELERY_LOW_QUEUE_NAME, max_retries=5)
def anonymize_applicant(applicant_pk):
    """
    Task for anonymize applicant, if it's possible
    """
    applicant = Applicant.all_objects.get(pk=applicant_pk)
    if applicant.can_be_anonymized:
        CitizenAnonymize(applicant.citizen).anonymize()
        applicant.pend_anonymize = False
        applicant.save()


@celery_app.task(queue=settings.CELERY_LOW_QUEUE_NAME, max_retries=0)
def check_authorization():
    """
    Task checking authorization
    """
    logging.info(f'APPLICANT | AUTHORIZATION CHECK | START')
    paginator = Paginator(Applicant.objects.all(), 1000)  # chunks of 1000, you can
    # change this to desired chunk size
    for page in range(1, paginator.num_pages + 1):
        logging.info(f'APPLICANT | AUTHORIZATION CHECK | PAGE | {page}')
        for a in paginator.page(page).object_list:
            if hasattr(a, 'applicantresponse'):
                a.flag_ca = a.applicantresponse.authorization
                a.save()
    logging.info(f'APPLICANT | AUTHORIZATION CHECK | READY')


@celery_app.task(queue=settings.CELERY_LOW_QUEUE_NAME, max_retries=1)
def post_migrate_years():
    Citizen.objects.filter(birth_year__lt=1900).update(birth_year=None)


@celery_app.task(queue=settings.CELERY_HIGH_QUEUE_NAME, max_retries=5)
def geocode_ubication(ubication_pk, derivate_id=None, user_id=None, reason=None):
    """
    Geocodes Ubication official street name
    """
    try:
        logger.info(f'GEOCODE | Ubication | {ubication_pk}')
        ubication = Ubication.objects.get(pk=ubication_pk)
        record_card_ubication_geocoder = get_geocoder_class()
        record_card_ubication_geocoder(ubication=ubication).update_ubication()
    except Exception as err:
        logger.info(f"{err}, {type(err)}, couldn't update ubication info.")
        raise err

    if derivate_id:
        record_card = RecordCard.objects.get(pk=derivate_id)
        logger.info(f'GEOCODE | DERIVATE | RECORD | {record_card.normalized_record_id}')
        record_card.derivate(user_id=user_id, reason=reason)
        logger.info(f'GEOCODE | DERIVATE | RECORD | SUCCESS {record_card.normalized_record_id}')


@celery_app.task(queue=settings.CELERY_HIGH_QUEUE_NAME, max_retries=5)
def remove_applicant_zero():
    citizen_zero_id = 0
    Request.objects.filter(applicant__citizen_id=citizen_zero_id).update(applicant=None)
    Applicant.all_objects.filter(citizen_id=citizen_zero_id).update(deleted=timezone.datetime(2020, 4, 3))


@celery_app.task(queue=settings.CELERY_HIGH_QUEUE_NAME, max_retries=5)
def recover_claims_response_config():
    RecoverClaimsRecordCardResponse().recover_recordcard_response()


@celery_app.task(queue=settings.CELERY_HIGH_QUEUE_NAME, max_retries=5)
def recover_close_user_audit():
    """
    Recover close user audits from records with state change fron pending answer to closed
    :return:
    """
    RecoverCloseUserAudit().recover_close_user()


@celery_app.task(queue=settings.CELERY_HIGH_QUEUE_NAME, max_retries=5)
def recover_ans_limits():
    """
    Recover ANS limits of records with theme changed
    :return:
    """
    RecoverAnsLimits().recover_limits()


@celery_app.task(queue=settings.CELERY_HIGH_QUEUE_NAME, max_retries=5)
def recover_claims_closing_dates():
    """
    Recover closing dates of opened claims
    :return:
    """
    RecoverClaimsClosingDate().recover_closing_dates()


@celery_app.task(queue=settings.CELERY_HIGH_QUEUE_NAME, max_retries=5)
def recover_theme_changed_info():
    """
    Recover theme record_type and process info
    :return:
    """
    RecoverThemeChangedInfo().recover_theme_info()
