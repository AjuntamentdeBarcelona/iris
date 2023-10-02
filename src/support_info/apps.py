from django.apps import AppConfig


class SupportInfoConfig(AppConfig):
    name = "support_info"

    def ready(self):
        self.register_tasks()

    @staticmethod
    def register_tasks():
        from .permissions import register_permissions
        register_permissions()

        from . import tasks
        return tasks
