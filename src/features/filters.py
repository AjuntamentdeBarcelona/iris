from django_filters import rest_framework as filters, Filter

from features.models import Values


class ValuesFilter(filters.FilterSet):

    values_type = Filter(field_name="values_type", label="Values Type", method="filter_values_type")

    class Meta:
        model = Values
        fields = ("values_type", )

    def filter_values_type(self, queryset, name, value):
        return queryset.filter(values_type__pk=value)
