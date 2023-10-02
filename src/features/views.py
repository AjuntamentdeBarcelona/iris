from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.filters import OrderingFilter
from django.utils.decorators import method_decorator
from rest_framework.generics import ListAPIView
from rest_framework.viewsets import ModelViewSet

from excel_export.mixins import ExcelExportListMixin
from features.models import ValuesType, Feature, Mask
from features.serializers import ValuesTypeSerializer, FeatureSerializer, MaskSerializer, ValuesTypeShortSerializer, \
    FeatureShortSerializer
from iris_masters.views import BasicMasterSearchMixin, BasicMasterAdminPermissionsMixin, BasicMasterViewSet
from main.api.filters import UnaccentSearchFilter
from main.api.pagination import FeaturePagination
from main.utils import get_translated_fields
from main.api.schemas import list_swagger_auto_schema_factory, retrieve_swagger_auto_schema_factory
from main.views import MultipleSerializersMixin


@method_decorator(name="list", decorator=list_swagger_auto_schema_factory(ValuesTypeShortSerializer))
@method_decorator(name="retrieve", decorator=retrieve_swagger_auto_schema_factory(ValuesTypeSerializer))
class ValuesTypeViewSet(ExcelExportListMixin, BasicMasterSearchMixin, MultipleSerializersMixin,
                        BasicMasterAdminPermissionsMixin, ModelViewSet):
    """
    Viewset to manage Values Type (CRUD).
    Administration permission  needed to create, update and destroy.
    The list endpoint:
     - can be exported to excel
     - can be ordered by the different language descriptions
     - support unaccent search by the different language descriptions

    The list of values is managed with ValuesType. It has to be sent as a list of dicts.

    The ValuesType descriptions must be unique
    """
    queryset = ValuesType.objects.all()
    serializer_class = ValuesTypeSerializer
    short_serializer_class = ValuesTypeShortSerializer
    filename = "values-types.xlsx"
    ordering_fields = get_translated_fields("description")
    # Set main lang as ordering
    ordering = ordering_fields[0],
    nested_excel_fields = {
        ExcelExportListMixin.NESTED_BASE_KEY: [ordering_fields[0]],
    }
    filter_backends = (UnaccentSearchFilter, DjangoFilterBackend, OrderingFilter)


@method_decorator(name="list", decorator=list_swagger_auto_schema_factory(FeatureSerializer))
class FeatureViewSet(ExcelExportListMixin, BasicMasterSearchMixin, BasicMasterAdminPermissionsMixin,
                     BasicMasterViewSet):
    """
    Viewset to manage Features (CRUD).
    Administration permission needed to create, update and destroy.
    The list endpoint:
     - can be exported to excel
     - can be ordered by the different language descriptions, values type description, mask_description or is_special
     - support unaccent search by the different language descriptions

    Validation issues:
     - features descriptions must be unique
     - a mask or a value type must be set
     - mask and values type can not be set at the same time
    """

    queryset = Feature.objects.all().select_related("values_type", "mask")
    serializer_class = FeatureSerializer
    short_serializer_class = FeatureShortSerializer
    pagination_class = FeaturePagination
    filename = "features.xlsx"
    nested_excel_fields = {
        ExcelExportListMixin.NESTED_BASE_KEY:
            get_translated_fields("description") + ["values_type", "mask", "is_special"],
        "values_type": {
            ExcelExportListMixin.NESTED_BASE_KEY: ["description"]
        },
        "mask": {
            ExcelExportListMixin.NESTED_BASE_KEY: ["description"]
        }
    }
    filter_backends = (UnaccentSearchFilter, DjangoFilterBackend, OrderingFilter)
    ordering_fields = get_translated_fields("description") + ["values_type__description", "mask__description",
                                                              "is_special"]


class MaskListView(BasicMasterSearchMixin, ListAPIView):
    """
    List of masks that can be used on Features
    """
    queryset = Mask.objects.all()
    serializer_class = MaskSerializer
