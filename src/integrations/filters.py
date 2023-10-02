from django_celery_results.models import TaskResult
from django_filters import FilterSet, DateFilter, BooleanFilter, NumberFilter
from django.utils.translation import gettext_lazy as _

from integrations.models import BatchFile


class TaskResultFilter(FilterSet):
    date_done__gte = DateFilter(label=_("Done at gte"), field_name="date_done", lookup_expr="gte")
    date_done__lte = DateFilter(label=_("Done at lte"), field_name="date_done", lookup_expr="lte")

    class Meta:
        model = TaskResult
        fields = ("date_done__gte", "date_done__lte", "task_name")


class BatchFileFilter(FilterSet):
    created_at__gte = DateFilter(label=_("Done at gte"), field_name="created_at", lookup_expr="gte")
    created_at__lte = DateFilter(label=_("Done at lte"), field_name="created_at", lookup_expr="lte")
    month = NumberFilter(label=_("Data start month"), field_name="oldest_date_limit__month", lookup_expr="exact")
    pending_validate = BooleanFilter(label=_("Validated"), field_name="validated_at", lookup_expr="isnull")

    class Meta:
        model = BatchFile
        fields = ("created_at__gte", "created_at__lte", "pending_validate", "trimestre", "year")

    def filter_queryset(self, queryset):
        if self.form.data.get("pending_validate") == "true":
            queryset = queryset.filter(validated_at__isnull=True)
        return super().filter_queryset(queryset)

    def valid_trimestre_value(self, year, month):
        if not year or not month:
            return False
        try:
            int(year)
            int(month)
        except ValueError:
            return False
        return True
