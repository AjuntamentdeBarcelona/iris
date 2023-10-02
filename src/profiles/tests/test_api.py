import uuid

import pytest
from django.contrib.auth.models import User
from django.test import override_settings
from mock import Mock, patch
from model_mommy import mommy
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND
from rest_framework import status

from iris_masters.models import InputChannel, LetterTemplate
from iris_masters.permissions import ADMIN
from main.open_api.tests.base import (BaseOpenAPIResourceTest, OpenAPIRetrieveMixin, BaseOpenAPITest,
                                      PostOperationMixin, OpenAPIResourceListMixin, DictListGetMixin,
                                      SoftDeleteCheckMixin, BaseOpenAPICRUResourceTest, BasePermissionsTest)
from main.test.mixins import AdminUserMixin
from profiles.models import (Group, UserGroup, GroupInputChannel, Permission, Profile, ProfilePermissions,
                             GroupDeleteRegister, GroupProfiles, GroupsUserGroup, get_anonymous_group)
from profiles.permission_registry import ADMIN_GROUP
from profiles.tests.utils import create_groups, dict_groups
from record_cards.tests.utils import SetUserGroupMixin, SetPermissionMixin


class TestGroup(SoftDeleteCheckMixin, AdminUserMixin, BaseOpenAPICRUResourceTest):
    path = "/profiles/groups/"
    base_api_path = "/services/iris/api"
    deleted_model_class = Group

    @property
    def base64_image(self):
        return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGPwzO0EAAJCAUB17jgyAAAAAElFTkSuQmCC"

    def get_default_data(self):
        return {
            "user_id": str(uuid.uuid4())[:20],
            "description": uuid.uuid4(),
            "profile_ctrl_user_id": str(uuid.uuid4())[:20],
            "no_reasigned": False,
            "icon": self.base64_image,
            "email": "test@test.com",
            "signature": "https://test.com",
            "letter_template_id_id":  mommy.make(LetterTemplate, user_id=1).pk,
            "parent": mommy.make(Group, user_id="2222", profile_ctrl_user_id="2222").pk,
            "last_pending_delivery": "2021-01-01",
            "citizen_nd": False,
            "certificate": True,
            "validate_thematic_tree": True,
            "is_ambit": True,
            "reassignments": [{
                "reasign_group": mommy.make(Group, user_id="resign", profile_ctrl_user_id="resign").pk
            }],
            "input_channels": [{"input_channel": mommy.make(InputChannel, user_id="22222").pk}],
            "can_reasign_groups": [{
                "origin_group": mommy.make(Group, user_id="test", profile_ctrl_user_id="test").pk
            }],
            "notifications_emails": "test@test.com,test2@test.com",
            "records_next_expire": True,
            "records_next_expire_freq": 1,
            "records_allocation": False,
            "pend_records": True,
            "pend_records_freq": 5,
            "pend_communication": True,
            "pend_communication_freq": 7
        }

    def given_create_rq_data(self):
        return {
            "user_id": str(uuid.uuid4())[:20],
            "description": uuid.uuid4(),
            "profile_ctrl_user_id": str(uuid.uuid4())[:20],
            "no_reasigned": False,
            "icon": self.base64_image,
            "email": "test@test.com",
            "signature": "https://test.com",
            "letter_template_id_id":  mommy.make(LetterTemplate, user_id=1).pk,
            "parent": mommy.make(Group, user_id="2222", profile_ctrl_user_id="2222").pk,
            "last_pending_delivery": "2021-01-01",
            "citizen_nd": False,
            "certificate": True,
            "validate_thematic_tree": True,
            "is_ambit": True,
            "reassignments": [{
                "reasign_group": mommy.make(Group, user_id="resign", profile_ctrl_user_id="resign").pk
            }],
            "input_channels": [{"input_channel": mommy.make(InputChannel, user_id="22222").pk}],
            "notifications_emails": "test@test.com,test2@test.com",
            "records_next_expire": True,
            "records_next_expire_freq": 1,
            "records_allocation": False,
            "pend_records": True,
            "pend_records_freq": 5,
            "pend_communication": True,
            "pend_communication_freq": 7
        }

    def when_data_is_invalid(self, data):
        data["description"] = ''
        data["notifications_emails"] = "test@test.com,test2st.com",
        data["pend_records_freq"] = 5

    def given_a_complete_update(self, obj):
        """
        :param obj: Object that will be updated.
        :return: Dictionary with attrs for creating a partial update on a given obj
        """
        obj["reassignments"] = [{
            "reasign_group": mommy.make(Group, user_id="resign", profile_ctrl_user_id="resign").pk
        }]
        obj["input_channels"] = [{"input_channel": mommy.make(InputChannel, user_id="22222").pk}]
        obj["icon"] = self.base64_image
        return obj

    def given_a_partial_update(self, obj):
        """
        :param obj: Object that will be updated.
        :return: Dictionary with attrs for creating a partial update on a given obj
        """
        obj["icon"] = self.base64_image
        return obj

    @pytest.mark.parametrize("object_number", (0, 1, 3))
    def test_list(self, object_number):
        [self.given_an_object() for obj in range(0, object_number)]
        response = self.list(force_params={"page_size": self.paginate_by})
        object_number *= 4  # Because of reassignments creation and parents
        object_number += 1  # Because group for admin permissions
        self.should_return_list(object_number, self.paginate_by, response)

    def test_update_put(self):
        obj = self.given_an_object()
        obj.update({self.path_pk_param_name: obj[self.lookup_field]})
        rq_data = self.given_a_complete_update(obj)
        with patch("profiles.tasks.group_update_group_descendants_plates.delay") as plate_delay:
            response = self.put(force_params=rq_data)
            assert response.status_code == HTTP_200_OK
            self.should_complete_update(response, obj)
            plate_delay.assert_called()

    def test_update_change_parent(self):
        obj = self.given_an_object()
        obj.update({self.path_pk_param_name: obj[self.lookup_field]})
        rq_data = self.given_a_complete_update(obj)
        rq_data["parent"] = mommy.make(Group, user_id="2222", profile_ctrl_user_id="2222").pk
        with patch("profiles.views.set_themes_ambits.delay") as mock_delay:
            response = self.put(force_params=rq_data)
            assert response.status_code == HTTP_200_OK
            self.should_complete_update(response, obj)
            mock_delay.assert_called()

    @pytest.mark.parametrize("create_profile,expected_response", (
            (True, HTTP_201_CREATED),
            (None, HTTP_400_BAD_REQUEST),
    ))
    def test_group_profiles(self, create_profile, expected_response):
        rq_data = self.get_default_data()
        if create_profile:
            permission = mommy.make(Permission, user_id="22222")
            profile = mommy.make(Profile, user_id="22222")
            ProfilePermissions.objects.create(permission=permission, profile=profile)
            rq_data["profiles"] = [{"profile": profile.pk}]
        else:
            rq_data["profiles"] = [{"profile": None}]

        self.when_is_authenticated()
        response = self.create(rq_data)
        assert response.status_code == expected_response
        if expected_response == HTTP_201_CREATED:
            self.should_create_object(response, rq_data)

    def test_create_valid(self):
        rq_data = self.given_create_rq_data()
        self.when_is_authenticated()

        with patch("profiles.tasks.group_update_group_descendants_plates.delay") as mock_delay:
            response = self.create(rq_data)
            assert response.status_code == HTTP_201_CREATED
            self.should_create_object(response, rq_data)
            mock_delay.assert_called_once()


