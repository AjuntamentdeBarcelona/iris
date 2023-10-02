from django.apps import AppConfig


class CommunicationsConfig(AppConfig):
    name = "communications"

    def ready(self):
        self.register_tasks()

    @staticmethod
    def register_tasks():
        from . import tasks
        return tasks
