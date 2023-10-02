from django_filters import rest_framework as filters

from support_info.models import SupportInfo


class SupportInfoFilter(filters.FilterSet):
    type = filters.ChoiceFilter(choices=SupportInfo.TYPES, field_name="type")
    title = filters.CharFilter(field_name="title", lookup_expr="unaccent__istartswith")
    category = filters.ChoiceFilter(choices=SupportInfo.CATEGORIES, field_name="category")

    class Meta:
        model = SupportInfo
        fields = ("type", "title", "category")
