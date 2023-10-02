import pytest

from iris_masters.models import RecordState
from iris_masters.permissions import ADMIN
from profiles.models import Group
from profiles.tests.utils import create_groups, dict_groups
from record_cards.record_actions.record_files import GroupManageFiles
from record_cards.tests.utils import CreateRecordCardMixin, SetGroupRequestMixin


@pytest.mark.django_db
class TestGroupManageFiles(SetGroupRequestMixin, CreateRecordCardMixin):

    @pytest.mark.parametrize("responsible_group,group_manage,creation_group,record_state_id,can_add_file", (
            (2, 2, 3, RecordState.PENDING_VALIDATE, True),
            (2, 3, 3, RecordState.PENDING_VALIDATE, True),
            (2, 3, 5, RecordState.PENDING_VALIDATE, False),
            (3, 2, 5, RecordState.PENDING_VALIDATE, True),
            (2, 4, 5, RecordState.IN_PLANING, False),
            (2, 1, 3, RecordState.PENDING_VALIDATE, True),
            (2, 1, 3, RecordState.IN_RESOLUTION, True),
    ))
    def test_group_can_add_file(self, responsible_group, group_manage, creation_group, record_state_id, can_add_file):
        groups = dict_groups()
        first_key = list(groups.keys())[0]
        responsible_group += first_key - 1
        group_manage += first_key - 1
        creation_group += first_key - 1
        record_card = self.create_record_card(record_state_id=record_state_id,
                                              responsible_profile=groups[responsible_group],
                                              creation_group=groups[creation_group])

        manage_group = groups[group_manage]
        _, request = self.set_group_request(group=manage_group)
        if manage_group == Group.get_dair_group():
            self.set_group_permissions('AAA', manage_group, [ADMIN])
        assert GroupManageFiles(record_card, manage_group, request.user).group_can_add_file() is can_add_file

    @pytest.mark.parametrize("responsible_profile,dair_group,can_delete_file", (
            (True, False, True),
            (False, True, True),
            (False, False, False),
    ))
    def test_group_can_delete_file(self, responsible_profile, dair_group, can_delete_file):
        dair, parent, soon, _, _, _ = create_groups()
        record_card = self.create_record_card(responsible_profile=parent)
        if responsible_profile:
            group = record_card.responsible_profile
        elif dair_group:
            group = dair
            self.set_group_permissions('AAA', group, [ADMIN])
        else:
            group = soon

        _, request = self.set_group_request(group=group)

        assert GroupManageFiles(record_card, group, request.user).group_can_delete_file() is can_delete_file
