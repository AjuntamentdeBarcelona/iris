import django_filters as filters
from django.utils import timezone

from integrations.manual_task_schedule.models import ManualScheduleLog


class ManualTaskFilter(filters.FilterSet):
    next = filters.BooleanFilter(method='next_filter')

    class Meta:
        model = ManualScheduleLog
        fields = ['task', 'status', 'next']

    def next_filter(self, queryset, *args, **kwargs):
        return queryset.filter(scheduled_date__gte=timezone.now())
