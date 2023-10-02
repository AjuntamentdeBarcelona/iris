from datetime import date
import pytest
from django.test import override_settings
from mock import Mock, patch
from model_mommy import mommy

from django.contrib.auth.models import User

from iris_masters.models import InputChannel, LetterTemplate
from profiles.models import (Group, UserGroup, Permission, Profile, GroupReassignation, GroupsUserGroup,
                             ProfilePermissions, GroupProfiles)
from profiles.serializers import (GroupSerializer, GroupSetSerializer, UserGroupSerializer, GroupShortSerializer,
                                  GroupReassignationSerializer, PermissionSerializer, ProfilePermissionsSerializer,
                                  ProfileSerializer, GroupProfilesSerializer, GroupInputChannelSerializer,
                                  GroupDeleteRegisterSerializer, GroupsUserGroupSerializer, UserGroupsSerializer)
from main.test.mixins import FieldsTestSerializerMixin
from profiles.tests.utils import create_groups
from themes.tests.test_serializers import UniqueValidityTest


@pytest.mark.django_db
class TestGroupSerializer:

    @pytest.mark.parametrize("description,profile_ctrl_user_id,email,signature,citizen_nd,create_parent,valid", (
            ("test description", "MOBI0210", "email@email.com", "https://test.com", False, True, True),
            ("test description", "MOBI0210", "", "", True, True, True),
            ("test description", "", "email@email.com", "https://test.com", False, True, False),
            ("", "MOBI0210", "email@email.com", "https://test.com", False, True, False),
            ("test description", "MOBI0210", "email@email.com", "https://test.com", False, False, False),
    ))
    def test_group_serializer(self, description, profile_ctrl_user_id, email, signature, citizen_nd, create_parent,
                              valid):

        if create_parent:
            parent = mommy.make(Group, user_id="222", profile_ctrl_user_id="22222").pk
        else:
            parent = None

        data = {
            "description": description,
            "profile_ctrl_user_id": profile_ctrl_user_id,
            "no_reasigned": True,
            "email": email,
            "signature": signature,
            "letter_template_id_id": mommy.make(LetterTemplate, user_id=1).pk,
            "parent": parent,
            "last_pending_delivery": date.today(),
            "citizen_nd": citizen_nd,
            "certificate": True,
            "validate_thematic_tree": True,
            "is_ambit": False,
            "reassignments": [{
                "reasign_group": mommy.make(Group, user_id="resign", profile_ctrl_user_id="resign").pk
            }],
            "input_channels": [{"input_channel": mommy.make(InputChannel, user_id="22222").pk}],
            "can_reasign_groups": [{
                "origin_group": mommy.make(Group, user_id="can_reasign_group",
                                           profile_ctrl_user_id="can_reasign_group").pk
            }],
        }
        ser = GroupSerializer(data=data)
        assert ser.is_valid() is valid, "Group serializer fails"
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize("create,invalid,nosend,valid", (
            (True, False, False, True),
            (False, True, False, False),
            (False, False, True, True),
    ))
    def test_group_serializer_letter_template(self, create, invalid, nosend, valid):

        if create:
            letter_template_id = mommy.make(LetterTemplate, user_id=1).pk
        elif invalid:
            letter_template_id = 354
        else:
            # nosend  True
            letter_template_id = None

        data = {
            "description": "test",
            "profile_ctrl_user_id": "3543543",
            "no_reasigned": True,
            "email": "test@test.com",
            "signature": "test",
            "letter_template_id_id": letter_template_id,
            "parent": mommy.make(Group, user_id="222", profile_ctrl_user_id="22222").pk,
            "last_pending_delivery": date.today(),
            "citizen_nd": False,
            "certificate": True,
            "validate_thematic_tree": True,
            "is_ambit": False,
            "reassignments": [{
                "reasign_group": mommy.make(Group, user_id="resign", profile_ctrl_user_id="resign").pk
            }],
            "input_channels": [{"input_channel": mommy.make(InputChannel, user_id="22222").pk}],
            "can_reasign_groups": [{
                "origin_group": mommy.make(Group, user_id="can_reasign_group",
                                           profile_ctrl_user_id="can_reasign_group").pk
            }],
        }
        ser = GroupSerializer(data=data)
        assert ser.is_valid() is valid, "Group serializer fails"
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize("add_parent_itself,remove_parent,valid", (
            (True, False, False),
            (False, False, True),
            (False, True, False),
    ))
    def test_group_parent_validation(self, add_parent_itself, remove_parent, valid):
        _, group, _, _, _, _ = create_groups()
        group_data = GroupSerializer(instance=group).data
        if add_parent_itself:
            group_data["parent"] = group.pk

        if remove_parent:
            group_data.pop("parent", None)
        ser = GroupSerializer(instance=group, data=group_data)
        assert ser.is_valid() is valid, "Group serializer parent validation fails"
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize("is_dair,add_parent,valid", (
            (True, False, True),
            (True, True, False),
            (False, False, False),
            (False, True, True),
    ))
    def test_group_dair_parent(self, is_dair, add_parent, valid):
        dair_group, parent, _, _, _, _ = create_groups()
        if is_dair:
            group = dair_group
        else:
            group = parent
        group_data = GroupSerializer(instance=group).data

        if add_parent:
            group_data["parent"] = mommy.make(Group, user_id="333", profile_ctrl_user_id="33333").pk
        else:
            group_data.pop("parent", None)
        ser = GroupSerializer(instance=group, data=group_data)
        assert ser.is_valid() is valid, "Group serializer parent validation fails"
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize(
        "notifications_emails,records_next_expire,records_next_expire_freq,records_allocation,pend_records,"
        "pend_records_freq,pend_communication,pend_communication_freq,valid", (
                ("test@test.com,test2@test.com", True, 3, False, False, 2, True, 3, True),
                ("test@test.com,test2m", True, 3, False, False, 2, True, 3, False),
                (",test@test.com", True, 3, False, False, 2, True, 3, False),
                ("test@test.com,test2@test.com,", True, 3, False, False, 2, True, 3, False),
                ("test@test.com,test2@test.com", False, 3, True, True, 2, True, 3, True),
                ("test@test.com,test2@test.com", True, 0, False, False, 2, True, 3, False),
                ("test@test.com,test2@test.com", True, 5, False, False, 0, True, 3, False),
                ("test@test.com,test2@test.com", True, 1, False, False, 2, True, 0, False),
        ))
    def test_groups_notifications_config(self, notifications_emails, records_next_expire, records_next_expire_freq,
                                         records_allocation, pend_records, pend_records_freq, pend_communication,
                                         pend_communication_freq, valid):
        parent = mommy.make(Group, user_id="333", profile_ctrl_user_id="33333")
        group = mommy.make(Group, user_id="333", profile_ctrl_user_id="33333", parent=parent)
        group_data = GroupSerializer(instance=group).data

        group_data["notifications_emails"] = notifications_emails
        group_data["records_next_expire"] = records_next_expire
        group_data["records_next_expire_freq"] = records_next_expire_freq
        group_data["records_allocation"] = records_allocation
        group_data["pend_records"] = pend_records
        group_data["pend_records_freq"] = pend_records_freq
        group_data["pend_communication"] = pend_communication
        group_data["pend_communication_freq"] = pend_communication_freq

        ser = GroupSerializer(instance=group, data=group_data)
        assert ser.is_valid() is valid, "Group serializer parent validation fails"
        assert isinstance(ser.errors, dict)

    def test_reassign_groups(self):
        dair, parent, soon, _, _, _ = create_groups(create_reasignations=False)
        group_data = GroupSerializer(instance=parent).data
        group_data["reassignments"] = [{"reasign_group": dair.pk}]
        group_data["can_reasign_groups"] = [{"origin_group": soon.pk}]
        ser = GroupSerializer(instance=parent, data=group_data)
        assert ser.is_valid() is True, "Group serializer parent validation fails"
        ser.save()
        assert GroupReassignation.objects.get(origin_group=parent, reasign_group=dair)
        assert GroupReassignation.objects.get(origin_group=soon, reasign_group=parent)

    def test_group_icon(self, base64_image):
        _, group, _, _, _, _ = create_groups()
        group_data = GroupSerializer(instance=group).data
        group_data["icon"] = base64_image
        ser = GroupSerializer(instance=group, data=group_data)
        assert ser.is_valid() is True, "Group serializer icon validation fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestGroupShortSerializer(FieldsTestSerializerMixin):
    serializer_class = GroupShortSerializer
    data_keys = ["id", "description", "profile_ctrl_user_id", "dist_sect_id", "email", "signature", "citizen_nd",
                 "is_ambit", "is_mobile"]

    def get_instance(self):
        return mommy.make(Group, user_id="2222", profile_ctrl_user_id="222")


