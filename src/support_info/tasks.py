from django.conf import settings

from main.celery import app as celery_app
from support_info.models import SupportChunkedFile


@celery_app.task(queue=settings.CELERY_LOW_QUEUE_NAME)
def delete_support_chuncked_files():
    """
    Execute the delete_chuncked_files command.
    :return:
    """
    SupportChunkedFile.objects.old().delete()
