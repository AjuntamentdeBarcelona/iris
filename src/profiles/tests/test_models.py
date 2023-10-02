import pytest
from django.contrib.auth.models import User
from django.test import override_settings
from model_mommy import mommy

from profiles.models import Group, UserGroup, Profile, Permission, ProfilePermissions, GroupProfiles, GroupsUserGroup, \
    ProfileUserGroup
from profiles.tests.utils import create_groups
import logging

logger = logging.getLogger(__name__)


@pytest.mark.django_db
class TestGroupAmbits:

    def test_get_isambit_groups(self):
        grand_parent, parent, first_soon, second_soon, noambit_parent, noambit_soon = create_groups()
        assert first_soon.get_isambit_groups(grand_parent) == [parent]
        assert parent.get_isambit_groups(grand_parent) == [first_soon, second_soon]
        assert grand_parent.get_isambit_groups(grand_parent) == [parent, first_soon, second_soon, noambit_parent,
                                                                 noambit_soon]

    def test_ambit_ancestor(self):
        grand_parent, parent, first_soon, second_soon, noambit_parent, noambit_soon = create_groups()
        assert second_soon.ambit_ancestor(grand_parent) == parent
        assert first_soon.ambit_ancestor(grand_parent) == parent
        assert parent.ambit_ancestor(grand_parent) is None
        assert grand_parent.ambit_ancestor(grand_parent) is None
        assert noambit_parent.ambit_ancestor(grand_parent) is None
        assert noambit_soon.ambit_ancestor(grand_parent) is None

    def test_get_ambit_parent(self):
        grand_parent, parent, first_soon, second_soon, noambit_parent, noambit_soon = create_groups()
        assert second_soon.get_ambit_parent() == parent
        assert first_soon.get_ambit_parent() == first_soon
        assert parent.get_ambit_parent() == parent
        assert grand_parent.get_ambit_parent() == grand_parent
        assert noambit_parent.get_ambit_parent() is None
        assert noambit_soon.get_ambit_parent() is None

    def test_get_ambit_ancestors_groups(self):
        grand_parent, parent, first_soon, second_soon, noambit_parent, noambit_soon = create_groups()
        assert second_soon.get_ambit_ancestors_groups(second_soon.ambit_ancestor(grand_parent)) == [parent, first_soon]
        assert first_soon.get_ambit_ancestors_groups(first_soon.ambit_ancestor(grand_parent)) == [parent, second_soon]

    def test_get_noambit_groups(self):
        grand_parent, _, _, _, noambit_parent, noambit_soon = create_groups()
        assert noambit_parent.get_noambit_groups(grand_parent) == []
        assert noambit_soon.get_noambit_groups(grand_parent) == [noambit_parent]

    def test_ambit(self):
        grand_parent, parent, first_soon, second_soon, noambit_parent, noambit_soon = create_groups()
        assert second_soon.ambit() == [parent, first_soon]
        assert first_soon.ambit() == [parent]
        assert parent.ambit() == [first_soon, second_soon]
        assert grand_parent.ambit() == [parent, first_soon, second_soon, noambit_parent, noambit_soon]
        assert noambit_parent.ambit() == []
        assert noambit_soon.ambit() == [noambit_parent]

    def test_ambit_ids(self):
        grand_parent, parent, first_soon, second_soon, noambit_parent, noambit_soon = create_groups()
        assert second_soon.ambit_ids == [parent.pk, first_soon.pk]
        assert first_soon.ambit_ids == [parent.pk]
        assert parent.ambit_ids == [first_soon.pk, second_soon.pk]
        assert grand_parent.ambit_ids == [parent.pk, first_soon.pk, second_soon.pk, noambit_parent.pk, noambit_soon.pk]
        assert noambit_parent.ambit_ids == []
        assert noambit_soon.ambit_ids == [noambit_parent.pk]

    def test_ambits_ancestors(self):
        grand_parent, parent, first_soon, second_soon, noambit_parent, noambit_soon = create_groups()
        assert second_soon.ambits_ancestors == [grand_parent, parent]
        assert first_soon.ambits_ancestors == [grand_parent, parent, first_soon]
        assert parent.ambits_ancestors == [grand_parent, parent]
        assert grand_parent.ambits_ancestors == [grand_parent]
        assert noambit_parent.ambits_ancestors == [grand_parent]
        assert noambit_soon.ambits_ancestors == [grand_parent]

    def test_calculate_group_plate(self):
        grand_parent, parent, first_soon, second_soon, noambit_parent, noambit_soon = create_groups()
        noambit_soon.parent = parent
        noambit_soon.save()
        Group.objects.rebuild()

        grand_parent.refresh_from_db()
        parent.refresh_from_db()
        first_soon.refresh_from_db()
        second_soon.refresh_from_db()
        noambit_parent.refresh_from_db()
        noambit_soon.refresh_from_db()

        assert grand_parent.calculate_group_plate() == f"{grand_parent.pk}-"
        assert parent.calculate_group_plate() == f"{grand_parent.pk}-{parent.pk}-"
        assert first_soon.calculate_group_plate() == f"{grand_parent.pk}-{parent.pk}-{first_soon.pk}-"
        assert second_soon.calculate_group_plate() == f"{grand_parent.pk}-{parent.pk}-{second_soon.pk}-"
        assert noambit_parent.calculate_group_plate() == f"{grand_parent.pk}-{noambit_parent.pk}-"
        assert noambit_soon.calculate_group_plate() == f"{grand_parent.pk}-{parent.pk}-{noambit_soon.pk}-"