class TestUserGroupRetrieve(OpenAPIRetrieveMixin, BaseOpenAPITest):
    detail_path = "/profiles/user-groups/"
    base_api_path = "/services/iris/api"

    @override_settings(INTERNAL_GROUPS_SYSTEM=False)
    @pytest.mark.parametrize("user_groups,create_user_group,expected_response", (
            (["MOBI0210", "MOBI0211", "MOBI0212"], True, HTTP_200_OK),
            ([], True, HTTP_400_BAD_REQUEST),
            (["MOBI0210", "MOBI0211", "MOBI0212"], False, HTTP_404_NOT_FOUND)
    ))
    def test_retrieve(self, user_groups, create_user_group, expected_response):
        group = mommy.make(Group, profile_ctrl_user_id="929292929", user_id="2222")
        get_user_groups = Mock(return_value=user_groups)
        with patch("profiles.views.get_user_groups_header_list", get_user_groups):
            with patch("profiles.serializers.get_user_groups_header_list", get_user_groups):
                for profile_ctrl_user_id in get_user_groups():
                    group = mommy.make(Group, profile_ctrl_user_id=profile_ctrl_user_id, user_id="2222")

                if create_user_group:
                    user_group = UserGroup.objects.create(user=self.user, group=group)
                response = self.retrieve()
                assert response.status_code == expected_response
                if expected_response == HTTP_200_OK:
                    assert response.json()["username"] == self.user.username
                    assert response.json()["current_group"][
                               "profile_ctrl_user_id"] == user_group.group.profile_ctrl_user_id
                    assert len(response.json()["groups"]) == len(get_user_groups())
                    for user_group_data in response.json()["groups"]:
                        assert user_group_data["profile_ctrl_user_id"] in get_user_groups(())

    @override_settings(INTERNAL_GROUPS_SYSTEM=True)
    @pytest.mark.parametrize("user_groups,create_user_group,expected_response", (
            (["MOBI0210", "MOBI0211", "MOBI0212"], True, HTTP_200_OK),
            ([], True, HTTP_200_OK),
            (["MOBI0210", "MOBI0211", "MOBI0212"], False, HTTP_404_NOT_FOUND)
    ))
    def test_retrieve_internal_groups(self, user_groups, create_user_group, expected_response):
        group = mommy.make(Group, profile_ctrl_user_id="929292929", user_id="2222")
        groups = []

        for profile_ctrl_user_id in user_groups:
            group = mommy.make(Group, profile_ctrl_user_id=profile_ctrl_user_id, user_id="2222")
            groups.append(group)

        if create_user_group:
            user_group = UserGroup.objects.create(user=self.user, group=group)
            for gr in groups:
                GroupsUserGroup.objects.create(user_group=user_group, group=gr)

        response = self.retrieve()
        assert response.status_code == expected_response

        if expected_response == HTTP_200_OK:
            assert response.json()["username"] == self.user.username
            assert response.json()["current_group"]["profile_ctrl_user_id"] == user_group.group.profile_ctrl_user_id
            assert len(response.json()["groups"]) == len(groups)
            for user_group_data in response.json()["groups"]:
                assert user_group_data["profile_ctrl_user_id"] in user_groups


