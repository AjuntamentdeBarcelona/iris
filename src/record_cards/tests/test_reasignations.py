from datetime import timedelta

import pytest
from model_mommy import mommy

from iris_masters.models import RecordState, Reason
from profiles.models import Group, GroupReassignation
from profiles.tests.utils import create_groups, add_extra_group_level
from record_cards.models import RecordCardReasignation
from record_cards.record_actions.reasignations import PossibleReassignations
from record_cards.tests.utils import CreateRecordCardMixin
from iris_masters.tests.utils import load_missing_data_reasons

@pytest.mark.django_db
class TestRecordCardReassignactions(CreateRecordCardMixin):

    @pytest.mark.parametrize("reasign_number,create_previous", (
            (0, False), (1, False), (3, False), (0, True), (1, True), (3, True),
    ))
    def test_record_card_possible_reasisgnations(self, reasign_number, create_previous):
        load_missing_data_reasons()
        record_card = self.create_record_card()
        sons = []
        if create_previous:
            reasing = Group.objects.create(profile_ctrl_user_id='REASIG', user_id='2222', parent=None)
            RecordCardReasignation.objects.create(
                record_card=record_card, user_id='2222', group=reasing, previous_responsible_profile=reasing,
                next_responsible_profile=record_card.responsible_profile, reason_id=Reason.CITIZEN_COMUNICATION,
                comment="text")
            sons.append(reasing)

        for group_code in range(reasign_number):
            soon = Group.objects.create(profile_ctrl_user_id='GRPAS{}'.format(group_code), user_id='2222',
                                        parent=record_card.responsible_profile)
            GroupReassignation.objects.create(origin_group=record_card.responsible_profile, reasign_group=soon)
            sons.append(soon)

        assert PossibleReassignations(record_card).possible_reasignations(record_card.responsible_profile) == sons

    @pytest.mark.parametrize("reassign_number,derivation_reason", (
        (3, Reason.INITIAL_ASSIGNATION),
        (3, Reason.DERIVATE_RESIGNATION),
    ))
    def test_not_accept_derivations_as_previous(self, reassign_number, derivation_reason):
        load_missing_data_reasons()
        # Test return reassignation to previous reasigner, it should
        record_card = self.create_record_card()
        groups = []
        # Create reasignation for the first derivation
        initial_group = Group.objects.create(profile_ctrl_user_id='REASIG', user_id='2222', parent=None)
        RecordCardReasignation.objects.create(
            record_card=record_card, user_id='2222', group=initial_group, previous_responsible_profile=initial_group,
            next_responsible_profile=record_card.responsible_profile, reason_id=derivation_reason,
            comment="text")
        # Configure reassignations for record responsible profile
        for group_code in range(reassign_number):
            son = Group.objects.create(profile_ctrl_user_id='GRPAS{}'.format(group_code), user_id='2222',
                                        parent=record_card.responsible_profile)
            GroupReassignation.objects.create(origin_group=record_card.responsible_profile, reasign_group=son)
            groups.append(son)
        # When result is got
        result = PossibleReassignations(record_card).possible_reasignations(record_card.responsible_profile)
        assert result == groups, 'Should only return direct reassignation groups and not derivation ones.'

    @pytest.mark.parametrize("state,should_reassign_to_previous", (
        (RecordState.PENDING_VALIDATE, True),
        (RecordState.IN_RESOLUTION, False),
    ))
    def test_return_to_previous_only_in_pending_to_validate(self, state, should_reassign_to_previous):
        """
        Records can be returned to the group who reassigned it to you, but only if they are pending to validate or
        if the detail allows reassignations once is validated.
        """
        load_missing_data_reasons()
        record_card = self.create_record_card(record_state_id=state, validated_reassignable=False)
        record_card.responsible_profile.level = 0
        record_card.responsible_profile.save()
        # When exists previous reassignation to a group from other ambit (2)
        initial_group = Group.objects.create(profile_ctrl_user_id='REASIG', user_id='2',
                                             parent=None, group_plate='XXXXX')
        RecordCardReasignation.objects.create(
            record_card=record_card, user_id='2222', group=initial_group, previous_responsible_profile=initial_group,
            next_responsible_profile=record_card.responsible_profile, reason_id=Reason.DAIR_CORRECTION,
            comment="text")

        # Should be (or not) reassignable to previous
        groups = PossibleReassignations(record_card).reasignations(record_card.responsible_profile)
        assert bool(groups) == should_reassign_to_previous

    @pytest.mark.parametrize("initial_record_state,validated_reassignable,created_at,claims_number,is_ambit,"
                             "only_ambit", (
                                     (RecordState.PENDING_VALIDATE, False, 0, 0, True, False),
                                     (RecordState.IN_PLANING, False, 0, 0, True, True),
                                     (RecordState.IN_PLANING, True, 0, 0, True, False),
                                     (RecordState.PENDING_VALIDATE, False, 0, 0, False, False),
                                     (RecordState.PENDING_VALIDATE, False, 0, 5, True, True),
                                     (RecordState.PENDING_VALIDATE, False, 0, 5, False, False),
                                     (RecordState.PENDING_VALIDATE, False, 3, 0, True, False),
                                     (RecordState.PENDING_VALIDATE, False, 5, 0, True, True),
                                     (RecordState.PENDING_VALIDATE, False, 10, 0, True, True),
                             ))
    def test_only_ambit_reasignation(self, initial_record_state, validated_reassignable, created_at,
                                     claims_number, is_ambit, only_ambit):
        element_detail = self.create_element_detail(validated_reassignable=validated_reassignable,
                                                    validation_place_days=3)
        responsible_profile = mommy.make(Group, user_id='2222', profile_ctrl_user_id='2222', is_ambit=is_ambit)
        record_card = self.create_record_card(record_state_id=initial_record_state, element_detail=element_detail,
                                              claims_number=claims_number, responsible_profile=responsible_profile)
        if created_at:
            record_card.created_at -= timedelta(days=created_at)

        only_ambit_reasignation = PossibleReassignations(record_card).only_ambit_reasignation(responsible_profile)
        assert only_ambit_reasignation['only_ambit'] is only_ambit
        if only_ambit:
            assert "reason" in only_ambit_reasignation
        else:
            assert "reason" not in only_ambit_reasignation

    @pytest.mark.parametrize(
        "reassignment_not_allowed,initial_record_state,validated_reassignable,created_at,"
        "claims_number,parent_reasignation,grand_parent_reasignation,expected_reasignations_key", (
                (True, RecordState.PENDING_VALIDATE, False, 0, 0, False, True, 3),
                (True, RecordState.PENDING_VALIDATE, False, 0, 0, False, False, 1),
                (True, RecordState.PENDING_VALIDATE, False, 0, 0, True, False, 4),
                (False, RecordState.PENDING_VALIDATE, False, 0, 0, False, True, 3),
                (False, RecordState.PENDING_VALIDATE, False, 0, 0, False, False, 1),
                (False, RecordState.PENDING_VALIDATE, False, 0, 0, True, False, 2),
                (False, RecordState.IN_PLANING, False, 0, 0, False, True, 3),
                (False, RecordState.IN_PLANING, False, 0, 0, False, False, 1),
                (False, RecordState.IN_PLANING, False, 0, 0, True, False, 4),
                (False, RecordState.IN_PLANING, True, 0, 0, False, True, 3),
                (False, RecordState.IN_PLANING, True, 0, 0, False, False, 1),
                (False, RecordState.IN_PLANING, True, 0, 0, True, False, 2),
                (False, RecordState.PENDING_VALIDATE, False, 0, 5, False, True, 3),
                (False, RecordState.PENDING_VALIDATE, False, 0, 5, False, False, 1),
                (False, RecordState.PENDING_VALIDATE, False, 0, 5, True, False, 4),
                (False, RecordState.PENDING_VALIDATE, False, 3, 0, False, True, 3),
                (False, RecordState.PENDING_VALIDATE, False, 3, 0, False, False, 1),
                (False, RecordState.PENDING_VALIDATE, False, 3, 0, True, False, 2),
                (False, RecordState.PENDING_VALIDATE, False, 5, 0, False, True, 3),
                (False, RecordState.PENDING_VALIDATE, False, 5, 0, False, False, 1),
                (False, RecordState.PENDING_VALIDATE, False, 5, 0, True, False, 2),
                (False, RecordState.PENDING_VALIDATE, False, 10, 0, False, True, 3),
                (False, RecordState.PENDING_VALIDATE, False, 10, 0, False, False, 1),
                (False, RecordState.PENDING_VALIDATE, False, 10, 0, True, False, 2),
        ))
    def test_record_card_reasignations(self, reassignment_not_allowed, initial_record_state, validated_reassignable,
                                       created_at, claims_number, parent_reasignation,
                                       grand_parent_reasignation, expected_reasignations_key):
        grand_parent, parent, first_soon, second_soon, noambit_parent, noambit_soon = create_groups(
            create_dair_reassignation=True
        )
        add_extra_group_level(first_soon)

        expected_reasignations = {
            1: [],
            2: [grand_parent, parent, first_soon, second_soon, noambit_parent, noambit_soon],
            3: [parent, first_soon, second_soon, noambit_parent, noambit_soon],
            4: [grand_parent, first_soon, second_soon]
        }

        element_detail = self.create_element_detail(validated_reassignable=validated_reassignable,
                                                    validation_place_days=3)
        record_card = self.create_record_card(record_state_id=initial_record_state, element_detail=element_detail,
                                              claims_number=claims_number, responsible_profile=parent,
                                              reassignment_not_allowed=reassignment_not_allowed)

        if parent_reasignation:
            reasignation_group = parent
        elif grand_parent_reasignation:
            GroupReassignation.objects.create(origin_group=grand_parent, reasign_group=first_soon)
            GroupReassignation.objects.create(origin_group=grand_parent, reasign_group=second_soon)
            reasignation_group = grand_parent
        else:
            reasignation_group = noambit_soon

        GroupReassignation.objects.bulk_create([
            GroupReassignation(origin_group=reasignation_group, reasign_group=group)
            for group in [grand_parent, parent, first_soon, second_soon, noambit_parent, noambit_soon]
            if group != reasignation_group and not GroupReassignation.objects.filter(
                origin_group=reasignation_group, reasign_group=group
            ).exists()
        ])
        expected = [e for e in expected_reasignations[expected_reasignations_key]
                    if e != record_card.responsible_profile]
        reasignations = PossibleReassignations(record_card).reasignations(reasignation_group)
        assert reasignations == expected

    @pytest.mark.parametrize(
        "reassignment_not_allowed,initial_record_state,validated_reassignable,created_at,"
        "claims_number,is_ambit,reasignation_type", (
                (True, RecordState.PENDING_VALIDATE, False, 0, 0, True, PossibleReassignations.REASIGN_AMBIT_GROUPS),
                (False, RecordState.PENDING_VALIDATE, False, 0, 0, True, PossibleReassignations.REASIGN_CONFIG_GROUPS),
                (False, RecordState.IN_PLANING, False, 0, 0, True, PossibleReassignations.REASIGN_AMBIT_GROUPS),
                (False, RecordState.IN_PLANING, True, 0, 0, True, PossibleReassignations.REASIGN_CONFIG_GROUPS),
                (False, RecordState.PENDING_VALIDATE, False, 0, 0, True, PossibleReassignations.REASIGN_CONFIG_GROUPS),
                (False, RecordState.PENDING_VALIDATE, False, 0, 0, False, PossibleReassignations.REASIGN_CONFIG_GROUPS),
                (False, RecordState.PENDING_VALIDATE, False, 0, 5, True, PossibleReassignations.REASIGN_AMBIT_GROUPS),
                (False, RecordState.PENDING_VALIDATE, False, 0, 5, False,
                 PossibleReassignations.REASIGN_COORDINATOR_ONLY),
                (False, RecordState.PENDING_VALIDATE, False, 3, 0, True, PossibleReassignations.REASIGN_CONFIG_GROUPS),
                (False, RecordState.PENDING_VALIDATE, False, 5, 0, True, PossibleReassignations.REASIGN_AMBIT_GROUPS),
                (False, RecordState.PENDING_VALIDATE, False, 10, 0, True, PossibleReassignations.REASIGN_AMBIT_GROUPS),
        ))
    def test_select_reasignation_type(self, reassignment_not_allowed, initial_record_state, validated_reassignable,
                                      created_at, claims_number, is_ambit, reasignation_type):
        element_detail = self.create_element_detail(validated_reassignable=validated_reassignable,
                                                    validation_place_days=3)
        responsible_profile = mommy.make(Group, user_id='2222', profile_ctrl_user_id='2222', is_ambit=is_ambit)
        record_card = self.create_record_card(record_state_id=initial_record_state, element_detail=element_detail,
                                              claims_number=claims_number,
                                              reassignment_not_allowed=reassignment_not_allowed,
                                              responsible_profile=responsible_profile)
        if created_at:
            record_card.created_at -= timedelta(days=created_at)

        select_reasignation_type = PossibleReassignations(record_card).select_reasignation_type(responsible_profile)
        assert select_reasignation_type['reasignation_type'] == reasignation_type
        if reasignation_type in [PossibleReassignations.NO_REASIGN_GROUPS,
                                 PossibleReassignations.REASIGN_AMBIT_GROUPS]:
            assert "reason" in select_reasignation_type

    @pytest.mark.parametrize(
        "reassignment_not_allowed,initial_record_state,validated_reassignable,created_at,"
        "claims_number,parent_reasignation,grand_parent_reasignation,action_url,reason", (
                (True, RecordState.PENDING_VALIDATE, False, 0, 0, False, True, True, True),
                (True, RecordState.PENDING_VALIDATE, False, 0, 0, False, False, False, True),
                (True, RecordState.PENDING_VALIDATE, False, 0, 0, True, False, True, True),
                (False, RecordState.PENDING_VALIDATE, False, 0, 0, False, True, True, False),
                (False, RecordState.PENDING_VALIDATE, False, 0, 0, False, False, False, True),
                (False, RecordState.PENDING_VALIDATE, False, 0, 0, True, False, True, False),
                (False, RecordState.IN_PLANING, False, 0, 0, False, True, True, True),
                (False, RecordState.IN_PLANING, False, 0, 0, False, False, False, True),
                (False, RecordState.IN_PLANING, False, 0, 0, True, False, True, True),
                (False, RecordState.IN_PLANING, True, 0, 0, False, True, True, False),
                (False, RecordState.IN_PLANING, True, 0, 0, False, False, False, True),
                (False, RecordState.IN_PLANING, True, 0, 0, True, False, True, False),
                (False, RecordState.PENDING_VALIDATE, False, 0, 5, False, True, True, True),
                (False, RecordState.PENDING_VALIDATE, False, 0, 5, False, False, False, True),
                (False, RecordState.PENDING_VALIDATE, False, 0, 5, True, False, True, True),
                (False, RecordState.PENDING_VALIDATE, False, 3, 0, False, True, True, False),
                (False, RecordState.PENDING_VALIDATE, False, 3, 0, False, False, False, True),
                (False, RecordState.PENDING_VALIDATE, False, 3, 0, True, False, True, False),
                (False, RecordState.PENDING_VALIDATE, False, 5, 0, False, True, True, False),
                (False, RecordState.PENDING_VALIDATE, False, 5, 0, False, False, False, True),
                (False, RecordState.PENDING_VALIDATE, False, 5, 0, True, False, True, False),
                (False, RecordState.PENDING_VALIDATE, False, 10, 0, False, True, True, False),
                (False, RecordState.PENDING_VALIDATE, False, 10, 0, False, False, False, True),
                (False, RecordState.PENDING_VALIDATE, False, 10, 0, True, False, True, False),
        ))
    def test_record_card_reasign_action(self, reassignment_not_allowed, initial_record_state, validated_reassignable,
                                        created_at, claims_number, parent_reasignation, grand_parent_reasignation,
                                        action_url, reason):
        grand_parent, parent, first_soon, second_soon, noambit_parent, noambit_soon = create_groups()
        element_detail = self.create_element_detail(validated_reassignable=validated_reassignable,
                                                    validation_place_days=3)
        record_card = self.create_record_card(record_state_id=initial_record_state, element_detail=element_detail,
                                              claims_number=claims_number, responsible_profile=parent,
                                              reassignment_not_allowed=reassignment_not_allowed)
        if parent_reasignation:
            reasignation_group = parent
        elif grand_parent_reasignation:
            reasignation_group = grand_parent
        else:
            reasignation_group = noambit_soon

        reasign_action = PossibleReassignations(record_card).reasign_action(reasignation_group)
        if action_url:
            assert reasign_action['action_url']
            assert reasign_action['can_perform'] is True
        else:
            assert reasign_action['action_url'] is None
            assert reasign_action['can_perform'] is False
        assert reasign_action['check_url'] is None
        if reason:
            assert reasign_action['reason']
        else:
            assert reasign_action['reason'] is None
