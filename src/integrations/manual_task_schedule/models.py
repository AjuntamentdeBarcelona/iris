from django.db import models
from django.conf import settings

from django.utils.translation import gettext_lazy as _


def get_periodic_tasks():
    return [{**t, "schedule": s, "crontab": t['schedule']}
            for s, t in getattr(settings, "TASKS_SCHEDULE", {}).items() if t.get("show_log", True)]


def get_tasks():
    return [t["task"] for t in get_periodic_tasks()]


def get_user_manageable_tasks():
    return [t["task"] for t in get_periodic_tasks() if t.get('user_retry', False)]


def task_allows_user_retry(task):
    return getattr(settings, "TASKS_SCHEDULE", {}).get(task, {}).get('user_retry', False)


class ManualScheduleLog(models.Model):
    """
    Admin user have the ability to reschedule batch processes. It's necessary to keep track of the different tasks for
      different reasons:
      - The users need to know if there exist a manual scheduled event.
      - The users need to cancel a manual requested execution if necessary.
      - Since executing them outside the recommended time window could impact application performance.

    With that in mind, this model tracks audit and execution information.
    """
    CANCELLED = "c"
    SCHEDULED = "s"
    ERROR = "e"
    READY = "r"
    SCHEDULE_STATUS = (
        (SCHEDULED, _('Scheduled')),
        (CANCELLED, _('Cancelled')),
        (ERROR, _('Error enqueuing, please reschedule')),
        (READY, _('Ready')),
    )

    json = models.TextField(default='')
    task = models.CharField(max_length=200, db_index=True)
    created_by = models.CharField(max_length=20)
    cancelled_by = models.CharField(max_length=20, blank=True, default="")
    status = models.CharField(max_length=1, choices=SCHEDULE_STATUS, default=SCHEDULED, db_index=True)
    scheduled_date = models.DateTimeField(db_index=True)

    def cancel(self, user):
        self.cancelled_by = user
        self.status = self.CANCELLED
        self.save()

    @property
    def can_be_deleted(self):
        return self.status == self.SCHEDULED

    class Meta:
        ordering = ('-scheduled_date', )
