from django.core.management.base import BaseCommand

from integrations.services.mario.services import MarioService


class Command(BaseCommand):

    def handle(self, *args, **options):
        MarioService().search('Museu')
