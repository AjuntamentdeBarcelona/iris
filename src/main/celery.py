import os

from celery import Celery
from configurations import importer
from django.conf import settings


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main.settings')
os.environ.setdefault('DJANGO_CONFIGURATION', 'Base')

importer.install()

app = Celery('irisbackoffice')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
