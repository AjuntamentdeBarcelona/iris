from django.core.management.base import BaseCommand

from integrations.manual_task_schedule.tasks import remove_celery_results


class Command(BaseCommand):

    def handle(self, *args, **options):
        remove_celery_results()
