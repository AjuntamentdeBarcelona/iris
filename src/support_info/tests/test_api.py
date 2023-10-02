from main.open_api.tests.base import SoftDeleteCheckMixin, BaseOpenAPIResourceTest
from main.test.mixins import AdminUserMixin

from support_info.models import SupportInfo
from support_info.permissions import SUPPORT_ADMIN


class TestSupportInfo(SoftDeleteCheckMixin, AdminUserMixin, BaseOpenAPIResourceTest):
    path = "/supports-info/"
    base_api_path = "/services/iris/api"
    deleted_model_class = SupportInfo
    permission_codename = SUPPORT_ADMIN

    def given_create_rq_data(self):
        return {
            "title": "test",
            "description": "description",
            "type": SupportInfo.DOCUMENTATION,
            "category": None,
            "file": None,
            "link": ""

        }

    def when_data_is_invalid(self, data):
        data["file"] = "asdasdadsadsadsa"

    def get_default_data(self):
        return {
            "title": "test",
            "description": "description",
            "type": SupportInfo.DOCUMENTATION,
            "category": None,
            "file": None,
            "link": ""

        }