@pytest.mark.django_db
class TestGroupReassignationSerializer:

    @pytest.mark.parametrize("valid", (True, False))
    def test_group_reassignation_serializer(self, valid):
        group_pk = mommy.make(Group, profile_ctrl_user_id="2222222", user_id="2222").pk if valid else None
        ser = GroupReassignationSerializer(data={"reasign_group": group_pk})
        assert ser.is_valid() is valid, "Group Reassignation serializer fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestGroupInputChannelSerializer:

    @pytest.mark.parametrize("create_input_channel,order,valid", (
            (True, 10, True),
            (False, 5, False),
            (True, None, False),
    ))
    def test_group_can_reassign_serializer(self, create_input_channel, order, valid):
        input_channel_pk = mommy.make(
            InputChannel, user_id="2222").pk if create_input_channel else None
        ser = GroupInputChannelSerializer(data={"input_channel": input_channel_pk, "order": order})
        assert ser.is_valid() is valid, "Group Can Reassign serializer fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestUserGroupSetSerializer:

    @override_settings(INTERNAL_GROUPS_SYSTEM=False)
    @pytest.mark.parametrize("group_id,valid", (
            ("MOBI0210", True),
            ("MOBI0000", False),
            (None, False)
    ))
    def test_groupset_serializer(self, group_id, valid):
        data = {
            "group_id": group_id,
        }
        get_user_groups = Mock(return_value=["MOBI0210", "MOBI0211", "MOBI0212"])
        with patch("profiles.serializers.get_user_groups_header_list", get_user_groups):
            ser = GroupSetSerializer(data=data, context={"ctrl_user_groups": get_user_groups()})
            assert ser.is_valid() is valid, "GroupSet serializer fails"
            assert isinstance(ser.errors, dict)

    @override_settings(INTERNAL_GROUPS_SYSTEM=True)
    @pytest.mark.parametrize("group_id,valid", (
            ("MOBI0210", True),
            ("MOBI0000", True),
            (None, False)
    ))
    def test_groupset_serializer_internal_groups(self, group_id, valid):
        data = {
            "group_id": group_id,
        }
        ser = GroupSetSerializer(data=data)
        assert ser.is_valid() is valid, "GroupSet serializer fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestUserGroupSerializer:

    @override_settings(INTERNAL_GROUPS_SYSTEM=False)
    @pytest.mark.parametrize("num_permissions", (0, 1, 3))
    def test_user_group_serializer_external_groups(self, num_permissions):
        group = None
        get_user_groups = Mock(return_value=["MOBI0210", "MOBI0211", "MOBI0212"])
        with patch("profiles.serializers.get_user_groups_header_list", get_user_groups):

            for profile_ctrl_user_id in get_user_groups():
                group = mommy.make(Group, profile_ctrl_user_id=profile_ctrl_user_id, user_id="2222")
            user = mommy.make(User, username="test")
            user_group = UserGroup.objects.create(user=user, group=group)
            permissions = [mommy.make(Permission, user_id="2222") for _ in range(num_permissions)]

            serializer_context = {"ctrl_user_groups": get_user_groups()}
            if permissions:
                serializer_context["permissions"] = permissions
            ser = UserGroupSerializer(instance=user_group, context={"ctrl_user_groups": get_user_groups(),
                                                                    "permissions": permissions})
            assert ser.data["username"] == user.username
            assert ser.data["current_group"]["profile_ctrl_user_id"] == group.profile_ctrl_user_id
            assert len(ser.data["groups"]) == len(get_user_groups())
            assert len(ser.data["permissions"]) == num_permissions
            for user_group_data in ser.data["groups"]:
                assert user_group_data["profile_ctrl_user_id"] in get_user_groups()

    @override_settings(INTERNAL_GROUPS_SYSTEM=False)
    @pytest.mark.parametrize("num_permissions", (0, 1, 3))
    def test_user_group_serializer_external_groups_deleted(self, num_permissions):
        group = None
        groups = []
        get_user_groups = Mock(return_value=["MOBI0210", "MOBI0211", "MOBI0212"])
        with patch("profiles.serializers.get_user_groups_header_list", get_user_groups):

            for profile_ctrl_user_id in get_user_groups():
                group = mommy.make(Group, profile_ctrl_user_id=profile_ctrl_user_id, user_id="2222")
                groups.append(group)
            user = mommy.make(User, username="test")
            user_group = UserGroup.objects.create(user=user, group=group)
            permissions = [mommy.make(Permission, user_id="2222") for _ in range(num_permissions)]

            serializer_context = {"ctrl_user_groups": get_user_groups()}
            if permissions:
                serializer_context["permissions"] = permissions

            groups[0].delete()
            ser = UserGroupSerializer(instance=user_group, context={"ctrl_user_groups": get_user_groups(),
                                                                    "permissions": permissions})
            assert ser.data["username"] == user.username
            assert ser.data["current_group"]["profile_ctrl_user_id"] == group.profile_ctrl_user_id
            assert len(ser.data["groups"]) == len(get_user_groups()) - 1
            assert len(ser.data["permissions"]) == num_permissions
            for user_group_data in ser.data["groups"]:
                assert user_group_data["profile_ctrl_user_id"] in get_user_groups()

    @override_settings(INTERNAL_GROUPS_SYSTEM=True)
    @pytest.mark.parametrize("num_permissions", (0, 1, 3))
    def test_user_group_serializer_internal_groups(self, num_permissions):
        group = None
        groups = []
        group_codes = ["MOBI0210", "MOBI0211", "MOBI0212"]

        for profile_ctrl_user_id in group_codes:
            group = mommy.make(Group, profile_ctrl_user_id=profile_ctrl_user_id, user_id="2222")
            groups.append(group)

        user = mommy.make(User, username="test")
        user_group = UserGroup.objects.create(user=user, group=group)
        for _ in range(num_permissions):
            permission = mommy.make(Permission, user_id="2222")
            profile = mommy.make(Profile, user_id="211111")
            ProfilePermissions.objects.create(profile=profile, permission=permission)
            GroupProfiles.objects.create(profile=profile, group=group)

        for gr in groups:
            GroupsUserGroup.objects.create(user_group=user_group, group=gr)

        ser = UserGroupSerializer(instance=user_group)
        assert ser.data["username"] == user.username
        assert ser.data["current_group"]["profile_ctrl_user_id"] == group.profile_ctrl_user_id
        assert len(ser.data["groups"]) == len(group_codes)
        assert len(ser.data["permissions"]) == num_permissions
        for user_group_data in ser.data["groups"]:
            assert user_group_data["profile_ctrl_user_id"] in group_codes

    @override_settings(INTERNAL_GROUPS_SYSTEM=True)
    @pytest.mark.parametrize("num_permissions", (0, 1, 3))
    def test_user_group_serializer_internal_groups_deleted(self, num_permissions):
        group = None
        groups = []
        group_codes = ["MOBI0210", "MOBI0211", "MOBI0212"]

        for profile_ctrl_user_id in group_codes:
            group = mommy.make(Group, profile_ctrl_user_id=profile_ctrl_user_id, user_id="2222")
            groups.append(group)

        user = mommy.make(User, username="test")
        user_group = UserGroup.objects.create(user=user, group=group)
        for _ in range(num_permissions):
            permission = mommy.make(Permission, user_id="2222")
            profile = mommy.make(Profile, user_id="211111")
            ProfilePermissions.objects.create(profile=profile, permission=permission)
            GroupProfiles.objects.create(profile=profile, group=group)

        for gr in groups:
            GroupsUserGroup.objects.create(user_group=user_group, group=gr)

        groups[0].delete()

        ser = UserGroupSerializer(instance=user_group)
        assert ser.data["username"] == user.username
        assert ser.data["current_group"]["profile_ctrl_user_id"] == group.profile_ctrl_user_id
        assert len(ser.data["groups"]) == len(group_codes) - 1
        assert len(ser.data["permissions"]) == num_permissions
        for user_group_data in ser.data["groups"]:
            assert user_group_data["profile_ctrl_user_id"] in group_codes


