from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from iris_masters.models import Reason, RecordState, ResponseChannel
from profiles.permissions import IrisPermissionChecker
from record_cards.permissions import NO_REASIGNABLE, VALIDATE, CANCEL, THEME_CHANGE, UPDATE, RECARD_ANSWER_RESEND, \
    RECARD_PLAN_RESOL, RECARD_ANSWER, RECARD_CLAIM, RECARD_MULTIRECORD, RESP_WILL_SOLVE, RECARD_CLOSED_FILES, \
    RECARD_REASIGN
from record_cards.record_actions.claim_validate import ClaimValidation
from record_cards.record_actions.exceptions import RecordClaimException
from record_cards.record_actions.group_response_messages import GroupCanResponseMessages
from record_cards.record_actions.reasignations import PossibleReassignations
from record_cards.record_actions.record_files import GroupManageFiles
from record_cards.record_actions.state_machine import RecordCardStateMachine
from themes.actions.group_tree import GroupThemeTree
from main.utils import get_user_traceability_id


class RecordActions:
    """
    Class to get possible actions that a user can do with a record card
    """
    MULTIRECORD_ACTION = "add-multirecord"
    RESEND_ANSWER = "answer-resend"
    REASIGN_ACTION = "reasign"
    UPDATE_ACTION = "update"
    TOOGLE_URGENCY_ACTION = "toogle-urgency"
    UPLOAD_FILE_ACTION = "upload-file"
    ADD_MESSAGE_ACTION = "add-message"
    ADD_CONVERSATION_ACTION = "add-conversation"
    ADD_COMMENT_ACTION = "add-comment"
    CHANGE_THEME_ACTION = "theme-change"
    BLOCK_ACTION = "set-block"
    CLAIM = "claim"

    closed_disallowed_actions = [MULTIRECORD_ACTION, REASIGN_ACTION, UPDATE_ACTION,
                                 UPLOAD_FILE_ACTION, ADD_MESSAGE_ACTION, ADD_CONVERSATION_ACTION]
    cancelled_disallowed_actions = [MULTIRECORD_ACTION, REASIGN_ACTION, UPDATE_ACTION, TOOGLE_URGENCY_ACTION,
                                    UPLOAD_FILE_ACTION, ADD_MESSAGE_ACTION, ADD_CONVERSATION_ACTION, ADD_COMMENT_ACTION,
                                    CHANGE_THEME_ACTION]

    def __init__(self, record_card, user, detail_mode=True) -> None:
        self.record_card = record_card
        self.user = user
        self.require_theme_change = False
        self.detail_mode = detail_mode
        self.user_group = self.user.usergroup.group if hasattr(self.user, "usergroup") else None
        self.can_tramit = self.record_card.group_can_tramit_record(self.user_group)
        super().__init__()

    def actions(self):
        actions = self.set_initial_actions() if self.detail_mode else {}
        user_perms = IrisPermissionChecker.get_for_user(self.user)
        transitions = RecordCardStateMachine(self.record_card).get_transitions() if self.generate_transitions else {}
        if self.can_tramit:
            actions.update(transitions)
            self.review_action_permissions(actions, RecordCardStateMachine.validated, user_perms, VALIDATE)
            self.review_action_permissions(actions, RecordCardStateMachine.canceled, user_perms, CANCEL)
            self.review_answer_action(actions)

            self.set_reasign_action(actions)
            self.review_action_permissions(actions, self.REASIGN_ACTION, user_perms, RECARD_REASIGN)
            if self.detail_mode:
                self.review_action_permissions(actions, RecordCardStateMachine.planified, user_perms, RECARD_PLAN_RESOL)
                self.review_action_permissions(actions, RecordCardStateMachine.resoluted, user_perms, RECARD_PLAN_RESOL)
                self.review_action_permissions(actions, RecordCardStateMachine.answer_action, user_perms, RECARD_ANSWER)
                self.check_theme_tree(actions)
                if self.record_card.record_state_id != RecordState.NO_PROCESSED:
                    self.set_add_conversation_action(actions)
                    self.set_block_action(actions)
                    self.set_draft_answer(actions)
                    self.set_toogle_urgency_action(actions)
                    self.set_upload_file_action(actions)
                    self.set_delete_file_action(actions)
                    self.set_update_applicant_action(actions)
                    self.set_add_multirecord_action(actions)
                    self.review_action_permissions(actions, self.MULTIRECORD_ACTION, user_perms, RECARD_MULTIRECORD)

                    #  set actions that depend on user permissions
                    self.set_update_action(actions, user_perms)
                    self.set_theme_change_action(actions, user_perms)
                    self.set_resend_answer_action(actions, user_perms)
                self.set_toogle_reasignable_action(actions, user_perms)
        if self.detail_mode:
            self.set_claim_action(actions)
            self.set_cancel_request(actions, user_perms)
            self.review_action_permissions(actions, self.CLAIM, user_perms, RECARD_CLAIM)
            if RecordCardStateMachine.applicant in transitions:
                if self.record_card.cant_set_applicant:
                    return {}
                else:
                    set_applicant_actions = {
                        RecordCardStateMachine.applicant: transitions.get(RecordCardStateMachine.applicant, {})
                    }
                    self.review_action_permissions(set_applicant_actions, RecordCardStateMachine.applicant, user_perms,
                                                   RESP_WILL_SOLVE)
                    return set_applicant_actions
            if self.is_creator:
                self.set_upload_file_action(actions)
        self.review_closed_states_allowed_actions(actions, user_perms)
        return actions

    @property
    def is_creator(self):
        return self.record_card.user_id == get_user_traceability_id(self.user)

    @property
    def generate_transitions(self):
        return self.detail_mode or self.record_card.record_state_id == RecordState.PENDING_VALIDATE

    def set_initial_actions(self):
        initial_actions = {}
        if self.can_tramit or self.can_response_messages:
            initial_actions[self.ADD_MESSAGE_ACTION] = {
                "action_url": reverse("private_api:communications:message_create"),
                "check_url": None, "can_perform": True, "action_method": "post"}

        initial_actions[self.ADD_COMMENT_ACTION] = {
            "action_url": reverse("private_api:record_cards:record_card_add_comment"),
            "check_url": None, "can_perform": True, "action_method": "post"}
        return initial_actions

    @property
    def can_response_messages(self):
        return GroupCanResponseMessages(self.record_card, self.user_group).can_response_messages()

    @staticmethod
    def review_action_permissions(actions, action, user_perms, permission):
        """
        If the action is in actions and user has no permission to do it, update the information

        :param actions: dict with record actions
        :param action: action to check
        :param user_perms: user permisions list
        :param permission: permission needed to the action
        :return:
        """
        if action in actions:
            if not user_perms.has_permission(permission):
                actions[action]["action_url"] = None
                actions[action]["can_perform"] = False
                actions[action]["has_permission"] = False
                actions[action]["reason"] = _("User has no permissions to do this action")
            else:
                actions[action]['has_permission'] = True

    def set_update_action(self, actions, user_perms):
        """
        Add update action to actions

        :param actions: dict with record actions
        :param user_perms: user permisions list
        :return:
        """
        action_url = reverse("private_api:record_cards:recordcard-detail",
                             kwargs={"reference": self.record_card.normalized_record_id})
        self.set_permission_action(actions, user_perms, UPDATE, action_url, self.UPDATE_ACTION, "patch")

    def set_toogle_reasignable_action(self, actions, user_perms):
        """
        Add toogle reasignable action to actions

        :param actions: dict with record actions
        :param user_perms: user permisions list
        :return:
        """
        action_url = reverse("private_api:record_cards:record_card_toggle_reassignable",
                             kwargs={"pk": self.record_card.pk})
        self.set_permission_action(actions, user_perms, NO_REASIGNABLE, action_url, "toogle-reasignable", "patch")

    def set_theme_change_action(self, actions, user_perms):
        """
        Add theme change action to actions

        :param actions: dict with record actions
        :param user_perms: user permisions list
        :return:
        """
        check_url = reverse("private_api:record_cards:record_card_theme_change_check",
                            kwargs={"pk": self.record_card.pk})
        if not self.record_card.is_validated or self.record_card.record_state_id == RecordState.CLOSED \
            or self.require_theme_change:
            action_url = reverse("private_api:record_cards:record_card_theme_change",
                                 kwargs={"pk": self.record_card.pk})
            actions.update({self.CHANGE_THEME_ACTION: {
                "check_url": check_url,
                "permission": THEME_CHANGE,
                "action_method": "post",
                "action_url": action_url,
                "can_perform": True,
                "reason": None
            }})
            if self.require_theme_change:
                actions[self.CHANGE_THEME_ACTION]["reason"] = _('Only can move to its own ambit themes.')
        else:
            actions.update({self.CHANGE_THEME_ACTION: {
                "check_url": check_url,
                "permission": THEME_CHANGE,
                "action_method": "post",
                "action_url": None,
                "can_perform": False,
                "reason": _("Cannot change theme on validated record cards.")
            }})
        self.review_action_permissions(actions, self.CHANGE_THEME_ACTION, user_perms, THEME_CHANGE)

    @staticmethod
    def set_permission_action(actions, user_perms, action_permission, action_url, action_name, action_method,
                              check_url=None):
        """
        Set an action depending of user permissions

        :param actions: dict with record actions
        :param user_perms: user permisions list
        :param action_permission: permission required for action
        :param action_url: url of the action
        :param action_name: action name
        :param action_method: action method
        :param check_url: check url of the action
        :return:
        """
        action = {
            "check_url": check_url if check_url else None,
            "permission": action_permission,
            "action_method": action_method,
        }
        if user_perms.has_permission(action_permission):
            action["action_url"] = action_url
            action["can_perform"] = True
        else:
            action["action_url"] = None
            action["can_perform"] = False
            action["reason"] = _("User has no permissions to do this action")
        actions.update({action_name: action})

    def set_cancel_request(self, actions, user_perms):
        """
        Add cancel request action to actions

        :param actions: dict with record actions
        :param user_perms: user permisions list
        :return:
        """
        action = {
            "check_url": None,
            "action_method": "post",
        }
        if self.record_card.record_state_id in RecordState.CLOSED_STATES:
            action["action_url"] = None
            action["can_perform"] = False
            action["reason"] = _("Action can not be done because the RecordCard is closed or cancelled.")
        else:
            if not user_perms.has_permission(CANCEL) or not self.can_tramit:
                action["action_url"] = reverse("private_api:record_cards:record_card_add_comment")
                action["can_perform"] = True
                action["reason_comment_id"] = Reason.RECORDCARD_CANCEL_REQUEST
            else:
                action["action_url"] = None
                action["can_perform"] = False
                action["reason"] = _("User has permissions to cancel the request")
        actions.update({"cancel-request": action})

    def set_add_conversation_action(self, actions):
        """
        Add "add convesation" action to actions. User will be able to do the action if it"s the responsible profile
        of the record

        :param actions: dict with record actions
        :return:
        """

        add_conversation = {"check_url": None, "action_method": "post"}
        if self.can_tramit:
            add_conversation["action_url"] = reverse("private_api:communications:message_create")
            add_conversation["can_perform"] = True
        else:
            add_conversation["action_url"] = None
            add_conversation["can_perform"] = False
            add_conversation["reason"] = _("User can not open a conversation because it's not the"
                                           " responsible profile of the record")
        actions.update({self.ADD_CONVERSATION_ACTION: add_conversation})

    def set_draft_answer(self, actions):
        """
        Add draft answer to actions

        :param actions: dict with record actions
        :return:
        """
        actions.update({"draft-answer": {"action_url": reverse("private_api:record_cards:record_card_draft_answer",
                                                               kwargs={"pk": self.record_card.pk}), "check_url": None,
                                         "can_perform": True, "action_method": "post"}})

    def set_block_action(self, actions):
        """
        Add toogle record block to actions

        :param actions: dict with record actions
        :return:
        """
        actions.update({self.BLOCK_ACTION: {"action_url": reverse("private_api:record_cards:record_card_toogle_block",
                                                                  kwargs={"pk": self.record_card.pk}),
                                            "check_url": None, "can_perform": True, "action_method": "post"}})

    def set_claim_action(self, actions):
        """
        Add claim action to actions

        :param actions: dict with record actions
        :return:
        """
        try:
            ClaimValidation(self.record_card).validate()
            claim_action = {
                "action_url": reverse("private_api:record_cards:record_card_claim",
                                      kwargs={"pk": self.record_card.pk}),
                "check_url": reverse("private_api:record_cards:record_card_claim_check",
                                     kwargs={"pk": self.record_card.pk}),
                "can_perform": True,
                "action_method": "post"
            }
        except RecordClaimException as claim_exception:
            claim_action = {
                "action_url": None,
                "check_url": reverse("private_api:record_cards:record_card_claim_check",
                                     kwargs={"pk": self.record_card.pk}),
                "can_perform": False,
                "reason": claim_exception.message,
                "action_method": "post"
            }

        return actions.update({self.CLAIM: claim_action})

    def set_reasign_action(self, actions):
        """
        Add reasign to actions

        :param actions: dict with record actions
        :return:
        """
        # We don't pass RECARD_REASSIGN_OUTSIDE permission since it must be transparent for the user
        # So it will be applied by not offering the options, but it won't show any reason message
        actions.update({self.REASIGN_ACTION: PossibleReassignations(
            record_card=self.record_card).reasign_action(self.user_group)})

    def set_toogle_urgency_action(self, actions):
        """
        Add toogle urgency to actions

        :param actions: dict with record actions
        :return:
        """
        actions.update({self.TOOGLE_URGENCY_ACTION: {
            "action_url": reverse("private_api:record_cards:record_card_toogle_urgency",
                                  kwargs={"pk": self.record_card.pk}),
            "check_url": None,
            "action_method": "patch",
            "can_perform": True
        }})

    def set_upload_file_action(self, actions):
        """
        Add updload file to actions

        :param actions: dict with record actions
        :return:
        """

        upload_file_action = {
            "check_url": None,
            "action_method": "put",
        }

        if GroupManageFiles(self.record_card, self.user_group, self.user).group_can_add_file():
            upload_file_action["action_url"] = reverse("private_api:record_cards:record_card_file_upload")
            upload_file_action["can_perform"] = True
        else:
            upload_file_action["action_url"] = None
            upload_file_action["can_perform"] = False
        actions.update({self.UPLOAD_FILE_ACTION: upload_file_action})

    def set_delete_file_action(self, actions):
        """
        Add delete file to actions

        :param actions: dict with record actions
        :return:
        """
        delete_file_action = {
            "check_url": None,
            "action_method": "delete",
        }
        if GroupManageFiles(self.record_card, self.user_group, self.user).group_can_delete_file():
            delete_file_action["action_url"] = reverse("private_api:record_cards:record_card_file_delete",
                                                       kwargs={"pk": self.record_card.pk})
            delete_file_action["can_perform"] = True
        else:
            delete_file_action["action_url"] = None
            delete_file_action["can_perform"] = False
        actions.update({"delete-file": delete_file_action})

    def set_update_applicant_action(self, actions):
        """
        Add update applicant file to actions

        :param actions: dict with record actions
        :return:
        """
        if not self.record_card.request.applicant:
            return
        actions.update({"update-applicant": {
            "action_url": reverse("private_api:record_cards:applicant-detail",
                                  kwargs={"pk": self.record_card.request.applicant.pk}),
            "check_url": None,
            "can_perform": True,
            "action_method": "patch"
        }})

    def set_add_multirecord_action(self, actions):
        """
        Add multirecord file to actions

        :param actions: dict with record actions
        :return:
        """
        actions.update({self.MULTIRECORD_ACTION: {
            "action_url": reverse("private_api:record_cards:recordcard-list"),
            "check_url": None,
            "can_perform": True,
            "action_method": "post"
        }})

    def set_resend_answer_action(self, actions, user_perms):
        """
        Resend record answer when closed.

        :param actions: dict with record actions
        :return:
        """
        has_answer = not hasattr(self.record_card, "recordcardresponse") \
                     or self.record_card.recordcardresponse.response_channel_id != ResponseChannel.NONE
        if self.record_card.record_state_id == RecordState.CLOSED and has_answer:
            actions.update({self.RESEND_ANSWER: {
                "action_url": reverse("private_api:record_cards:record_card_resend_answer", args=[self.record_card.pk]),
                "check_url": None,
                "can_perform": user_perms.has_permission(RECARD_ANSWER_RESEND),
                "action_method": "post",
                "permission": RECARD_ANSWER_RESEND,
            }})

    def review_answer_action(self, actions):
        """
        Check if user group can answer the record. If group can"t answer it, expose the reason

        :param actions: dict with record actions
        :return:
        """
        group_can_answer = self.record_card.group_can_answer(self.user_group)
        if RecordCardStateMachine.answer_action in actions and not group_can_answer["can_answer"]:
            actions[RecordCardStateMachine.answer_action]["action_url"] = None
            actions[RecordCardStateMachine.answer_action]["can_perform"] = False
            actions[RecordCardStateMachine.answer_action]["reason"] = group_can_answer["reason"]

    def review_closed_states_allowed_actions(self, actions, perms=None):
        if self.record_card.record_state_id == RecordState.CLOSED:
            closed_disallowed = self.closed_disallowed_actions
            # Action allowed with permission
            if perms and perms.has_permission(RECARD_CLOSED_FILES):
                closed_disallowed = [a for a in closed_disallowed if a != self.UPLOAD_FILE_ACTION]
            for disallowed_action in closed_disallowed:
                actions.pop(disallowed_action, None)
        elif self.record_card.record_state_id == RecordState.CANCELLED:
            for disallowed_action in self.cancelled_disallowed_actions:
                actions.pop(disallowed_action, None)

    def check_theme_tree(self, actions):
        """
        A user cannot resolve a record assigned to a theme outside its valid theme tree. Before resolving, they must
        change theme before
        """
        if not self.record_card.record_state_id == RecordState.IN_RESOLUTION:
            return
        if actions.get(RecordCardStateMachine.resoluted, {}).get('can_perform', False):
            # Check theme tree
            g_themes = GroupThemeTree(self.user_group)
            self.require_theme_change = not g_themes.is_group_record(self.record_card)
            actions[RecordCardStateMachine.resoluted].update({
                'must_change_theme': not g_themes.is_group_record(self.record_card)
            })