@pytest.mark.django_db
class TestUserGroup:

    @override_settings(INTERNAL_GROUPS_SYSTEM=False)
    @pytest.mark.parametrize("permissions", (0, 1, 3))
    def test_user_group_permissions(self, permissions):
        user = mommy.make(User, username="test")
        group = mommy.make(Group, user_id="test", profile_ctrl_user_id="test")
        user_group = UserGroup.objects.create(user=user, group=group)
        for _ in range(permissions):
            permission = mommy.make(Permission, user_id="2222")
            profile = mommy.make(Profile, user_id="211111")
            ProfilePermissions.objects.create(profile=profile, permission=permission)
            GroupProfiles.objects.create(profile=profile, group=group)

        assert len(user_group.get_user_permissions()) == permissions

    @override_settings(INTERNAL_GROUPS_SYSTEM=True)
    @pytest.mark.parametrize("groups", (0, 1, 3))
    def test_user_group_permissions_internal_groups(self, groups):
        user = mommy.make(User, username="test")
        group = mommy.make(Group, user_id="test", profile_ctrl_user_id="test")
        user_group = UserGroup.objects.create(user=user, group=group)
        for _ in range(groups):
            group = mommy.make(Group, user_id="test", profile_ctrl_user_id="test")
            permission = mommy.make(Permission, user_id="2222")
            profile = mommy.make(Profile, user_id="211111")
            ProfilePermissions.objects.create(profile=profile, permission=permission)
            GroupProfiles.objects.create(profile=profile, group=group)
            GroupsUserGroup.objects.create(user_group=user_group, group=group)

        assert len(user_group.get_user_permissions()) == groups


@pytest.mark.django_db
class TestProfileModel:

    @pytest.mark.parametrize("groups", (0, 1, 3))
    def test_disable_profile_usages(self, groups):
        profile = mommy.make(Profile, user_id="211111")
        user = mommy.make(User, username="test")
        group = mommy.make(Group, user_id="test", profile_ctrl_user_id="test")
        user_group = UserGroup.objects.create(user=user, group=group)
        ProfileUserGroup.objects.create(profile=profile, user_group=user_group)
        for _ in range(groups):
            group = mommy.make(Group, user_id="test", profile_ctrl_user_id="test")
            permission = mommy.make(Permission, user_id="2222")
            ProfilePermissions.objects.create(profile=profile, permission=permission)
            GroupProfiles.objects.create(profile=profile, group=group)

        profile.disable_profile_usages()
        assert GroupProfiles.objects.filter(profile_id=profile.pk, enabled=True).count() == 0
        assert ProfileUserGroup.objects.filter(profile_id=profile.pk, enabled=True).count() == 0
        assert ProfilePermissions.objects.filter(profile_id=profile.pk, enabled=True).count() == 0