@pytest.mark.django_db
class TestPermissionSerializer(FieldsTestSerializerMixin):
    serializer_class = PermissionSerializer
    data_keys = ["id", "codename", "description", "category"]

    def get_instance(self):
        return mommy.make(Permission, user_id="22222")


@pytest.mark.django_db
class TestProfilePermissionsSerializer:

    @pytest.mark.parametrize("create_permission,valid", (
            (True, True),
            (None, False)
    ))
    def test_profile_permissions_serializer(self, create_permission, valid):
        if create_permission:
            permission = mommy.make(Permission, user_id="22222")
            data = {"permission": permission.pk}
        else:
            data = {"permission": None}
        ser = ProfilePermissionsSerializer(data=data)
        assert ser.is_valid() is valid, "Profile Permissions serializer fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestProfileSerializer(UniqueValidityTest):
    serializer_class = ProfileSerializer

    def given_fields(self):
        return ["description"]

    @pytest.mark.parametrize("description,create_permission,valid", (
            ("profile_description", True, True),
            ("profile_description", None, False),
            ("", True, False),
    ))
    def test_profile_permissions(self, description, create_permission, valid):
        data = {"description": description}
        if create_permission:
            permission = mommy.make(Permission, user_id="22222")
            data.update({"permissions": [{"permission": permission.pk}]})
        else:
            data.update({"permissions": [{"permission": None}]})

        ser = ProfileSerializer(data=data)
        assert ser.is_valid() is valid, "Profile Serializer fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestGroupProfilesSerializer:

    @pytest.mark.parametrize("create_profile,valid", (
            (True, True),
            (None, False)
    ))
    def test_profile_permissions_serializer(self, create_profile, valid):
        if create_profile:
            profile = mommy.make(Profile, user_id="22222")
            data = {"profile": profile.pk}
        else:
            data = {"profile": None}
        ser = GroupProfilesSerializer(data=data)
        assert ser.is_valid() is valid, "Group Profiles serializer fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestGroupDeleteRegisterSerializer:

    @pytest.mark.parametrize(
        "set_delete_group,set_resignation_group,copy_delete_group,delete_parent_group,only_open,valid", (
                (True, True, False, False, True, True),
                (False, True, False, False, True, False),
                (True, False, False, False, True, False),
                (True, True, False, False, False, True),
                (True, True, True, False, False, False),
                (True, True, False, True, True, False),
        ))
    def test_group_delete_register_serializer(self, set_delete_group, set_resignation_group, copy_delete_group,
                                              delete_parent_group, only_open, valid):

        _, parent, soon, _, noambit_parent, _ = create_groups()

        if set_delete_group and not delete_parent_group:
            delete_group_pk = soon.pk
        elif set_delete_group and delete_parent_group:
            delete_group_pk = noambit_parent.pk
        else:
            delete_group_pk = None
        if set_resignation_group:
            reasignation_group_pk = parent.pk
        else:
            reasignation_group_pk = None

        if copy_delete_group:
            reasignation_group_pk = delete_group_pk

        data = {
            "deleted_group_id": delete_group_pk,
            "reasignation_group_id": reasignation_group_pk,
            "only_open": only_open
        }
        ser = GroupDeleteRegisterSerializer(data=data)
        assert ser.is_valid() is valid, "Group Delete Register serializer fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestGroupsUserGroupSerializer:

    @pytest.mark.parametrize("create_group,valid", (
            (True, True),
            (False, False)
    ))
    def test_groups_usergroup_serializer(self, create_group, valid):
        group_pk = mommy.make(Group, user_id="2222", profile_ctrl_user_id="2222").pk if create_group else None
        ser = GroupsUserGroupSerializer(data={"group": group_pk})
        assert ser.is_valid() is valid, "Groups UserGroup serializer fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestUserGroupsSerializer:

    @pytest.mark.parametrize("add_username,add_group_id,add_group_to_groups,valid", (
            (True, True, True, True),
            (False, True, True, False),
            (True, False, True, False),
            (True, True, False, True),  # Remove access from user by removing groups
    ))
    def test_user_groups_serializer(self, add_username, add_group_id, add_group_to_groups, valid):
        user = User.objects.create(username="test")
        dair, parent, soon, soo2, _, _ = create_groups()

        groups = [{"group": dair.pk}, {"group": soon.pk}]
        if add_group_to_groups:
            groups.append({"group": parent.pk})

        data = {
            "username": user.username if add_username else "",
            "group_id": parent.pk if add_group_id else None,
            "groups": groups,
            'profiles': []
        }

        ser = UserGroupsSerializer(data=data)
        assert ser.is_valid() is valid, "User Groups serializer fails"
        assert isinstance(ser.errors, dict)
