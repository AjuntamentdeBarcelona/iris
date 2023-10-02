import logging
from datetime import datetime

from django.conf import settings

from integrations.data_checks.integrations_parameters import check_integrations_parameters
from main.celery import app as celery_app

from integrations.models import BatchFile
from integrations.services.batch_processes.tools import FilesTools
from integrations.services.batch_processes.opendata.queryset import OpenDataQuerySets
from integrations.services.mail.hooks import avoid_answer
from integrations.services.mail import hooks as email_hooks
from iris_masters.models import ResponseChannel, Parameter
from record_cards.models import RecordCard, RecordCardTextResponse
from django.utils.module_loading import import_string


logger = logging.getLogger(__name__)


@celery_app.task(queue=settings.CELERY_LOW_QUEUE_NAME, max_retries=5)
def generate_open_data_report(month=None, year=None):
    if not month:
        month = datetime.now().month
    get_trimester = {1: 4, 2: 4, 3: 4, 4: 1, 5: 1, 6: 1, 7: 2, 8: 2, 9: 2, 10: 3, 11: 3, 12: 3}
    trimester = get_trimester.get(month)

    if not year:
        year = datetime.now().year

    if trimester == 4:
        year = year - 1

    path = 'opendata_views/OpenData_Trimestre' + str(trimester) + '_' + str(year) + '.csv'
    od = OpenDataQuerySets(year=year, trimester=trimester, to_validate=False, create=False)
    FilesTools(od, call=False).file_writer_partition(path, 'partitioning', ',', add_headers=True, lineterminator=True,
                                                     encoding='utf-8', xml=False)
    BatchFile.objects.create(process='od', file=path, year=year, trimestre=trimester)


@celery_app.task(queue=settings.CELERY_LOW_QUEUE_NAME, max_retries=5)
def validate_batch_file(batch_file_id):
    batch_file = BatchFile.objects.get(id=batch_file_id)
    path = 'opendata_views/OpendataCVS_Trimestre' + str(batch_file.trimestre) + '_' + str(batch_file.year) + '.csv'
    od = OpenDataQuerySets(year=batch_file.year, trimester=batch_file.trimestre)
    FilesTools(od, call=False).file_writer_partition(path,
                                                     'definitive_validation',
                                                     ',',
                                                     add_headers=True,
                                                     lineterminator=True,
                                                     encoding='utf-8', xml=True,
                                                     move_to_sftp=True)
    BatchFile.objects.filter(id=batch_file_id).update(file=path, status=BatchFile.VALIDATED)


@celery_app.task(queue=settings.CELERY_HIGH_QUEUE_NAME, max_retries=5)
def generate_record_card_response_letter(record_card_id, file_name=None):
    if settings.PDF_BACKEND is not None:
        try:
            create_pdf = import_string(settings.PDF_BACKEND)  # integrations.services.pdf.hooks.create_pdf
            create_pdf(record_card_id, file_name)
        except ImportError:
            logger.info(f"Unable to locate the module {settings.PDF_BACKEND}, couldn't create PDF.")
    else:
        logger.info("No PDF generator backend module was specified.")


@celery_app.task(queue=settings.CELERY_LOW_QUEUE_NAME, max_retries=5)
def send_answer(record_card_id):
    """
    Generates the report_type from BiIrisQuerySets and saves the result to the destination path.
    :param record_card_id
    (todo) Review comment (Doesn't seem to be using BiIrisQuerySets)
    """
    record_card = RecordCard.objects.get(id=record_card_id)
    text_response = RecordCardTextResponse.objects.filter(
        record_card_id=record_card.pk
    ).order_by("created_at").first()
    if text_response and text_response.avoid_send:
        logger.info("RECORD CARD| {} | AVOID ANSWER | WILL GENERATE TRACE".format(record_card.normalized_record_id))
        avoid_answer.delay(record_card.pk)
    else:
        rc_id = record_card.recordcardresponse.get_response_channel()
        if rc_id == ResponseChannel.EMAIL:
            email_hooks.send_answer_email(record_card.pk)
        elif rc_id == ResponseChannel.SMS:
            phone_number = record_card.recordcardresponse.address_mobile_email
            if 9 <= len(phone_number) <= 12:
                if settings.SMS_BACKEND is not None:
                    try:
                        send_sms = import_string(settings.SMS_BACKEND)
                        send_sms(
                            record_card.pk, send_real_sms=Parameter.get_parameter_by_key("SMSENABLE", "0") == "1"
                        )
                    except ImportError:
                        logger.info(f"Unable to locate the module {settings.SMS_BACKEND}, couldn't send SMS.")
                else:
                    logger.info("No SMS backend sender module was specified.")
        elif rc_id == ResponseChannel.LETTER:
            if settings.LETTER_RESPONSE_ENABLED:
                logger.info("RECORD CARD| {} | LETTER | Start Generating".format(record_card.normalized_record_id))
                if settings.PDF_BACKEND is not None:
                    try:
                        create_pdf = import_string(settings.PDF_BACKEND)  # integrations.services.pdf.hooks.create_pdf
                        create_pdf(record_card.pk)
                        logger.info("RECORD CARD| {} | LETTER | Generated".format(record_card.normalized_record_id))
                    except ImportError:
                        logger.info(f"Unable to locate the module {settings.PDF_BACKEND}, couldn't create PDF.")
                else:
                    logger.info("No PDF generator backend module was specified.")
            else:
                logger.info("Letter response isn't enabled, letters won't be sent.")


@celery_app.task(queue=settings.CELERY_LOW_QUEUE_NAME, max_retries=1)
def post_migrate_tasks():
    check_integrations_parameters(None)
