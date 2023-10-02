from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate


class IrisTemplatesConfig(AppConfig):
    name = 'iris_templates'

    def ready(self):
        from .permissions import register_permissions
        register_permissions()
        if settings.EXECUTE_DATA_CHEKS:
            from iris_templates.data_checks.visible_parameters import check_template_parameters
            post_migrate.connect(check_template_parameters, sender=self)
