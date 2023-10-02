from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate
from integrations.signals import register_signals


class IntegrationsConfig(AppConfig):
    name = 'integrations'

    def ready(self):
        self.register_tasks()
        register_signals()
        if settings.EXECUTE_DATA_CHEKS:
            from integrations.data_checks.integrations_parameters import check_integrations_parameters
            post_migrate.connect(check_integrations_parameters, sender=self)

    @staticmethod
    def register_tasks():
        from . import tasks
        return tasks
