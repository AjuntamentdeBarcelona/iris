import django_filters as filters
from ariadna.models import Ariadna


class AriadnaFilter(filters.FilterSet):

    class Meta:
        model = Ariadna
        fields = {
            "used": ["exact"],
            "presentation_date": ["gt", "gte", "lt", "lte"]
        }
