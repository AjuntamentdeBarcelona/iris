from datetime import timedelta

import pytest

from iris_masters.models import RecordState
from profiles.models import Group
from profiles.tests.utils import dict_groups, create_groups
from record_cards.permissions import RECARD_COORDINATOR_VALIDATION_DAYS, RECARD_REASSIGN_OUTSIDE
from record_cards.tests.utils import CreateRecordCardMixin, SetPermissionMixin
from themes.actions.possible_theme_change import PossibleThemeChange
from themes.models import ElementDetail
from communications.tests.utils import load_missing_data
from iris_masters.tests.utils import load_missing_data_process, load_missing_data_districts


@pytest.mark.django_db
class TestPossibleThemeChange(SetPermissionMixin, CreateRecordCardMixin):

    @pytest.mark.parametrize('group,record_state,validated_reassignable,previous_created_at,only_ambit', (
            (1, RecordState.PENDING_VALIDATE, False, False, False),
            (2, RecordState.PENDING_VALIDATE, False, False, False),
            (3, RecordState.PENDING_VALIDATE, False, False, False),
            (2, RecordState.IN_RESOLUTION, True, False, True),
            (3, RecordState.IN_RESOLUTION, False, False, True),
            (2, RecordState.PENDING_VALIDATE, False, True, True),
            (2, RecordState.IN_RESOLUTION, True, True, True),
            (2, RecordState.CLOSED, False, False, False),
    ))
    def test_only_ambit_themes(self, group, record_state, validated_reassignable, previous_created_at, only_ambit):
        load_missing_data()
        groups = dict_groups()
        first_key = list(groups.keys())[0]
        group -= 1
        element_detail = self.create_element_detail(validated_reassignable=validated_reassignable)
        record_card = self.create_record_card(record_state_id=record_state, responsible_profile=groups[first_key + 1],
                                              element_detail=element_detail, previous_created_at=previous_created_at)
        self.set_group_permissions("TEST", groups[group + first_key], [RECARD_REASSIGN_OUTSIDE])
        assert PossibleThemeChange(record_card, groups[group + first_key]).only_ambit_themes() is only_ambit

    @pytest.mark.parametrize("has_permission,days_previous,only_ambit", (
            (True, 5, False), (True, 15, True),
            (False, 3, False), (False, 15, True),
    ))
    def test_only_ambit_permissions(self, has_permission, days_previous, only_ambit):
        dair, parent, soon, _, _, _ = create_groups()
        if has_permission:
            self.set_permission(RECARD_COORDINATOR_VALIDATION_DAYS, parent)
        record_card = self.create_record_card(record_state_id=RecordState.PENDING_VALIDATE, responsible_profile=soon)
        record_card.created_at -= timedelta(days=days_previous)
        record_card.save()
        assert PossibleThemeChange(record_card, parent).only_ambit_themes() is only_ambit

    @pytest.mark.parametrize('group,record_state,validated_reassignable,previous_created_at,expected_themes', (
            (1, RecordState.PENDING_VALIDATE, False, False, 4),
            (2, RecordState.PENDING_VALIDATE, False, False, 4),
            (3, RecordState.PENDING_VALIDATE, False, False, 4),
            (2, RecordState.IN_RESOLUTION, True, False, 1),
            (3, RecordState.IN_RESOLUTION, False, False, 1),
            (2, RecordState.PENDING_VALIDATE, False, True, 1),
            (2, RecordState.IN_RESOLUTION, True, True, 1),
    ))
    def test_themes_to_change(self, group, record_state, validated_reassignable, previous_created_at, expected_themes):
        load_missing_data()
        load_missing_data_process()
        load_missing_data_districts()
        ElementDetail.objects.all().delete()
        for _ in range(3):
            self.create_element_detail(validated_reassignable=validated_reassignable)

        element_detail = self.create_element_detail(validated_reassignable=validated_reassignable,
                                                    create_direct_derivations=True,
                                                    create_district_derivations=True)
        element_detail.register_theme_ambit()

        pk = Group.objects.all().first().pk
        soon_group = Group.objects.get(pk=pk + 3)
        record_card = self.create_record_card(record_state_id=record_state, responsible_profile=soon_group,
                                              element_detail=element_detail, previous_created_at=previous_created_at)
        db_group = Group.objects.get(pk=pk + group)
        themes_to_change = PossibleThemeChange(record_card, db_group).themes_to_change()
        assert themes_to_change.count() == expected_themes
