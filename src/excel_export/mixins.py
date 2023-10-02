from collections import OrderedDict

from drf_renderer_xlsx.mixins import XLSXFileMixin
from rest_framework.mixins import ListModelMixin
from rest_framework.renderers import JSONRenderer, BrowsableAPIRenderer
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.status import HTTP_403_FORBIDDEN

from iris_masters.models import Parameter
from excel_export.renderers import CustomXLSXRenderer
from excel_export.styles import ExcelBaseStyles
from iris_masters.permissions import MASTERS_EXCEL, ADMIN
from main.utils import get_translated_fields
from profiles.permissions import IrisPermissionChecker


class ColumnNamesMixin:

    def get_column_header(self):
        header = super().get_column_header()
        if hasattr(self, 'serializer'):
            # list serializers has the individual one in child attr
            ser = getattr(self.serializer, 'child', self.serializer)
            titles = [
                str(getattr(field, 'label', name))
                for name, field in ser.fields.items()
            ]
            header['titles'] = titles
        return header


class ExcelExportListMixin(ColumnNamesMixin, XLSXFileMixin, ExcelBaseStyles, ListModelMixin):
    EXCEL_MIME_TYPE = "application/xlsx"
    renderer_classes = [JSONRenderer, BrowsableAPIRenderer, CustomXLSXRenderer]
    filename = "list-export.xlsx"
    NESTED_BASE_KEY = "__fields__"
    nested_excel_fields = {
        NESTED_BASE_KEY: [],
    }
    export_serializer = None

    @property
    def is_export(self):
        return self.request.META.get("HTTP_ACCEPT") == self.EXCEL_MIME_TYPE

    def list(self, request, *args, **kwargs):
        if not self.is_export:
            return super().list(request, *args, **kwargs)
        perms = IrisPermissionChecker.get_for_user(request.user)
        if not perms.has_permission(MASTERS_EXCEL) and not perms.has_permission(ADMIN):
            return Response([], status=HTTP_403_FORBIDDEN)

        reg_limit = int(Parameter.get_parameter_by_key("NUM_REGISTRES_REPORTS", 5000))
        queryset = self.filter_queryset(self.get_queryset())[:reg_limit]
        serializer = self.get_serializer(queryset, many=True)

        data_response = []

        for obj in serializer.data:
            data_response.append(OrderedDict((field, obj.get(field))
                                             for field in self.nested_excel_fields[self.NESTED_BASE_KEY]))

        return Response(data_response)

    def get_serializer(self, *args, **kwargs):
        serializer_instance = super().get_serializer(*args, **kwargs)
        if self.is_export and not self.export_serializer:
            # On list action serializer instance is a ListSerializer
            self.review_excel_fields(serializer_instance.child)
        self.serializer = serializer_instance
        return serializer_instance

    def get_serializer_class(self):
        if self.is_export and self.export_serializer:
            return self.export_serializer
        return super().get_serializer_class()

    def review_excel_fields(self, serializer):
        self._review_excel_field(serializer, self.nested_excel_fields)

    def _review_excel_field(self, serializer, included_map):
        excluded = []
        for field_name, field in serializer.fields.items():
            if isinstance(field, Serializer):
                if field_name in included_map:
                    self._review_excel_field(field, included_map[field_name])
                else:
                    excluded.append(field_name)
            elif field_name not in included_map.get(self.NESTED_BASE_KEY, []):
                excluded.append(field_name)
        for field_name in excluded:
            serializer.fields.pop(field_name, None)


class ExcelDescriptionExportMixin(ExcelExportListMixin):
    nested_excel_fields = {
        ExcelExportListMixin.NESTED_BASE_KEY: ["description"],
    }


class ExcelTranslatableDescriptionExportMixin(ExcelExportListMixin):
    nested_excel_fields = {
        ExcelExportListMixin.NESTED_BASE_KEY: get_translated_fields("description"),
    }
