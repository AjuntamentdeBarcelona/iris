from django.contrib import admin

# Register your models here.
from integrations.manual_task_schedule.models import ManualScheduleLog

admin.site.register(ManualScheduleLog)
