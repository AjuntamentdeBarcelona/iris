from rest_framework.pagination import PageNumberPagination


class IrisPagination(PageNumberPagination):
    max_page_size = 30
    page_size_query_param = 'page_size'


class MessagesPagination(PageNumberPagination):
    page_size_query_param = 'page_size'
    page_size = 20


class IrisMaxPagination(IrisPagination):
    page_size = 200
    max_page_size = 200


class IrisOnlyMaxPagination(IrisPagination):
    max_page_size = 200


class RecordCardPagination(IrisPagination):
    page_size = 30


class FeaturePagination(RecordCardPagination):
    pass
