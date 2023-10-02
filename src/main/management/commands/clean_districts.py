from django.core.management.base import BaseCommand

from iris_masters.models import District
from record_cards.models import Citizen, SocialEntity, Ubication


class Command(BaseCommand):
    """
    Command to clean districts values to prepare the migration to the FK
    """

    help = "Clean district values"

    def add_arguments(self, parser):

        parser.add_argument('--model', action='store', dest='model_name',
                            help='Model to clean district field.')

    def handle(self, *args, **options):
        self.stdout.write('Start cleaning district field')

        # Get the database we're operating from
        model_name = options.get('model_name')
        models = {
            'Citizen': Citizen,
            'SocialEntity': SocialEntity,
            'Ubication': Ubication
        }
        model = models[model_name]
        for record in model.objects.all():
            self.stdout.write('{}: {}'.format(model_name, record.pk))
            self.stdout.write('Old district value: {}'.format(record.district))
            self.clean_record_districts(record)
            self.stdout.write('New district value: {}'.format(record.district))
            self.stdout.write('\n')

    def clean_record_districts(self, record):
        if record.district:
            try:
                record.district = int(record.district)
            except Exception:
                if "." in record.district:
                    record.district = int(record.district.split(".")[0])
                elif "Fora de Barcelona" == record.district or " " == record.district:
                    record.district = str(District.FORA_BCN)
                else:
                    raise Exception("New district value: {}".format(record.district))
        else:
            record.district = str(District.FORA_BCN)
        record.save()
