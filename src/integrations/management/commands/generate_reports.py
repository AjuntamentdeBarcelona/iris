from django.core.management.base import BaseCommand

from integrations.tasks import generate_open_data_report


class Command(BaseCommand):
    """
    Command to clean delete Chuncked Files with more than one hour of live
    """

    help = "Delete Chuncked Files with more than one hour of live"

    def handle(self, *args, **options):
        self.stdout.write('REPORT | OPENDATA REPORTS | Starting')
        generate_open_data_report()
        self.stdout.write('REPORT | OPENDATA REPORTS | End')
