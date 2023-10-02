from django.apps import AppConfig


class ReportsConfig(AppConfig):
    name = "reports"

    def ready(self):
        from reports.permissions import register_permissions
        register_permissions()
