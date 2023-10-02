from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django_filters import rest_framework as filters

from iris_masters.models import Application, RecordType
from themes.actions.theme_keywords_search import KeywordSearch
from themes.models import Area, Element, ElementDetail


class KeywordsFilterMixin:
    queryset_filter_kwarg = None

    def get_queryset_filter_kwarg(self):
        if not self.queryset_filter_kwarg:
            raise Exception("Set queryset_filter_kwarg")
        return self.queryset_filter_kwarg

    def filter_keywords(self, queryset, name, value):
        details_ids, _ = KeywordSearch(value.split(",")[:10]).details_search()
        queryset_kwargs = {self.get_queryset_filter_kwarg(): details_ids}
        queryset = queryset.filter(**queryset_kwargs)
        return queryset


class ElementFilter(KeywordsFilterMixin, filters.FilterSet):
    area = filters.ModelMultipleChoiceFilter(field_name="area_id", distinct=False,
                                             queryset=Area.objects.filter(**Area.ENABLED_AREA_FILTERS))

    class Meta:
        model = Element
        fields = ("area",)


class ElementDetailFilter(KeywordsFilterMixin, filters.FilterSet):
    area = filters.ModelMultipleChoiceFilter(field_name="element__area_id", distinct=False,
                                             queryset=Area.objects.filter(**Area.ENABLED_AREA_FILTERS))
    element = filters.ModelMultipleChoiceFilter(field_name="element_id", distinct=False,
                                                queryset=Element.objects.filter(**Element.ENABLED_ELEMENT_FILTERS))
    applications = filters.ModelMultipleChoiceFilter(field_name="applications", distinct=False,
                                                     queryset=Application.objects.all())
    record_types = filters.ModelMultipleChoiceFilter(field_name="record_type", distinct=False,
                                                     queryset=RecordType.objects.all())

    keywords = filters.Filter(field_name="keywords", label="Keywords", method="filter_keywords")
    active = filters.BooleanFilter(label="Active", field_name="active", method="filter_active")
    # date filters
    activation_date_ini = filters.DateFilter(label=_("Created at init"), field_name="activation_date",
                                             lookup_expr="gte")
    activation_date_end = filters.DateFilter(label=_("Created at end"), method="filter_activation_date_end")

    queryset_filter_kwarg = "pk__in"

    class Meta:
        model = ElementDetail
        fields = ("keywords", "element_id", "id", "area", "element")

    def filter_active(self, queryset, name, value):
        date_filters = Q(activation_date__lte=timezone.now().date()) | Q(activation_date__isnull=True)
        return queryset.filter(date_filters, active=True) if value else queryset.exclude(date_filters, active=True)

    def filter_activation_date_end(self, queryset, name, value):
        # As the value is a Date and its is compared with a datetime, the lookup __lte is not usefull.
        # For that reason, we use lt and add a day to the comparision value
        date_limit = value + timedelta(days=1)
        return queryset.filter(activation_date__lt=date_limit)
