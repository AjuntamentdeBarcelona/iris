from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from excel_export.mixins import ExcelExportListMixin
from iris_masters.views import BasicMasterAdminPermissionsMixin, BasicMasterSearchMixin
from main.api.filters import UnaccentSearchFilter
from protocols.models import Protocols
from protocols.serializers import ProtocolsSerializer
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated

from main.api.schemas import (destroy_swagger_auto_schema_factory, create_swagger_auto_schema_factory,
                              update_swagger_auto_schema_factory, list_swagger_auto_schema_factory)


@method_decorator(name="create", decorator=create_swagger_auto_schema_factory(ProtocolsSerializer))
@method_decorator(name="update", decorator=update_swagger_auto_schema_factory(ProtocolsSerializer))
@method_decorator(name="partial_update", decorator=update_swagger_auto_schema_factory(ProtocolsSerializer))
@method_decorator(name="destroy", decorator=destroy_swagger_auto_schema_factory())
@method_decorator(name="list", decorator=list_swagger_auto_schema_factory(ProtocolsSerializer))
class ProtocolsViewSet(ExcelExportListMixin, BasicMasterAdminPermissionsMixin, BasicMasterSearchMixin, ModelViewSet):
    """
    Viewset to manage Protocols (CRUD) with 'protocol_id' as look_up field.
    Administration permission  needed to create, update and destroy.
    The list endpoint:
     - is not paginated
     - can be exported to excel
     - can be ordered by the protocol_id and short_descriptions
     - support unaccent search by the protocol_id, short_description and description
     - can be filtered by protocol_id__contains
    """

    serializer_class = ProtocolsSerializer
    queryset = Protocols.objects.order_by("protocol_id")
    permission_classes = (IsAuthenticated, )
    lookup_field = "protocol_id"
    pagination_class = None
    filename = "protocols.xlsx"
    nested_excel_fields = {
        ExcelExportListMixin.NESTED_BASE_KEY: ["protocol_id", "short_description"]
    }
    search_fields = ["#description", "#protocol_id", "#short_description"]
    filter_backends = (UnaccentSearchFilter, DjangoFilterBackend, OrderingFilter)
    ordering_fields = ["protocol_id", "short_description"]

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset()
        protocol_id = self.request.GET.get("protocol_id")
        if protocol_id:
            queryset = queryset.filter(protocol_id__contains=protocol_id)

        return queryset


@method_decorator(name="create", decorator=create_swagger_auto_schema_factory(ProtocolsSerializer))
@method_decorator(name="update", decorator=update_swagger_auto_schema_factory(ProtocolsSerializer))
@method_decorator(name="partial_update", decorator=update_swagger_auto_schema_factory(ProtocolsSerializer))
@method_decorator(name="destroy", decorator=destroy_swagger_auto_schema_factory())
@method_decorator(name="list", decorator=list_swagger_auto_schema_factory(ProtocolsSerializer))
class ProtocolsIdViewSet(ProtocolsViewSet):
    """
    Viewset to manage Protocols (CRUD) with 'id' as look_up field.
    Administration permission  needed to create, update and destroy.
    The list endpoint:
     - is not paginated
     - can be exported to excel
     - can be ordered by the protocol_id and short_descriptions
     - support unaccent search by the protocol_id, short_description and description
     - can be filtered by protocol_id__contains
    """
    lookup_field = "id"
