from datetime import timedelta

import pytest
from django.utils import timezone
from mock import patch, Mock

from integrations.manual_task_schedule.models import ManualScheduleLog
from integrations.manual_task_schedule.tasks import execute_task_from_schedule, launch_manual_scheduled_task, \
    calc_countdown_for_task
from integrations.manual_task_schedule.tests.dummy_task import dummy_task_with_kwargs


class TestScheduleTasks:
    task_path = 'integrations.manual_task_schedule.tests.dummy_task.dummy_task_with_kwargs'

    def test_execute_task(self):
        with patch(self.task_path, Mock(delay=dummy_task_with_kwargs)):
            sc = ManualScheduleLog(
                scheduled_date=timezone.now(),
                task=self.task_path,
                json='{"test_kwarg": true}'
            )
            # OK if not raises exception
            execute_task_from_schedule(self.task_path, sc)

    @pytest.mark.django_db
    def test_execute_and_ready(self):
        sc = ManualScheduleLog.objects.create(
            scheduled_date=timezone.now(),
            task=self.task_path,
            json='{"test_kwarg": true}'
        )
        with patch(self.task_path, Mock(delay=dummy_task_with_kwargs)):
            new_sc = launch_manual_scheduled_task(task_import_path=self.task_path, schedule_info_pk=sc.pk)
            assert new_sc == ManualScheduleLog.READY

    def test_calc_countdown(self):
        now = timezone.now()
        delay_seconds = 339
        sc = ManualScheduleLog(scheduled_date=now + timedelta(seconds=delay_seconds))
        with patch('integrations.manual_task_schedule.tasks.timezone.now', Mock(return_value=now)):
            assert calc_countdown_for_task(sc) == delay_seconds

    def test_past_countdown(self):
        sc = ManualScheduleLog(scheduled_date=timezone.now())
        assert calc_countdown_for_task(sc) == 0
