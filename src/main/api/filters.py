from django_filters import LookupChoiceFilter
from rest_framework.filters import SearchFilter


class UnaccentSearchFilter(SearchFilter):
    lookup_prefixes = {
        '^': 'istartswith',
        '=': 'iexact',
        '@': 'search',
        '$': 'iregex',
        '#': 'unaccent__icontains'
    }


class UnaccentLookupChoiceFilter(LookupChoiceFilter):

    def filter(self, qs, lookup):
        if not lookup:
            return super(LookupChoiceFilter, self).filter(qs, None)

        self.lookup_expr = "unaccent__{}".format(lookup.lookup_expr)
        return super(LookupChoiceFilter, self).filter(qs, lookup.value)
