import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.functional import cached_property
from mock import patch, Mock
from model_mommy import mommy

from communications.models import Conversation, Message, ConversationGroup
from iris_masters.models import Process, RecordState, Reason
from iris_masters.permissions import ADMIN
from profiles.models import Group, Profile, Permission, ProfilePermissions, GroupProfiles, UserGroup, GroupsUserGroup
from profiles.permissions import IrisPermissionChecker
from profiles.tests.utils import dict_groups, create_groups
from record_cards.models import Applicant, Citizen
from record_cards.permissions import NO_REASIGNABLE, VALIDATE, CANCEL, THEME_CHANGE, UPDATE
from record_cards.record_actions.actions import RecordActions
from record_cards.record_actions.state_machine import RecordCardStateMachine
from record_cards.tests.utils import CreateRecordCardMixin
from communications.tests.utils import load_missing_data


@pytest.mark.django_db
class TestRecordActions(CreateRecordCardMixin):

    @cached_property
    def user(self):
        return User.objects.create(username="test")

    @staticmethod
    def set_permissions(group, permissions_codes):
        profile = mommy.make(Profile, user_id="2222")
        for permission in Permission.objects.filter(codename__in=permissions_codes):
            ProfilePermissions.objects.create(permission=permission, profile=profile)
        GroupProfiles.objects.create(group=group, profile=profile)

    def set_user_group(self, group):
        user_group = UserGroup.objects.create(user=self.user, group=group)
        GroupsUserGroup.objects.create(user_group=user_group, group=group)

    @pytest.mark.parametrize("can_answer", (True, False))
    def test_review_answer_action(self, can_answer):
        load_missing_data()
        record_card = self.create_record_card()
        actions = {
            "answer": {
                "action_url": reverse("private_api:record_cards:record_card_answer", kwargs={"pk": record_card.pk}),
                "can_perform": True
            }
        }
        group_can_answer = Mock(return_value={"can_answer": can_answer, "reason": "asdadsadsa"})
        with patch("record_cards.models.RecordCard.group_can_answer", group_can_answer):
            RecordActions(record_card, self.user).review_answer_action(actions)
            assert actions["answer"]["can_perform"] is can_answer
            if not can_answer:
                assert actions["answer"]["action_url"] is None
                assert "reason" in actions["answer"]

    def test_set_add_multirecord_action(self):
        actions = {}
        load_missing_data()
        record_card = self.create_record_card()
        RecordActions(record_card, self.user).set_add_multirecord_action(actions)
        assert actions[RecordActions.MULTIRECORD_ACTION]["action_url"]
        assert actions[RecordActions.MULTIRECORD_ACTION]["check_url"] is None
        assert actions[RecordActions.MULTIRECORD_ACTION]["can_perform"] is True
        assert actions[RecordActions.MULTIRECORD_ACTION]["action_method"] == "post"

    def test_set_update_applicant_action(self):
        actions = {}
        record_card = self.create_record_card()
        RecordActions(record_card, self.user).set_update_applicant_action(actions)
        assert actions["update-applicant"]["action_url"]
        assert actions["update-applicant"]["check_url"] is None
        assert actions["update-applicant"]["can_perform"] is True
        assert actions["update-applicant"]["action_method"] == "patch"

    @pytest.mark.parametrize("action_group,can_perform", (
            (1, True), (2, True), (3, False), (4, False), (5, False), (6, False)
    ))
    def test_set_delete_file_action(self, action_group, can_perform):
        load_missing_data()
        actions = {}
        groups = dict_groups()
        action_group -= 1
        first_key = list(groups.keys())[0]
        group = groups[action_group + first_key]
        self.set_user_group(group)
        if group == Group.get_dair_group():
            self.set_group_permissions('AAA', group, [ADMIN])
        record_card = self.create_record_card(responsible_profile=groups[1 + first_key])
        RecordActions(record_card, self.user).set_delete_file_action(actions)
        assert actions["delete-file"]["can_perform"] is can_perform
        assert actions["delete-file"]["check_url"] is None
        assert actions["delete-file"]["action_method"] == "delete"
        if can_perform:
            assert actions["delete-file"]["action_url"]
        else:
            assert actions["delete-file"]["action_url"] is None

    @pytest.mark.parametrize("action_group,can_perform", (
            (1, True), (2, True), (3, False), (4, False), (5, False), (6, False)
    ))
    def test_set_upload_file_action(self, action_group, can_perform):
        load_missing_data()
        actions = {}
        groups = dict_groups()
        action_group -= 1
        first_key = list(groups.keys())[0]
        group = groups[action_group + first_key]
        self.set_user_group(group)
        if group == Group.get_dair_group():
            self.set_group_permissions('AAA', group, [ADMIN])
        record_card = self.create_record_card(responsible_profile=groups[1 + first_key])
        RecordActions(record_card, self.user).set_upload_file_action(actions)
        assert actions[RecordActions.UPLOAD_FILE_ACTION]["can_perform"] is can_perform
        assert actions[RecordActions.UPLOAD_FILE_ACTION]["check_url"] is None
        assert actions[RecordActions.UPLOAD_FILE_ACTION]["action_method"] == "put"
        if can_perform:
            assert actions[RecordActions.UPLOAD_FILE_ACTION]["action_url"]
        else:
            assert actions[RecordActions.UPLOAD_FILE_ACTION]["action_url"] is None

    def test_set_toogle_urgency_action(self):
        load_missing_data()
        actions = {}
        record_card = self.create_record_card()
        RecordActions(record_card, self.user).set_toogle_urgency_action(actions)
        assert actions[RecordActions.TOOGLE_URGENCY_ACTION]["action_url"]
        assert actions[RecordActions.TOOGLE_URGENCY_ACTION]["check_url"] is None
        assert actions[RecordActions.TOOGLE_URGENCY_ACTION]["can_perform"] is True
        assert actions[RecordActions.TOOGLE_URGENCY_ACTION]["action_method"] == "patch"

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
    def test_set_reasign_action(self, reassignment_not_allowed, initial_record_state, validated_reassignable,
                                created_at, claims_number, parent_reasignation, grand_parent_reasignation, action_url,
                                reason):
        load_missing_data()
        grand_parent, parent, first_soon, second_soon, noambit_parent, noambit_soon = create_groups()
        if parent_reasignation:
            reasignation_group = parent
        elif grand_parent_reasignation:
            reasignation_group = grand_parent
        else:
            reasignation_group = noambit_soon
        self.set_user_group(reasignation_group)

        element_detail = self.create_element_detail(validated_reassignable=validated_reassignable,
                                                    validation_place_days=3)
        record_card = self.create_record_card(record_state_id=initial_record_state, element_detail=element_detail,
                                              claims_number=claims_number, responsible_profile=parent,
                                              reassignment_not_allowed=reassignment_not_allowed)

        actions = {}
        RecordActions(record_card, self.user).set_reasign_action(actions)
        if action_url:
            assert actions[RecordActions.REASIGN_ACTION]["action_url"]
            assert actions[RecordActions.REASIGN_ACTION]["can_perform"] is True
        else:
            assert actions[RecordActions.REASIGN_ACTION]["action_url"] is None
            assert actions[RecordActions.REASIGN_ACTION]["can_perform"] is False
        assert actions[RecordActions.REASIGN_ACTION]["check_url"] is None
        if reason:
            assert actions[RecordActions.REASIGN_ACTION]["reason"]
        else:
            assert actions[RecordActions.REASIGN_ACTION]["reason"] is None
        assert actions[RecordActions.REASIGN_ACTION]["action_method"] == "post"

    @pytest.mark.parametrize("applicant_blocked,can_perform", (
            (True, False), (False, True),
    ))
    def test_set_claim_action(self, applicant_blocked, can_perform):
        load_missing_data()
        actions = {}
        citizen = mommy.make(Citizen, blocked=applicant_blocked, user_id='2222')
        applicant = mommy.make(Applicant, citizen=citizen, user_id='2222')

        record_card = self.create_record_card(record_state_id=RecordState.CLOSED, applicant=applicant,
                                              create_worflow=True)
        RecordActions(record_card, self.user).set_claim_action(actions)
        assert actions["claim"]["can_perform"] is can_perform
        assert actions["claim"]["check_url"]
        assert actions["claim"]["action_method"] == "post"
        if can_perform:
            assert actions["claim"]["action_url"]
        else:
            assert actions["claim"]["action_url"] is None
            assert actions["claim"]["reason"]

    def test_set_toogle_block_action(self):
        load_missing_data()
        actions = {}
        record_card = self.create_record_card()
        RecordActions(record_card, self.user).set_block_action(actions)
        assert actions[RecordActions.BLOCK_ACTION]["action_url"]
        assert actions[RecordActions.BLOCK_ACTION]["check_url"] is None
        assert actions[RecordActions.BLOCK_ACTION]["can_perform"] is True
        assert actions[RecordActions.BLOCK_ACTION]["action_method"] == "post"

    def test_set_draft_answer(self):
        load_missing_data()
        actions = {}
        record_card = self.create_record_card()
        RecordActions(record_card, self.user).set_draft_answer(actions)
        assert actions["draft-answer"]["action_url"]
        assert actions["draft-answer"]["check_url"] is None
        assert actions["draft-answer"]["can_perform"] is True
        assert actions["draft-answer"]["action_method"] == "post"

    @pytest.mark.parametrize("responsible_profile", (True, False))
    def test_set_add_conversation_action(self, responsible_profile):
        load_missing_data()
        actions = {}
        group = mommy.make(Group, user_id="2222", profile_ctrl_user_id="2222", group_plate='XMXMXMXM')
        self.set_user_group(group)
        if responsible_profile:
            record_card = self.create_record_card(responsible_profile=group)
        else:
            record_card = self.create_record_card()
        RecordActions(record_card, self.user).set_add_conversation_action(actions)
        assert actions[RecordActions.ADD_CONVERSATION_ACTION]["check_url"] is None
        if responsible_profile:
            assert actions[RecordActions.ADD_CONVERSATION_ACTION]["action_url"]
            assert actions[RecordActions.ADD_CONVERSATION_ACTION]["can_perform"] is True
        else:
            assert actions[RecordActions.ADD_CONVERSATION_ACTION]["action_url"] is None
            assert actions[RecordActions.ADD_CONVERSATION_ACTION]["can_perform"] is False
            assert actions[RecordActions.ADD_CONVERSATION_ACTION]["reason"]

    @pytest.mark.parametrize("user_permissions", ([NO_REASIGNABLE], []))
    def test_set_toogle_reasignable_action(self, user_permissions):
        load_missing_data()
        group = mommy.make(Group, user_id="2222", profile_ctrl_user_id="22222")
        self.set_user_group(group)
        self.set_permissions(group, user_permissions)
        user_perms = IrisPermissionChecker.get_for_user(self.user)

        record_card = self.create_record_card(responsible_profile=group)
        actions = {}
        RecordActions(record_card, self.user).set_toogle_reasignable_action(actions, user_perms)

        assert actions["toogle-reasignable"]["check_url"] is None
        assert actions["toogle-reasignable"]["action_method"] == "patch"
        if user_permissions:
            assert actions["toogle-reasignable"]["action_url"]
            assert actions["toogle-reasignable"]["can_perform"] is True
        else:
            assert actions["toogle-reasignable"]["action_url"] is None
            assert actions["toogle-reasignable"]["can_perform"] is False
            assert actions["toogle-reasignable"]["reason"]

    @pytest.mark.parametrize("user_permissions", ([THEME_CHANGE], []))
    def test_set_theme_change_action(self, user_permissions):
        load_missing_data()
        group = mommy.make(Group, user_id="2222", profile_ctrl_user_id="22222")
        self.set_user_group(group)
        self.set_permissions(group, user_permissions)
        user_perms = IrisPermissionChecker.get_for_user(self.user)

        record_card = self.create_record_card(responsible_profile=group, record_state_id=RecordState.PENDING_VALIDATE)
        actions = {}
        RecordActions(record_card, self.user).set_theme_change_action(actions, user_perms)

        assert actions[RecordActions.CHANGE_THEME_ACTION]["check_url"]
        assert actions[RecordActions.CHANGE_THEME_ACTION]["action_method"] == "post"
        if user_permissions:
            assert actions[RecordActions.CHANGE_THEME_ACTION]["action_url"]
            assert actions[RecordActions.CHANGE_THEME_ACTION]["can_perform"] is True
        else:
            assert actions[RecordActions.CHANGE_THEME_ACTION]["action_url"] is None
            assert actions[RecordActions.CHANGE_THEME_ACTION]["can_perform"] is False
            assert actions[RecordActions.CHANGE_THEME_ACTION]["reason"]

    @pytest.mark.parametrize("record_state_id,can_perform", (
            (RecordState.PENDING_VALIDATE, True),
            (RecordState.EXTERNAL_RETURNED, True),
            (RecordState.IN_PLANING, False),
            (RecordState.IN_RESOLUTION, False),
            (RecordState.CLOSED, True),
    ))
    def test_theme_change_action_state(self, record_state_id, can_perform):
        load_missing_data()
        group = mommy.make(Group, user_id="2222", profile_ctrl_user_id="22222")
        self.set_user_group(group)
        self.set_permissions(group, [THEME_CHANGE])
        user_perms = IrisPermissionChecker.get_for_user(self.user)

        record_card = self.create_record_card(responsible_profile=group, record_state_id=record_state_id)
        actions = {}
        RecordActions(record_card, self.user).set_theme_change_action(actions, user_perms)

        assert actions[RecordActions.CHANGE_THEME_ACTION]["can_perform"] is can_perform
        assert actions[RecordActions.CHANGE_THEME_ACTION]["check_url"]
        assert actions[RecordActions.CHANGE_THEME_ACTION]["action_method"] == "post"
        if can_perform:
            assert actions[RecordActions.CHANGE_THEME_ACTION]["action_url"]
        else:
            assert actions[RecordActions.CHANGE_THEME_ACTION]["action_url"] is None
            assert actions[RecordActions.CHANGE_THEME_ACTION]["reason"]

    @pytest.mark.parametrize("user_permissions", ([UPDATE], []))
    def test_set_update_action(self, user_permissions):
        load_missing_data()
        group = mommy.make(Group, user_id="2222", profile_ctrl_user_id="22222")
        self.set_user_group(group)
        self.set_permissions(group, user_permissions)
        user_perms = IrisPermissionChecker.get_for_user(self.user)

        record_card = self.create_record_card(responsible_profile=group)
        actions = {}
        RecordActions(record_card, self.user).set_update_action(actions, user_perms)

        assert actions[RecordActions.UPDATE_ACTION]["check_url"] is None
        assert actions[RecordActions.UPDATE_ACTION]["action_method"] == "patch"
        if user_permissions:
            assert actions[RecordActions.UPDATE_ACTION]["action_url"]
            assert actions[RecordActions.UPDATE_ACTION]["can_perform"] is True
        else:
            assert actions[RecordActions.UPDATE_ACTION]["action_url"] is None
            assert actions[RecordActions.UPDATE_ACTION]["can_perform"] is False
            assert actions[RecordActions.UPDATE_ACTION]["reason"]

    @pytest.mark.parametrize("record_state_id,user_permissions", (
            (RecordState.PENDING_VALIDATE, [CANCEL]),
            (RecordState.PENDING_VALIDATE, []),
            (RecordState.CANCELLED, [CANCEL]),
            (RecordState.CANCELLED, []),
    ))
    def test_set_cancel_request(self, record_state_id, user_permissions):
        load_missing_data()
        group = mommy.make(Group, user_id="2222", profile_ctrl_user_id="22222")
        self.set_user_group(group)
        self.set_permissions(group, user_permissions)
        user_perms = IrisPermissionChecker.get_for_user(self.user)

        record_card = self.create_record_card(record_state_id=record_state_id, responsible_profile=group)
        actions = {}
        RecordActions(record_card, self.user).set_cancel_request(actions, user_perms)

        assert actions["cancel-request"]["check_url"] is None
        assert actions["cancel-request"]["action_method"] == "post"

        if user_permissions or record_card.record_state_id in RecordState.CLOSED_STATES:
            assert actions["cancel-request"]["action_url"] is None
            assert actions["cancel-request"]["can_perform"] is False
            assert actions["cancel-request"]["reason"]
        else:
            assert actions["cancel-request"]["action_url"]
            assert actions["cancel-request"]["can_perform"] is True
            assert actions["cancel-request"]["reason_comment_id"] == Reason.RECORDCARD_CANCEL_REQUEST

    @pytest.mark.parametrize("user_permissions,process_pk,record_state_id,action,action_permission", (
            ([VALIDATE], Process.CLOSED_DIRECTLY, RecordState.PENDING_VALIDATE, RecordCardStateMachine.validated,
             VALIDATE),
            ([], Process.CLOSED_DIRECTLY, RecordState.PENDING_VALIDATE, RecordCardStateMachine.validated, VALIDATE),
            ([CANCEL], Process.PLANING_RESOLUTION_RESPONSE, RecordState.IN_RESOLUTION, RecordCardStateMachine.canceled,
             CANCEL),
            ([], Process.PLANING_RESOLUTION_RESPONSE, RecordState.IN_RESOLUTION, RecordCardStateMachine.canceled,
             CANCEL)
    ))
    def test_review_action_permissions(self, user_permissions, process_pk, record_state_id, action, action_permission):
        load_missing_data()
        group = mommy.make(Group, user_id="2222", profile_ctrl_user_id="22222")
        self.set_user_group(group)
        self.set_permissions(group, user_permissions)
        user_perms = IrisPermissionChecker.get_for_user(self.user)
        record_card = self.create_record_card(responsible_profile=group, process_pk=process_pk,
                                              record_state_id=record_state_id)

        actions = RecordCardStateMachine(record_card).get_transitions()
        RecordActions(record_card, self.user).review_action_permissions(actions, action, user_perms, action_permission)
        if user_permissions:
            assert actions[action]["action_url"]
            assert actions[action]["can_perform"] is True
        else:
            assert actions[action]["action_url"] is None
            assert actions[action]["can_perform"] is False
            assert actions[action]["reason"]

    @pytest.mark.parametrize("tramit_group,can_response_messages", (
            (1, False), (2, False), (3, False), (3, True), (5, True),
    ))
    def test_set_initial_actions(self, tramit_group, can_response_messages):
        load_missing_data()
        groups = dict_groups()
        tramit_group -= 1
        first_key = list(groups.keys())[0]
        self.set_user_group(groups[tramit_group + first_key])
        parent = groups[1 + first_key]
        record_card = self.create_record_card(responsible_profile=parent)
        if can_response_messages:
            conversation = mommy.make(Conversation, user_id='222', record_card=record_card, creation_group=parent)
            ConversationGroup.objects.create(conversation=conversation, group=groups[tramit_group + first_key])
            mommy.make(Message, user_id='22222', conversation=conversation, group=parent,
                       record_state_id=record_card.record_state_id)

        actions = RecordActions(record_card, self.user).set_initial_actions()

        if record_card.group_can_tramit_record(groups[tramit_group + first_key]):
            assert RecordActions.ADD_MESSAGE_ACTION in actions
            assert RecordActions.ADD_COMMENT_ACTION in actions

        if can_response_messages:
            assert RecordActions.ADD_MESSAGE_ACTION in actions

        for action_key, action in actions.items():
            assert action["action_url"]
            assert action["check_url"] is None
            assert action["can_perform"] is True
            assert action["action_method"] == "post"

    @pytest.mark.parametrize("tramit_group,can_response_messages,detail_mode", (
            (1, False, True),
            (2, False, True),
            (3, False, True),
            (3, True, True),
            (5, True, True),
            (1, False, False),
            (2, False, False),
            (3, False, False),
            (3, True, False),
            (5, True, False),
    ))
    def test_actions(self, tramit_group, can_response_messages, detail_mode):
        load_missing_data()
        groups = dict_groups()
        tramit_group -= 1
        first_key = list(groups.keys())[0]
        self.set_user_group(groups[tramit_group + first_key])
        parent = groups[1 + first_key]
        record_card = self.create_record_card(responsible_profile=parent, record_state_id=RecordState.IN_RESOLUTION,
                                              process_pk=Process.EVALUATION_RESOLUTION_RESPONSE)
        if can_response_messages:
            conversation = mommy.make(Conversation, user_id='222', record_card=record_card, creation_group=parent)
            ConversationGroup.objects.create(conversation=conversation, group=groups[tramit_group + first_key])
            mommy.make(Message, user_id='22222', conversation=conversation, group=parent,
                       record_state_id=record_card.record_state_id)
        actions = RecordActions(record_card, self.user, detail_mode=detail_mode).actions()

        if detail_mode:
            can_tramit_actions = [RecordActions.ADD_MESSAGE_ACTION, RecordActions.ADD_COMMENT_ACTION,
                                  RecordActions.UPDATE_ACTION, "toogle-reasignable", RecordActions.CHANGE_THEME_ACTION,
                                  RecordActions.ADD_CONVERSATION_ACTION, "draft-answer", RecordActions.BLOCK_ACTION,
                                  "claim", RecordActions.REASIGN_ACTION, RecordActions.TOOGLE_URGENCY_ACTION,
                                  RecordActions.UPLOAD_FILE_ACTION, "delete-file", "update-applicant",
                                  RecordActions.MULTIRECORD_ACTION, "cancel-request"]
        else:
            can_tramit_actions = [RecordActions.REASIGN_ACTION]

        if record_card.group_can_tramit_record(groups[tramit_group + first_key]):
            for tramit_action in can_tramit_actions:
                assert tramit_action in actions

        if can_response_messages and detail_mode:
            assert RecordActions.ADD_MESSAGE_ACTION in actions
        elif not detail_mode:
            assert RecordActions.ADD_MESSAGE_ACTION not in actions

    @pytest.mark.parametrize("initial_record_state_id,unexpected_actions", (
            (RecordState.CANCELLED, RecordActions.cancelled_disallowed_actions),
            (RecordState.CLOSED, RecordActions.closed_disallowed_actions)
    ))
    def test_review_closed_states_allowed_actions(self, initial_record_state_id, unexpected_actions):
        load_missing_data()
        dair, _, _, _, _, _ = create_groups()
        record_card = self.create_record_card(responsible_profile=dair, record_state_id=initial_record_state_id)
        record_actions = {action: {} for action in RecordActions.cancelled_disallowed_actions}
        RecordActions(record_card, self.user, detail_mode=True).review_closed_states_allowed_actions(
            record_actions)
        for unexpected_action in unexpected_actions:
            assert unexpected_action not in record_actions

    def test_set_applicant_action(self):
        load_missing_data()
        dair, _, _, _, _, _ = create_groups()
        record_card = self.create_record_card(responsible_profile=dair, record_state_id=RecordState.NO_PROCESSED)
        actions = RecordActions(record_card, self.user, detail_mode=True).actions()
        assert RecordCardStateMachine.applicant in actions
        assert len(actions.keys()) == 1

    def test_set_applicant_action_cant(self):
        load_missing_data()
        dair, _, _, _, _, _ = create_groups()
        record_card = self.create_record_card(responsible_profile=dair, record_state_id=RecordState.NO_PROCESSED)
        cant_set_applicant = Mock(return_value=True)
        with patch("record_cards.models.RecordCard.cant_set_applicant", cant_set_applicant):
            actions = RecordActions(record_card, self.user, detail_mode=True).actions()
            assert RecordCardStateMachine.applicant not in actions
            assert not actions
