import pytest
from django.utils import timezone

from integrations.manual_task_schedule.models import ManualScheduleLog


@pytest.mark.django_db
class TestManualScheduleLog:
    TEST_USERNAME = 'TEST'
    TEST_CREATED_BY = 'TEST_CREATE'

    def test_cancel(self):
        sc = self.given_an_schedule()
        sc.cancel(self.TEST_USERNAME)
        assert sc.status == ManualScheduleLog.CANCELLED
        assert sc.cancelled_by == self.TEST_USERNAME
        assert sc.created_by == self.TEST_CREATED_BY

    @pytest.mark.parametrize('status,can_be_deleted', (
        (ManualScheduleLog.SCHEDULED, True),
        (ManualScheduleLog.CANCELLED, False),
        (ManualScheduleLog.ERROR, False),
        (ManualScheduleLog.READY, False),
    ))
    def test_can_be_deleted(self, status, can_be_deleted):
        assert ManualScheduleLog(status=status).can_be_deleted == can_be_deleted

    def given_an_schedule(self):
        return ManualScheduleLog.objects.create(
            task='TEST',
            created_by='TEST_CREATE',
            scheduled_date=timezone.now(),
        )
