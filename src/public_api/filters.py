from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from django_filters import rest_framework as filters

from iris_masters.models import RecordState, RecordType
from record_cards.models import RecordCard
from themes.filters import KeywordsFilterMixin
from themes.models import Element, Area, ElementDetail


class ElementDetailPublicFilter(KeywordsFilterMixin, filters.FilterSet):
    queryset_filter_kwarg = "pk__in"

    element_id = filters.ModelChoiceFilter(field_name="element_id", queryset=Element.objects.filter(
        deleted__isnull=True, area__deleted__isnull=True))
    area_id = filters.ModelChoiceFilter(field_name="element__area_id",
                                        queryset=Area.objects.filter(deleted__isnull=True))
    keywords = filters.Filter(label="Keywords", method="filter_keywords")

    class Meta:
        model = ElementDetail
        fields = ("element_id", "area_id", "keywords")


class RecordCardPublicFilter(KeywordsFilterMixin, filters.FilterSet):

    queryset_filter_kwarg = "element_detail__pk__in"

    area_id = filters.ModelChoiceFilter(field_name="element_detail__element__area_id",
                                        queryset=Area.objects.filter(deleted__isnull=True))
    element_id = filters.ModelMultipleChoiceFilter(field_name="element_detail__element_id", distinct=False,
                                                   queryset=Element.objects.filter(**Element.ENABLED_ELEMENT_FILTERS))
    record_type_id = filters.ModelChoiceFilter(field_name="record_type_id", queryset=RecordType.objects.all())

    start_date_ini = filters.DateFilter(label=_("Start date init"), field_name="start_date_process", lookup_expr="gte")
    start_date_end = filters.DateFilter(label=_("Start date end"), field_name="start_date_process", lookup_expr="lte")
    keywords = filters.Filter(label="Keywords", method="filter_keywords")
    closed_records = filters.BooleanFilter(method="filter_closed_records")

    # ubication filter
    show_ubication = filters.BooleanFilter(label=_("Records with no ubication"), method="filter_show_ubication")
    via_type = filters.Filter(label=_("Via Type"), method="filter_via_type")
    neighborhood = filters.Filter(label=_("Neighborhood"), method="filter_neighborhood")
    neighborhood_id = filters.Filter(label=_("Neighborhood"), method="filter_neighborhood_id")
    district_id = filters.Filter(label=_("District"), method="filter_district")
    street = filters.Filter(label=_("Street"), method="filter_address")
    number = filters.Filter(label=_("Number"), method="filter_address")

    class Meta:
        model = RecordCard
        fields = ("id", "area_id", "element_id", "start_date_ini", "start_date_end", "keywords", "closed_records",
                  "show_ubication")

    def filter_closed_records(self, queryset, name, value):
        return queryset.filter(record_state_id=RecordState.CLOSED) if value else queryset

    def filter_allows_ssi_location(self, queryset):
        return queryset.filter(element_detail__allows_ssi_location=True, ubication__isnull=False)

    def filter_via_type(self, queryset, name, value):
        queryset = self.filter_allows_ssi_location(queryset)
        return queryset.filter(element_detail__allows_ssi_location=True, ubication__via_type__icontains=value)

    def filter_neighborhood(self, queryset, name, value):
        queryset = self.filter_allows_ssi_location(queryset)
        return queryset.filter(ubication__neighborhood__unaccent__icontains=value)

    def filter_neighborhood_id(self, queryset, name, value):
        queryset = self.filter_allows_ssi_location(queryset)
        return queryset.filter(ubication__neighborhood_id=value)

    def filter_district(self, queryset, name, value):
        queryset = self.filter_allows_ssi_location(queryset)
        return queryset.filter(ubication__district_id=value)

    def filter_address(self, queryset, name, value):
        queryset = self.filter_allows_ssi_location(queryset)
        return queryset.filter(Q(ubication__street__unaccent__icontains=value) |
                               Q(ubication__street2__unaccent__icontains=value),
                               element_detail__allows_ssi_location=True)

    def filter_show_ubication(self, queryset, name, value):
        if value:
            return queryset.filter(element_detail__allows_ssi_location=True, ubication__isnull=False)
        return queryset.filter(Q(element_detail__allows_ssi_location=False) | Q(ubication__isnull=True))


class MarioPublicFilter(filters.FilterSet):

    tematica = filters.Filter()
