from model_mommy import mommy

from iris_masters.permissions import ADMIN
from profiles.models import Profile, Permission, ProfilePermissions, GroupProfiles, UserGroup, Group, GroupsUserGroup
from record_cards.tests.utils import SetGroupRequestMixin
from communications.tests.utils import load_missing_data
from iris_masters.tests.utils import load_missing_data_process, load_missing_data_districts


class FieldsTestSerializerMixin(SetGroupRequestMixin):
    serializer_class = None
    data_keys = []

    def get_serializer_class(self):
        if not self.serializer_class:
            raise Exception("Set the serializer class!")
        return self.serializer_class

    def get_instance(self):
        raise NotImplementedError("Implement this method")

    def get_keys_number(self):
        if not self.data_keys:
            raise Exception("Set the keys expected on the serializer data")
        return len(self.data_keys)

    def get_data_keys(self):
        if not self.data_keys:
            raise Exception("Set the keys expected on the serializer data")
        return self.data_keys

    def get_instanced_serializer(self):
        _, request = self.set_group_request()
        return self.get_serializer_class()(instance=self.get_instance(), context={"request": request})

    def test_serializer(self):
        load_missing_data()
        load_missing_data_process()
        load_missing_data_districts()
        ser = self.get_instanced_serializer()
        assert len(ser.data.keys()) == self.get_keys_number()
        for data_key in self.data_keys:
            assert data_key in ser.data, f"Required {data_key} not present in serializer data"


class UpperFieldsTestSerializerMixin(FieldsTestSerializerMixin):

    def test_serializer(self):
        _, request = self.set_group_request()
        ser = self.get_serializer_class()(instance=self.get_instance(), context={"request": request})
        assert len(ser.data.keys()) == self.get_keys_number()
        for data_key in self.data_keys:
            assert data_key.upper() in ser.data, f"Required {data_key} not present in serializer data"


class AdminUserMixin:
    permission_codename = ADMIN

    def when_is_authenticated(self):
        """
        Authenticates the next request.
        """
        user = self.given_a_user()
        if not hasattr(user, "usergroup"):
            group = mommy.make(Group, user_id="222", profile_ctrl_user_id="22222")
            user_group = UserGroup.objects.create(user=user, group=group)
            GroupsUserGroup.objects.create(user_group=user_group, group=group)
            has_admin_permission = False
        else:
            group = user.usergroup.group
            GroupsUserGroup.objects.get_or_create(user_group=user.usergroup, group=group)
            has_admin_permission = self.chek_admin_permission(group)

        if not has_admin_permission:
            profile = mommy.make(Profile, user_id="222")
            admin_permission = Permission.objects.get(codename=self.permission_codename)
            ProfilePermissions.objects.create(permission=admin_permission, profile=profile)
            GroupProfiles.objects.create(group=group, profile=profile)

        self.client.force_authenticate(user=user)

    @staticmethod
    def chek_admin_permission(group):
        for group_profile in group.groupprofiles_set.filter(enabled=True):
            for profile_permission in group_profile.profile.profilepermissions_set.filter(enabled=True):
                if profile_permission.permission.codename == ADMIN:
                    return True
        return False
