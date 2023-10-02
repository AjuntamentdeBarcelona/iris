from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate


class ThemesConfig(AppConfig):
    name = "themes"

    def ready(self):
        self.register_tasks()
        if settings.EXECUTE_DATA_CHEKS:
            from themes.data_checks.zones import check_zones
            from themes.data_checks.survey import check_survey
            post_migrate.connect(check_zones, sender=self)
            post_migrate.connect(check_survey, sender=self)

    @staticmethod
    def register_tasks():
        from . import tasks
        return tasks
