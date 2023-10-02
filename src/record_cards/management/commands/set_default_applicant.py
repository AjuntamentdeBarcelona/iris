from django.core.management.base import BaseCommand, CommandError

from record_cards.data_checks.default_applicant import create_default_applicant


class Command(BaseCommand):
    """
    Command to set the value of the default applicant
    taken from the parameter AGRUPACIO_PER_DEFECTE
    """

    help = "Set the value of the default applicant taken from the parameter AGRUPACIO_PER_DEFECTE"

    def handle(self, *args, **options):
        create_default_applicant(sender=None)
