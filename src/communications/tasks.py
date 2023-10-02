from django.core.management import call_command
from django.conf import settings

from main.celery import app as celery_app


@celery_app.task(queue=settings.CELERY_LOW_QUEUE_NAME)
def check_messages_response_time_expired():
    """
    Execute the check_messages_response_time_expired command.
    :return:
    """
    call_command("check_messages_response_time_expired")
