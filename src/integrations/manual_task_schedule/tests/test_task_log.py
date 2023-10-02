from unittest.mock import patch, Mock

from celery.schedules import crontab

from integrations.manual_task_schedule.models import get_tasks, task_allows_user_retry


class TestTaskConfig:
    """
    Tests utility functions for getting the tasks configured as visible by user (API logs or retries)
    """
    def when_tasks_are_retrieved(self):
        self.result = get_tasks()

    def when_checking_is_allows_user_retry(self, task):
        return task_allows_user_retry(task)

    def tasks_defined_as(self, tasks):
        self.tasks = tasks
        for task in self.tasks.values():
            task["schedule"] = crontab(minute="*/1")
        return patch('integrations.serializers.settings', Mock(CELERY_BEAT_SCHEDULE=self.tasks))

    def should_return_tasks(self, tasks):
        for task in tasks:
            assert task in self.result
