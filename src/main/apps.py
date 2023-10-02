from django.apps import AppConfig


class MainConfig(AppConfig):
    name = 'main'

    def ready(self):
        self.register_tasks()

    @staticmethod
    def register_tasks():
        from . import tasks
        return tasks
