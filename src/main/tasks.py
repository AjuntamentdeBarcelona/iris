import logging
from django.core.management import call_command
from django.conf import settings

from main.celery import app as celery_app


@celery_app.task(queue=settings.CELERY_LOW_QUEUE_NAME)
def send_mail():
    """
    Execute the send_mail command.
    :return:
    """

    if not settings.SEND_MAIL_ACTIVE:
        return
    call_command('send_mail', "--message_limit=5")


@celery_app.task(queue=settings.CELERY_LOW_QUEUE_NAME)
def retry_deferred():
    """
    Execute the retry_deferred command with a max-retries of 15
    :return:
    """

    if not settings.SEND_MAIL_ACTIVE:
        return
    call_command('retry_deferred', "--max-retries=15")


@celery_app.task(bind=True, queue=settings.CELERY_HIGH_QUEUE_NAME, max_retries=5)
def celery_test_task(self):
    """
    Test celery use
    :return:
    """
    logger = logging.getLogger(__name__)
    logger.info("Celery test task!")


@celery_app.task(bind=True, queue=settings.CELERY_LOW_QUEUE_NAME, max_retries=1)
def invalidate_cachalot(self):
    """
    Test celery use
    :return:
    """
    logger = logging.getLogger(__name__)
    logger.info("Invalidating cachalot")
    call_command("invalidate_cachalot")
    logger.info("Cachalot invalidated")