class TestUserGroupSet(PostOperationMixin, BaseOpenAPITest):
    path = "/profiles/user-groups/set/"
    base_api_path = "/services/iris/api"

    @override_settings(INTERNAL_GROUPS_SYSTEM=False)
    @pytest.mark.parametrize("profile_ctrl_user_id,expected_response", (
            ("MOBI0210", HTTP_200_OK),
            ("MOBI0000", HTTP_400_BAD_REQUEST),
    ))
    def test_user_group_set(self, profile_ctrl_user_id, expected_response):
        get_user_groups = Mock(return_value=["MOBI0210", "MOBI0211", "MOBI0212"])
        with patch("profiles.serializers.get_user_groups_header_list", get_user_groups):
            for ctrl_user_id in get_user_groups():
                mommy.make(Group, profile_ctrl_user_id=ctrl_user_id, user_id="2222")

            response = self.post(force_params={"profile_ctrl_user_id": profile_ctrl_user_id})
            assert response.status_code == expected_response
            if expected_response == HTTP_200_OK:
                response_content = response.json()
                assert "username" in response_content
                assert "groups" in response_content
                assert "current_group" in response_content

    @override_settings(INTERNAL_GROUPS_SYSTEM=True)
    @pytest.mark.parametrize("profile_ctrl_user_id,create_ctrl_group,set_user_group,expected_response", (
            ("MOBI0210", False, True, HTTP_200_OK),
            ("MOBI0000", True, True, HTTP_400_BAD_REQUEST),
            ("MOBI0000", False, True, HTTP_404_NOT_FOUND),
            ("MOBI0210", False, False, HTTP_200_OK),
    ))
    def test_user_group_set_internal_group(self, profile_ctrl_user_id, create_ctrl_group, set_user_group,
                                           expected_response):
        user_groups = ["MOBI0210", "MOBI0211", "MOBI0212"]
        group = None
        groups = []
        for ctrl_user_id in user_groups:
            group = mommy.make(Group, profile_ctrl_user_id=ctrl_user_id, user_id="2222")
            groups.append(group)

        if create_ctrl_group:
            mommy.make(Group, profile_ctrl_user_id=profile_ctrl_user_id, user_id="2222")

        if set_user_group:
            user_group = UserGroup.objects.create(user=self.user, group=group)
            for gr in groups:
                GroupsUserGroup.objects.create(user_group=user_group, group=gr)

        response = self.post(force_params={"profile_ctrl_user_id": profile_ctrl_user_id})
        assert response.status_code == expected_response
        if expected_response == HTTP_200_OK:
            response_content = response.json()
            assert "username" in response_content
            assert "groups" in response_content
            assert "current_group" in response_content


