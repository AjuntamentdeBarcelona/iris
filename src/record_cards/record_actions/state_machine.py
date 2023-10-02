from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from iris_masters.models import RecordState, Process
from profiles.permissions import IrisPermissionChecker
from record_cards import permissions as record_permissions


class DummyStateMachineRecord:

    def __init__(self):
        self.pk = 0
        self.workflow = self.DummyWorkflow()

    class DummyWorkflow:
        def __init__(self):
            self.pk = 0


class RecordCardStateMachine:

    pending_validation = "pending_validate"
    validated = "validate"
    planified = "planifying"
    canceled = "cancel"
    applicant = "set_applicant"
    closed = "closed"
    close = "close"
    returned = "return"
    external_processed = "external_processing"
    external_processed_email = "external_processing_email"
    resoluted = "resolute"
    pend_answered = "pending_answer"
    answer_action = "answer"

    def __init__(self, record_card=None) -> None:
        self.record_card = record_card or DummyStateMachineRecord()
        super().__init__()

    def reverse(self, name, pk):
        pk = 0 if isinstance(self.record_card, DummyStateMachineRecord) else pk
        url = reverse(name, kwargs={"pk": pk})
        return url.replace("0", "{pk}") if pk == 0 else url

    def validate(self, is_next=False) -> dict:
        return {
            "action": self.validated,
            "permission": record_permissions.VALIDATE,
            "verbose_name": _(u"Validate Record Card"),
            "action_url": self.reverse("private_api:record_cards:record_card_validate", self.record_card.pk),
            "check_url": self. reverse("private_api:record_cards:record_card_validate_check", self.record_card.pk),
            "is_next": True if is_next else False,
            "can_perform": True
        }

    def cancel(self, is_next=False) -> dict:
        return {
            "action": self.canceled,
            "permission": record_permissions.CANCEL,
            "verbose_name": _(u"Cancel Record Card"),
            "action_url": self.reverse("private_api:record_cards:record_card_cancel", self.record_card.pk),
            "is_next": True if is_next else False,
            "can_perform": True
        }

    def set_applicant(self, is_next=False) -> dict:
        return {
            "action": self.applicant,
            "permission": record_permissions.RESP_WILL_SOLVE,
            "verbose_name": _(u"Attach applicant"),
            "action_url": self.reverse("private_api:record_cards:record_card_will_solve", self.record_card.pk),
            "is_next": True if is_next else False,
            "can_perform": True
        }

    def answer(self, is_next=False) -> dict:
        return {
            "action": self.answer_action,
            "verbose_name": _(u"Answer Record Card"),
            "action_url": self.reverse("private_api:record_cards:record_card_answer", self.record_card.pk),
            "is_next": True if is_next else False,
            "can_perform": True
        }

    def plan(self, is_next=False) -> dict:
        return {
            "action": self.planified,
            "permission": record_permissions.RECARD_PLAN_RESOL,
            "verbose_name": _(u"Planify Record Card"),
            "action_url": self.reverse("private_api:record_cards:workflow_plan",
                                       self.record_card.workflow.pk) if self.record_card.workflow else "",
            "check_url": self.reverse("private_api:record_cards:workflow_plan_check",
                                      self.record_card.workflow.pk) if self.record_card.workflow else "",
            "is_next": True if is_next else False,
            "workflow": True,
            "can_perform": True,
        }

    def resolute(self, is_next=False) -> dict:
        return {
            "action": self.resoluted,
            "permission": record_permissions.RECARD_PLAN_RESOL,
            "verbose_name": _(u"Record Card Resolution"),
            "action_url": self.reverse("private_api:record_cards:workflow_resolute",
                                       self.record_card.workflow.pk) if self.record_card.workflow else "",
            "check_url": self.reverse("private_api:record_cards:workflow_resolute_check",
                                      self.record_card.workflow.pk) if self.record_card.workflow else "",
            "is_next": True if is_next else False,
            "workflow": True,
            "can_perform": True,
        }

    def external_returned(self, is_next=False) -> dict:
        return {
            "action": self.returned,
            "verbose_name": _(u"External Returned Record Card"),
            "action_url": self.reverse("private_api:public_external_processing:public_external_return",
                                       self.record_card.pk),
            "is_next": True if is_next else False,
            "can_perform": True
        }

    def external_close(self, is_next=False) -> dict:
        return {
            "action": self.close,
            "verbose_name": _(u"External Close Record Card"),
            "action_url": self.reverse("private_api:public_external_processing:public_external_close",
                                       self.record_card.pk),
            "is_next": True if is_next else False,
            "can_perform": True
        }

    def external_cancel(self, is_next=False) -> dict:
        return {
            "action": self.canceled,
            "verbose_name": _(u"External Cancel Record Card"),
            "action_url": self.reverse("private_api:public_external_processing:public_external_cancel",
                                       self.record_card.pk),
            "is_next": True if is_next else False,
            "can_perform": True
        }

    def get_not_tramit_state(self):
        return {
            "initial": False,
            "state": self.pending_validation,
            "get_state_change_method": "change_state",
            "transitions": {
                RecordState.CANCELLED: self.cancel(),
                RecordState.PENDING_VALIDATE: self.set_applicant(is_next=True)
            }
        }

    def state_machine(self) -> dict:
        return {
            Process.CLOSED_DIRECTLY: {
                RecordState.NO_PROCESSED: self.get_not_tramit_state(),
                RecordState.PENDING_VALIDATE: {
                    "initial": True,
                    "state": self.pending_validation,
                    "get_state_change_method": "change_state",
                    "transitions": {
                        RecordState.CLOSED:  self.validate(is_next=True),
                        RecordState.CANCELLED: self.cancel()
                    }
                },
                RecordState.CANCELLED: {"state": self.canceled, "get_state_change_method": "change_state"},
                RecordState.CLOSED: {"state": self.closed, "get_state_change_method": "change_state"}
            },

            Process.DIRECT_EXTERNAL_PROCESSING: {
                # TODO: review with Process.EXTERNAL_PROCESSING
                RecordState.NO_PROCESSED: self.get_not_tramit_state(),
                RecordState.PENDING_VALIDATE: {
                    "initial": True,
                    "state": self.pending_validation,
                    "get_state_change_method": "change_state",
                    "transitions": {
                        RecordState.EXTERNAL_PROCESSING: self.validate(is_next=True),
                        RecordState.CANCELLED: self.cancel()
                    }
                },
                RecordState.EXTERNAL_PROCESSING: {
                    "state": self.external_processed,
                    "get_state_change_method": "change_state",
                    "transitions": {
                        RecordState.EXTERNAL_RETURNED: self.external_returned(),
                        RecordState.CLOSED: self.external_close(is_next=True),
                    }
                },
                RecordState.EXTERNAL_RETURNED: {
                    "state": self.returned,
                    "get_state_change_method": "change_state",
                    "transitions": {
                        RecordState.EXTERNAL_PROCESSING: self.validate(is_next=True),
                        RecordState.CANCELLED: self.cancel()
                    }
                },
                RecordState.CANCELLED: {"state": self.canceled, "get_state_change_method": "change_state"},
                RecordState.CLOSED: {"state": self.closed, "get_state_change_method": "change_state"}
            },

            Process.PLANING_RESOLUTION_RESPONSE: {
                RecordState.NO_PROCESSED: self.get_not_tramit_state(),
                RecordState.PENDING_VALIDATE: {
                    "initial": True,
                    "state": self.pending_validation,
                    "get_state_change_method": "change_state",
                    "transitions": {
                        RecordState.IN_PLANING: self.validate(is_next=True),
                        RecordState.CANCELLED: self.cancel()
                    }
                },
                RecordState.IN_PLANING: {
                    "state": self.planified,
                    "get_state_change_method": "change_state",
                    "transitions": {
                        RecordState.IN_RESOLUTION: self.plan(is_next=True),
                        RecordState.CANCELLED: self.cancel()
                    }
                },
                RecordState.IN_RESOLUTION: {
                    "state": self.resoluted,
                    "get_state_change_method": "change_state",
                    "transitions": {
                        RecordState.PENDING_ANSWER: self.resolute(is_next=True),
                        RecordState.CANCELLED: self.cancel()
                    }
                },
                RecordState.PENDING_ANSWER: {
                    "state": self.pend_answered,
                    "get_state_change_method": "pending_answer_change_state",
                    "transitions": {
                        RecordState.CLOSED: self.answer(is_next=True),
                        RecordState.CANCELLED: self.cancel()
                    }
                },
                RecordState.CANCELLED: {"state": self.canceled, "get_state_change_method": "change_state"},
                RecordState.CLOSED: {"state": self.closed, "get_state_change_method": "change_state"}
            },

            Process.RESOLUTION_RESPONSE: {
                RecordState.NO_PROCESSED: self.get_not_tramit_state(),
                RecordState.PENDING_VALIDATE: {
                    "initial": True,
                    "state": self.pending_validation,
                    "get_state_change_method": "change_state",
                    "transitions": {
                        RecordState.IN_RESOLUTION: self.validate(is_next=True),
                        RecordState.CANCELLED: self.cancel(),
                    }
                },
                RecordState.IN_RESOLUTION: {
                    "state": self.resoluted,
                    "get_state_change_method": "change_state",
                    "transitions": {
                        RecordState.PENDING_ANSWER: self.resolute(is_next=True),
                        RecordState.CANCELLED: self.cancel(),
                    }
                },
                RecordState.PENDING_ANSWER: {
                    "state": self.pend_answered,
                    "get_state_change_method": "pending_answer_change_state",
                    "transitions": {
                        RecordState.CLOSED: self.answer(is_next=True),
                        RecordState.CANCELLED: self.cancel()

                    }
                },
                RecordState.CANCELLED: {"state": self.canceled, "get_state_change_method": "change_state"},
                RecordState.CLOSED: {"state": self.closed, "get_state_change_method": "change_state"}
            },

            Process.EVALUATION_RESOLUTION_RESPONSE: {
                RecordState.NO_PROCESSED: self.get_not_tramit_state(),
                RecordState.PENDING_VALIDATE: {
                    "initial": True,
                    "state": self.pending_validation,
                    "get_state_change_method": "change_state",
                    "transitions": {
                        RecordState.IN_PLANING: self.validate(is_next=True),
                        RecordState.CANCELLED: self.cancel()
                    }
                },
                RecordState.IN_PLANING: {
                    "state": self.planified,
                    "get_state_change_method": "change_state",
                    "transitions": {
                        RecordState.IN_RESOLUTION: self.plan(is_next=True),
                        RecordState.CANCELLED: self.cancel()
                    }
                },
                RecordState.IN_RESOLUTION: {
                    "state": self.resoluted,
                    "get_state_change_method": "change_state",
                    "transitions": {
                        RecordState.PENDING_ANSWER: self.resolute(is_next=True),
                        RecordState.CANCELLED: self.cancel()
                    }
                },
                RecordState.PENDING_ANSWER: {
                    "state": self.pend_answered,
                    "get_state_change_method": "pending_answer_change_state",
                    "transitions": {
                        RecordState.CLOSED: self.answer(is_next=True),
                        RecordState.CANCELLED: self.cancel()
                    }
                },
                RecordState.CANCELLED: {"state": self.canceled, "get_state_change_method": "change_state"},
                RecordState.CLOSED: {"state": self.closed, "get_state_change_method": "change_state"}
            },

            Process.RESPONSE: {
                RecordState.NO_PROCESSED: self.get_not_tramit_state(),
                RecordState.PENDING_VALIDATE: {
                    "initial": True,
                    "state": self.pending_validation,
                    "get_state_change_method": "change_state",
                    "transitions": {
                        RecordState.PENDING_ANSWER: self.validate(is_next=True),
                        RecordState.CANCELLED: self.cancel(),
                    }
                },
                RecordState.PENDING_ANSWER: {
                    "state": self.pend_answered,
                    "get_state_change_method": "pending_answer_change_state",
                    "transitions": {
                        RecordState.CLOSED: self.answer(is_next=True),
                        RecordState.CANCELLED: self.cancel()
                    }
                },
                RecordState.CANCELLED: {"state": self.canceled, "get_state_change_method": "change_state"},
                RecordState.CLOSED: {"state": self.closed, "get_state_change_method": "change_state"}
            },

            Process.EXTERNAL_PROCESSING: {
                RecordState.NO_PROCESSED: self.get_not_tramit_state(),
                # TODO: review with Process.DIRECT_EXTERNAL_PROCESSING
                RecordState.PENDING_VALIDATE: {
                    "initial": True,
                    "state": self.pending_validation,
                    "get_state_change_method": "change_state",
                    "transitions": {
                        RecordState.EXTERNAL_PROCESSING: self.validate(is_next=True),
                        RecordState.CANCELLED: self.cancel()
                    }
                },
                RecordState.EXTERNAL_PROCESSING: {
                    "state": self.external_processed,
                    "get_state_change_method": "change_state",
                    "transitions": {
                        RecordState.EXTERNAL_RETURNED: self.external_returned(),
                        RecordState.CLOSED: self.external_close(is_next=True),
                    }
                },
                RecordState.EXTERNAL_RETURNED: {
                    "state": self.returned,
                    "get_state_change_method": "change_state",
                    "transitions": {
                        RecordState.EXTERNAL_PROCESSING: self.validate(is_next=True),
                        RecordState.CANCELLED: self.cancel()
                    }
                },
                RecordState.CANCELLED: {"state": self.canceled, "get_state_change_method": "change_state"},
                RecordState.CLOSED: {"state": self.closed, "get_state_change_method": "change_state"}
            },

            Process.EXTERNAL_PROCESSING_EMAIL: {
                RecordState.NO_PROCESSED: self.get_not_tramit_state(),
                RecordState.PENDING_VALIDATE: {
                    "initial": True,
                    "state": self.pending_validation,
                    "get_state_change_method": "change_state",
                    "transitions": {
                        RecordState.EXTERNAL_PROCESSING: self.validate(is_next=True),
                        RecordState.CANCELLED: self.cancel()
                    }
                },
                RecordState.EXTERNAL_PROCESSING: {
                    "state": self.external_processed_email,
                    "get_state_change_method": "change_state",
                    "transitions": {
                        RecordState.EXTERNAL_RETURNED: self.external_returned(),
                        RecordState.CLOSED: self.external_close(),
                    }
                },
                RecordState.EXTERNAL_RETURNED: {
                    "state": self.returned,
                    "get_state_change_method": "change_state",
                    "transitions": {
                        RecordState.EXTERNAL_PROCESSING: self.validate(),
                        RecordState.CANCELLED: self.cancel()
                    }
                },
                RecordState.CANCELLED: {"state": self.canceled, "get_state_change_method": "change_state"},
                RecordState.CLOSED: {"state": self.closed, "get_state_change_method": "change_state"}
            },

            Process.RESOLUTION_EXTERNAL_PROCESSING: {
                RecordState.NO_PROCESSED: self.get_not_tramit_state(),
                RecordState.PENDING_VALIDATE: {
                    "initial": True,
                    "state": self.pending_validation,
                    "get_state_change_method": "change_state",
                    "transitions": {
                        RecordState.IN_RESOLUTION: self.validate(is_next=True),
                        RecordState.CANCELLED: self.cancel(),
                    }
                },
                RecordState.IN_RESOLUTION: {
                    "state": self.resoluted,
                    "get_state_change_method": "change_state",
                    "transitions": {
                        RecordState.EXTERNAL_PROCESSING: self.resolute(is_next=True),
                        RecordState.CANCELLED: self.cancel(),
                    }
                },
                RecordState.EXTERNAL_PROCESSING: {
                    "state": self.external_processed,
                    "get_state_change_method": "change_state",
                    "transitions": {
                        RecordState.EXTERNAL_RETURNED: self.external_returned(),
                        RecordState.CLOSED: self.external_close(is_next=True),
                    }
                },
                RecordState.EXTERNAL_RETURNED: {
                    "state": self.returned,
                    "get_state_change_method": "change_state",
                    "transitions": {
                        RecordState.IN_RESOLUTION: self.validate(is_next=True),
                        RecordState.CANCELLED: self.cancel()
                    }
                },
                RecordState.CANCELLED: {"state": self.canceled, "get_state_change_method": "change_state"},
                RecordState.CLOSED: {"state": self.closed, "get_state_change_method": "change_state"}
            },

            Process.RESOLUTION_EXTERNAL_PROCESSING_EMAIL: {
                RecordState.NO_PROCESSED: self.get_not_tramit_state(),
                RecordState.PENDING_VALIDATE: {
                    "initial": True,
                    "state": self.pending_validation,
                    "get_state_change_method": "change_state",
                    "transitions": {
                        RecordState.IN_RESOLUTION: self.validate(is_next=True),
                        RecordState.CANCELLED: self.cancel()
                    }
                },
                RecordState.IN_RESOLUTION: {
                    "state": self.resoluted,
                    "get_state_change_method": "change_state",
                    "transitions": {
                        RecordState.EXTERNAL_PROCESSING: self.resolute(is_next=True),
                        RecordState.CANCELLED: self.cancel()
                    }
                },
                RecordState.EXTERNAL_PROCESSING: {
                    "state": self.external_processed_email,
                    "get_state_change_method": "change_state",
                    "transitions": {
                        RecordState.EXTERNAL_RETURNED: self.external_returned(),
                        RecordState.PENDING_ANSWER: self.external_close(is_next=True),
                    }
                },
                RecordState.PENDING_ANSWER: {
                    "state": self.pend_answered,
                    "get_state_change_method": "pending_answer_change_state",
                    "transitions": {
                        RecordState.CLOSED: self.answer(is_next=True),
                        RecordState.CANCELLED: self.cancel()
                    }
                },
                RecordState.EXTERNAL_RETURNED: {
                    "state": self.returned,
                    "get_state_change_method": "change_state",
                    "transitions": {
                        RecordState.IN_RESOLUTION: self.validate(is_next=True),
                        RecordState.CANCELLED: self.cancel()
                    }
                },
                RecordState.CANCELLED: {"state": self.canceled, "get_state_change_method": "change_state"},
                RecordState.CLOSED: {"state": self.closed, "get_state_change_method": "change_state"}
            }
        }

    def get_transitions(self) -> dict:
        transitions = {}
        if not self.record_card.process_id:
            return transitions
        current_state = self.state_machine()[self.record_card.process_id][self.record_card.record_state_id]
        if "transitions" not in current_state:
            return transitions

        for state, transition in current_state["transitions"].items():
            transitions[transition["action"]] = {
                "action_url": transition.get("action_url"),
                "check_url": transition.get("check_url"),
                "permission": transition.get("permission"),
                "can_perform": transition.get("can_perform")
            }

        return transitions

    def get_transitions_for_user(self, user) -> dict:
        transitions = self.get_transitions()
        perms = IrisPermissionChecker.get_for_user(user)
        return {
            key: transition for key, transition in transitions.items()
            if "permission" not in transition or perms.has_permission(transition["permission"])
        }

    def get_ideal_path(self) -> list:
        states_steps = self.state_machine()[self.record_card.process_id]

        state = None
        ideal_path = []

        for state_code, state_step in states_steps.items():
            if state_step.get('initial'):
                state = state_code
                ideal_path.append(state_step["state"])
                break

        if state is None:
            raise Exception("State Machine has no initial step for process {}".format(self.record_card.process_id))

        while "transitions" in states_steps[state]:
            old_state = state
            transitions = states_steps[state]["transitions"]
            for state_code, action in transitions.items():
                if action["is_next"]:
                    state = state_code
                    ideal_path.append(action["action"])
                    break
            if state == old_state:
                break
        return ideal_path

    def get_current_step(self) -> str:
        return self.state_machine()[self.record_card.process_id][self.record_card.record_state_id]["state"]

    def get_next_step_code(self) -> int or None:
        states = self.state_machine()[self.record_card.process_id][self.record_card.record_state_id]
        if "transitions" in states:
            for state_code, action in states["transitions"].items():
                if action["is_next"]:
                    return state_code

    def get_state_change_method(self, next_state_id) -> str:
        """
        Return the record card method to register the state change

        :param next_state_id: Next state of record card id
        :return:
        """
        return self.state_machine()[self.record_card.process_id][next_state_id]["get_state_change_method"]

    @staticmethod
    def get_plan_process_states() -> list:
        return [(Process.PLANING_RESOLUTION_RESPONSE, RecordState.IN_RESOLUTION),
                (Process.EVALUATION_RESOLUTION_RESPONSE, RecordState.IN_RESOLUTION)]

    @staticmethod
    def get_resolute_process_states() -> list:
        return [(Process.PLANING_RESOLUTION_RESPONSE, RecordState.PENDING_ANSWER),
                (Process.RESOLUTION_RESPONSE, RecordState.PENDING_ANSWER),
                (Process.EVALUATION_RESOLUTION_RESPONSE, RecordState.PENDING_ANSWER),
                (Process.RESOLUTION_EXTERNAL_PROCESSING, RecordState.EXTERNAL_PROCESSING),
                (Process.RESOLUTION_EXTERNAL_PROCESSING_EMAIL, RecordState.EXTERNAL_PROCESSING)]
