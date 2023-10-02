from django.core.management.base import BaseCommand

from record_cards.models import RecordChunkedFile


class Command(BaseCommand):
    """
    Command to clean delete Chuncked Files with more than one hour of live
    """

    help = "Delete Chuncked Files with more than one hour of live"

    def handle(self, *args, **options):
        self.stdout.write('Start checking chuncked files')
        old_files = RecordChunkedFile.objects.old()
        for file in old_files:
            file_pk = file.pk
            file.delete()
            self.stdout.write("Record Chunked File {} deleted".format(file_pk))
        self.stdout.write('End checking chuncked files')