class TestGroupsRebuildTree(PostOperationMixin, BaseOpenAPITest):
    path = "/profiles/groups/rebuildtree/"
    base_api_path = "/services/iris/api"

    @pytest.mark.parametrize("is_admin,expected_response", (
            (True, HTTP_200_OK),
            (False, HTTP_200_OK),
    ))
    def test_groups_rebuild_tree(self, is_admin, expected_response):
        self.user.is_staff = is_admin
        self.user.save()
        response = self.post()
        assert response.status_code == expected_response


class TestGroupsInputChannelsView(OpenAPIResourceListMixin, BaseOpenAPITest):
    path = "/profiles/groups/input_channels/"
    base_api_path = "/services/iris/api"
    group = None

    def given_an_object(self):
        input_channel = mommy.make(InputChannel, user_id="2222")
        GroupInputChannel.objects.create(group=self.group, input_channel=input_channel, enabled=True)

    @pytest.mark.parametrize("object_number", (0, 1, 3))
    def test_list(self, object_number):
        self.group = mommy.make(Group, user_id="2222", profile_ctrl_user_id="222")
        if not hasattr(self.user, "usergroup"):
            UserGroup.objects.create(user=self.user, group=self.group)

        [self.given_an_object() for _ in range(0, object_number)]
        response = self.list(force_params={"page_size": self.paginate_by})
        self.should_return_list(object_number, self.paginate_by, response)


class TestListGetGroupsTreeView(DictListGetMixin, BaseOpenAPITest):
    path = "/profiles/groups/tree/"
    base_api_path = "/services/iris/api"

    def test_get_groups_tree(self):
        grand_parent, parent, first_soon, second_soon, noambit_parent, noambit_soon = create_groups(
            create_reasignations=False)
        response = self.dict_list_retrieve()
        assert response.status_code == HTTP_200_OK
        json_tree = response.json()
        assert json_tree["id"] == grand_parent.pk
        for children in json_tree["childrens"]:
            assert children["id"] in [parent.pk, noambit_parent.pk]

        assert json_tree["childrens"][0]["id"] == parent.pk
        for children in json_tree["childrens"][0]["childrens"]:
            assert children["id"] in [first_soon.pk, second_soon.pk]

        assert json_tree["childrens"][1]["id"] == noambit_parent.pk
        for children in json_tree["childrens"][1]["childrens"]:
            assert children["id"] in [noambit_soon.pk]


class TestPermissionsList(OpenAPIResourceListMixin, BaseOpenAPITest):
    path = "/profiles/permissions/"
    base_api_path = "/services/iris/api"

    @pytest.mark.parametrize("object_number", (0, 1, 5))
    def test_list(self, object_number):
        Permission.objects.all().delete()
        [self.given_an_object() for obj in range(0, object_number)]
        response = self.list(force_params={"page_size": self.paginate_by})
        self.should_return_list(object_number, 0, response)

    def given_an_object(self):
        return mommy.make(Permission, user_id="22222")


