import uuid

from model_mommy import mommy

from iris_masters.permissions import ADMIN
from main.open_api.tests.base import BaseOpenAPIResourceTest, BasePermissionsTest
from main.test.mixins import AdminUserMixin
from profiles.models import Group, UserGroup, GroupProfiles, ProfilePermissions, Profile, Permission, GroupsUserGroup
from protocols.models import Protocols
from record_cards.tests.utils import SetPermissionMixin, SetUserGroupMixin


class TestProtocol(AdminUserMixin, SetUserGroupMixin, SetPermissionMixin, BaseOpenAPIResourceTest):
    path = "/protocols/"
    base_api_path = "/services/iris/api"
    path_pk_param_name = "protocol_id"
    lookup_field = "protocol_id"
    paginate_by = 0

    def get_default_data(self):
        return {
            "description": uuid.uuid4(),
            "short_description": uuid.uuid4(),
            "protocol_id": str(uuid.uuid4())[:30],
        }

    def given_create_rq_data(self):
        return {
            "description": "test",
            "short_description": "test",
            "protocol_id": "10000000",
        }

    def when_data_is_invalid(self, data):
        data["description"] = ""


class TestProtocolsAdminPermissions(BasePermissionsTest):
    base_api_path = "/services/iris/api"
    path_pk_param_name = "protocol_id"

    cases = [
        {
            "detail_path": "/protocols/{protocol_id}/",
            "model_class": Protocols,
        }
    ]

    def given_an_object(self, model_class):
        return mommy.make(model_class, user_id="user_id")

    def set_admin_permission(self):
        if not hasattr(self.user, "usergroup"):
            group = mommy.make(Group, user_id="222", profile_ctrl_user_id="22222")
            user_group = UserGroup.objects.create(user=self.user, group=group)
            GroupsUserGroup.objects.create(user_group=user_group, group=group)
        else:
            group = self.user.usergroup.group
            GroupsUserGroup.objects.create(user_group=self.user.usergroup, group=group)
        profile = mommy.make(Profile, user_id="222")
        admin_permission = Permission.objects.get(codename=ADMIN)
        ProfilePermissions.objects.create(permission=admin_permission, profile=profile)
        GroupProfiles.objects.create(group=group, profile=profile)
