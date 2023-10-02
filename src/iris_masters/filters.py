from django.utils.translation import ugettext_lazy as _

from django_filters.rest_framework import FilterSet, BooleanFilter, DateFilter
from iris_masters.models import Announcement


class InputChannelFilter(FilterSet):
    visible = BooleanFilter(field_name="visible")


class AnnouncementFilter(FilterSet):
    created_at__gte = DateFilter(label=_("Created at gte"), field_name='created_at', lookup_expr='gte')
    created_at__lte = DateFilter(label=_("Created at lte"), field_name='created_at', lookup_expr='lte')
    expiration_date__gte = DateFilter(label=_("Experiation date gte"), field_name='expiration_date', lookup_expr='gte')
    expiration_date__lte = DateFilter(label=_("Experiation date lte"), field_name='expiration_date', lookup_expr='lte')

    class Meta:
        model = Announcement
        fields = ('created_at__gte', 'created_at__lte', 'expiration_date__gte', 'expiration_date__lte')
