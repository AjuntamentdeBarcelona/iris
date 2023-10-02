from django.apps import AppConfig
from django.db.models import CharField

from record_cards.lookups import ILike


class RecordCardsConfig(AppConfig):
    name = 'record_cards'

    def ready(self):
        from .permissions import register_permissions
        register_permissions()
        self.register_tasks()
        CharField.register_lookup(ILike)

    @staticmethod
    def register_tasks():
        from . import tasks
        return tasks
