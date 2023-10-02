from rest_framework.pagination import PageNumberPagination
from iris_masters.models import Parameter


class ElementFavouritePagination(PageNumberPagination):

    def get_page_size(self, request):
        return int(Parameter.get_parameter_by_key("ELEMENT_FAVORITS", 10))