class TestProfile(SoftDeleteCheckMixin, AdminUserMixin, SetPermissionMixin, SetUserGroupMixin, BaseOpenAPIResourceTest):
    path = "/profiles/profiles/"
    base_api_path = "/services/iris/api"
    paginate_by = None

    model_class = Profile
    delete_previous_objects = True
    deleted_model_class = Profile

    def get_default_data(self):
        return {
            "description": uuid.uuid4(),
        }

    def given_create_rq_data(self):
        return {
            "description": uuid.uuid4(),
        }

    def when_data_is_invalid(self, data):
        data["description"] = ''

    @pytest.mark.parametrize("object_number", (0, 1, 5))
    def test_list(self, object_number):
        [Profile.objects.create(**self.given_create_rq_data()) for _ in range(0, object_number)]
        response = self.list(force_params={})
        object_number += 1 # Adjust with existent groups for admin permissions
        self.should_return_list(object_number, self.paginate_by, response)

    def test_create_valid(self):
        rq_data = self.given_create_rq_data()
        self.when_is_authenticated()
        response = self.create(rq_data)
        assert response.status_code == HTTP_201_CREATED
        self.should_create_object(response, rq_data)

    @pytest.mark.parametrize("description,create_permission,expected_response", (
            ("profile_description", True, HTTP_201_CREATED),
            ("profile_description", None, HTTP_400_BAD_REQUEST),
            ("", True, HTTP_400_BAD_REQUEST),
    ))
    def test_profile_permissions(self, description, create_permission, expected_response):
        rq_data = {"description": description}
        if create_permission:
            permission = mommy.make(Permission, user_id="22222")
            rq_data["permissions"] = [{"permission": permission.pk}]
        else:
            rq_data["permissions"] = [{"permission": None}]

        self.when_is_authenticated()
        response = self.create(rq_data)
        assert response.status_code == expected_response
        if expected_response == HTTP_201_CREATED:
            self.should_create_object(response, rq_data)

    def test_delete(self):
        obj = self.given_an_object()
        url_params = {self.path_pk_param_name: obj[self.lookup_field]}
        self.create_group_profiles(url_params)
        with patch("profiles.tasks.profile_post_delete.delay") as mock_delay:
            response = self.delete(force_params=url_params)
            self.should_delete(response, url_params)
            mock_delay.assert_called()

    def create_group_profiles(self, url_params):
        dair, parent, soon, _, _, _ = create_groups()
        GroupProfiles.objects.create(profile_id=url_params[self.path_pk_param_name], group=dair)
        GroupProfiles.objects.create(profile_id=url_params[self.path_pk_param_name], group=parent)
        GroupProfiles.objects.create(profile_id=url_params[self.path_pk_param_name], group=soon)


class TestCreateGroupDeleteRegisterView(PostOperationMixin, SetUserGroupMixin, AdminUserMixin, BaseOpenAPITest):
    path = "/profiles/groups/delete/"
    base_api_path = "/services/iris/api"

    @pytest.mark.parametrize(
        "set_delete_group,set_resignation_group,copy_delete_group,delete_parent_group,only_open,expected_response", (
                (True, True, False, False, True, HTTP_201_CREATED),
                (False, True, False, False, True, HTTP_400_BAD_REQUEST),
                (True, False, False, False, True, HTTP_400_BAD_REQUEST),
                (True, True, False, False, False, HTTP_201_CREATED),
                (True, True, True, False, False, HTTP_400_BAD_REQUEST),
                (True, True, False, True, True, HTTP_400_BAD_REQUEST),
        ))
    def test_create_group_delete_register(self, set_delete_group, set_resignation_group, copy_delete_group,
                                          delete_parent_group, only_open, expected_response):
        grand_parent, parent, soon, _, noambit_parent, _ = create_groups()
        self.set_usergroup(grand_parent)

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
        with patch("profiles.tasks.group_delete_action_execute.delay") as mock_delay:
            response = self.post(force_params=data)
            assert response.status_code == expected_response
            if expected_response == HTTP_201_CREATED:
                assert Group.all_objects.get(pk=delete_group_pk).deleted
                response_content = response.json()
                assert GroupDeleteRegister.objects.get(pk=response_content["id"])
                mock_delay.assert_called_once()


class TestProfilesAdminPermissions(BasePermissionsTest):
    base_api_path = "/services/iris/api"

    cases = [
        {
            "detail_path": "/profiles/profiles/{id}/",
            "model_class": Profile,
        },
    ]

    def given_an_object(self, model_class):
        return mommy.make(model_class, user_id="2222")

    def set_admin_permission(self):
        if not hasattr(self.user, "usergroup"):
            group = mommy.make(Group, user_id="222", profile_ctrl_user_id="22222")
            user_group = UserGroup.objects.create(user=self.user, group=group)
            GroupsUserGroup.objects.create(user_group=user_group, group=group)
        else:
            group = self.user.usergroup.group
            GroupsUserGroup.objects.create(user_group=self.user.usergroup, group=group)
        profile = mommy.make(Profile, user_id="222")
        for perm in [ADMIN, ADMIN_GROUP]:
            admin_permission = Permission.objects.get(codename=perm)
            ProfilePermissions.objects.create(permission=admin_permission, profile=profile)
        GroupProfiles.objects.create(group=group, profile=profile)


