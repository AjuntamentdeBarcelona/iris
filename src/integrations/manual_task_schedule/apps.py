from django.apps import AppConfig


class ManualTaskScheduleConfig(AppConfig):
    name = 'integrations.manual_task_schedule'

    def ready(self):
        self.register_tasks()

    @staticmethod
    def register_tasks():
        from . import tasks
        return tasks
