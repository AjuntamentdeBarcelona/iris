import pytest
from django.contrib.auth.models import User
from django.test import RequestFactory
from django.utils.functional import cached_property

from rest_framework import serializers
from rest_framework.generics import ListAPIView

from excel_export.mixins import ExcelExportListMixin
from excel_export.renderers import CustomXLSXRenderer
from record_cards.tests.utils import SetUserGroupMixin


class DummySerializer(serializers.Serializer):
    field = serializers.CharField()
    second_field = serializers.CharField()
    third_field = serializers.CharField()


class DummyAPIView(ExcelExportListMixin, ListAPIView):
    serializer_class = DummySerializer
    nested_excel_fields = {
        ExcelExportListMixin.NESTED_BASE_KEY: ["field", "second_field"],
    }
    queryset = []


@pytest.mark.django_db
class TestExcelExportListMixin(SetUserGroupMixin):

    @cached_property
    def user(self):
        return User.objects.create(username="excel")

    def test_excel_export_list_mixin(self):
        request = RequestFactory().get("/")
        request.META["HTTP_ACCEPT"] = "application/xlsx"
        self.set_usergroup()
        request.user = self.user
        response = DummyAPIView.as_view()(request)
        assert type(response.accepted_renderer) == CustomXLSXRenderer