class TestUserViewSet(AdminUserMixin, BaseOpenAPICRUResourceTest):
    path = "/profiles/users/"
    base_api_path = "/services/iris/api"
    permission_codename = ADMIN_GROUP

    def get_default_data(self):
        dair, parent, soon, _, _, _ = create_groups()
        user = mommy.make(User)
        return {
            "username": user.username,
            "group_id": parent.pk,
            "groups": [{"group": dair.pk}, {"group": parent.pk}, {"group": soon.pk}],
            "profiles": []
        }

    def given_create_rq_data(self):
        dair, parent, soon, _, _, _ = create_groups()
        user = mommy.make(User)
        return {
            "username": user.username,
            "group_id": parent.pk,
            "groups": [{"group": dair.pk}, {"group": parent.pk}, {"group": soon.pk}],
            "profiles": []
        }

    def when_data_is_invalid(self, data):
        data["username"] = ''
        data["group_id"] = None,

    def given_a_complete_update(self, obj):
        """
        :param obj: Object that will be updated.
        :return: Dictionary with attrs for creating a partial update on a given obj
        """
        obj["groups"] = [{"group": 1}, {"group": 2}]
        return obj

    @pytest.mark.parametrize("object_number", (0, 1, 3))
    def test_list(self, object_number):
        groups = dict_groups()
        [self.given_an_object_list(groups) for obj in range(0, object_number)]
        response = self.list(force_params={"page_size": self.paginate_by})
        assert response.status_code == HTTP_200_OK
        self.should_return_list(object_number + 1, self.paginate_by, response)

    def given_an_object_list(self, groups):
        user = mommy.make(User)
        first_key = list(groups.keys())[0]
        user_group = UserGroup.objects.create(user=user, group=groups[first_key + 1])
        GroupsUserGroup.objects.create(user_group=user_group, group=groups[first_key])
        GroupsUserGroup.objects.create(user_group=user_group, group=groups[first_key + 1])
        GroupsUserGroup.objects.create(user_group=user_group, group=groups[first_key + 2])
        return user_group

    def test_update_no_groups(self):
        obj = self.given_an_object()
        obj.update({self.path_pk_param_name: obj[self.lookup_field]})
        obj["groups"] = []
        response = self.put(force_params=obj)
        assert response.status_code == HTTP_400_BAD_REQUEST
        user_group = UserGroup.objects.get(pk=obj["id"])
        assert user_group.group == get_anonymous_group()

    def test_update_put(self):
        obj = self.given_an_object()
        obj.update({self.path_pk_param_name: obj[self.lookup_field]})
        if not Group.objects.filter(pk=1):
            group = Group(pk=1)
            group.save()
        if not Group.objects.filter(pk=2):
            group = Group(pk=2)
            group.save()
        if not Group.objects.filter(id=obj['group_id']):
            group = Group(id=obj['group_id'])
            group.save()
        else:
            group = Group.objects.get(id=obj['group_id'])
            group.is_anonymous = False
            group.save()
        rq_data = self.given_a_complete_update(obj)
        response = self.put(force_params=rq_data)
        assert response.status_code == status.HTTP_200_OK
        self.should_complete_update(response, obj)

    def test_update_patch(self):
        obj = self.given_an_object()
        if not Group.objects.filter(pk=1):
            group = Group(pk=1)
            group.save()
        if not Group.objects.filter(pk=2):
            group = Group(pk=2)
            group.save()
        if not Group.objects.filter(id=obj['group_id']):
            group = Group(id=obj['group_id'])
            group.save()
        else:
            group = Group.objects.get(id=obj['group_id'])
            group.is_anonymous = False
            group.save()
        obj.update({self.path_pk_param_name: obj[self.lookup_field]})
        rq_data = self.given_a_partial_update(obj)
        response = self.patch(force_params=rq_data)
        assert response.status_code == status.HTTP_200_OK
        self.should_partial_update(response, obj)
