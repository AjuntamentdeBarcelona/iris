import pytest

from iris_masters.models import RecordState, Process
from record_cards.record_actions.state_machine import RecordCardStateMachine as StateMachine
from record_cards.tests.utils import CreateRecordCardMixin


@pytest.mark.django_db
class TestStateMachine(CreateRecordCardMixin):

    @pytest.mark.parametrize('process_pk,expected_ideal_path,force_error', (
            (Process.CLOSED_DIRECTLY, [StateMachine.pending_validation, StateMachine.validated], False),
            (Process.DIRECT_EXTERNAL_PROCESSING,
             [StateMachine.pending_validation, StateMachine.validated, StateMachine.close], False),
            (Process.PLANING_RESOLUTION_RESPONSE,
             [StateMachine.pending_validation, StateMachine.validated, StateMachine.planified,
              StateMachine.resoluted, StateMachine.answer_action],
             False),
            (Process.RESOLUTION_RESPONSE,
             [StateMachine.pending_validation, StateMachine.validated, StateMachine.resoluted,
              StateMachine.answer_action],
             False),
            (Process.EVALUATION_RESOLUTION_RESPONSE,
             [StateMachine.pending_validation, StateMachine.validated, StateMachine.planified,
              StateMachine.resoluted, StateMachine.answer_action],
             False),
            (Process.RESPONSE,
             [StateMachine.pending_validation, StateMachine.validated, StateMachine.answer_action],
             False),
            (Process.EXTERNAL_PROCESSING,
             [StateMachine.pending_validation, StateMachine.validated, StateMachine.close], False),
            (Process.EXTERNAL_PROCESSING_EMAIL,
             [StateMachine.pending_validation, StateMachine.validated],
             False),
            (Process.RESOLUTION_EXTERNAL_PROCESSING,
             [StateMachine.pending_validation, StateMachine.validated, StateMachine.resoluted, StateMachine.close],
             False),
            (Process.RESOLUTION_EXTERNAL_PROCESSING_EMAIL,
             [StateMachine.pending_validation, StateMachine.validated, StateMachine.resoluted,
              StateMachine.close, StateMachine.answer_action], False),
            (Process.RESOLUTION_EXTERNAL_PROCESSING_EMAIL,
             [StateMachine.pending_validation, StateMachine.external_processed_email,
              StateMachine.pend_answered], True),
    ))
    def test_state_machine_ideal_path(self, process_pk, expected_ideal_path, force_error):
        record_card = self.create_record_card(process_pk=process_pk, record_state_id=RecordState.PENDING_VALIDATE)
        if not force_error:
            assert StateMachine(record_card).get_ideal_path() == expected_ideal_path
        else:
            assert StateMachine(record_card).get_ideal_path() != expected_ideal_path

    @pytest.mark.parametrize('process_pk,record_state_pk,current_step', (
            (Process.CLOSED_DIRECTLY, RecordState.PENDING_VALIDATE, StateMachine.pending_validation),
            (Process.CLOSED_DIRECTLY, RecordState.CLOSED, StateMachine.closed),
            (Process.CLOSED_DIRECTLY, RecordState.CANCELLED, StateMachine.canceled),

            (Process.DIRECT_EXTERNAL_PROCESSING, RecordState.PENDING_VALIDATE, StateMachine.pending_validation),
            (Process.DIRECT_EXTERNAL_PROCESSING, RecordState.EXTERNAL_PROCESSING, StateMachine.external_processed),
            (Process.DIRECT_EXTERNAL_PROCESSING, RecordState.EXTERNAL_RETURNED, StateMachine.returned),
            (Process.DIRECT_EXTERNAL_PROCESSING, RecordState.CLOSED, StateMachine.closed),
            (Process.DIRECT_EXTERNAL_PROCESSING, RecordState.CANCELLED, StateMachine.canceled),

            (Process.PLANING_RESOLUTION_RESPONSE, RecordState.PENDING_VALIDATE, StateMachine.pending_validation),
            (Process.PLANING_RESOLUTION_RESPONSE, RecordState.IN_PLANING, StateMachine.planified),
            (Process.PLANING_RESOLUTION_RESPONSE, RecordState.IN_RESOLUTION, StateMachine.resoluted),
            (Process.PLANING_RESOLUTION_RESPONSE, RecordState.PENDING_ANSWER, StateMachine.pend_answered),
            (Process.PLANING_RESOLUTION_RESPONSE, RecordState.CLOSED, StateMachine.closed),
            (Process.PLANING_RESOLUTION_RESPONSE, RecordState.CANCELLED, StateMachine.canceled),

            (Process.RESOLUTION_RESPONSE, RecordState.PENDING_VALIDATE, StateMachine.pending_validation),
            (Process.RESOLUTION_RESPONSE, RecordState.IN_RESOLUTION, StateMachine.resoluted),
            (Process.RESOLUTION_RESPONSE, RecordState.PENDING_ANSWER, StateMachine.pend_answered),
            (Process.RESOLUTION_RESPONSE, RecordState.CLOSED, StateMachine.closed),
            (Process.RESOLUTION_RESPONSE, RecordState.CANCELLED, StateMachine.canceled),

            (Process.EVALUATION_RESOLUTION_RESPONSE, RecordState.PENDING_VALIDATE, StateMachine.pending_validation),
            (Process.EVALUATION_RESOLUTION_RESPONSE, RecordState.IN_PLANING, StateMachine.planified),
            (Process.EVALUATION_RESOLUTION_RESPONSE, RecordState.IN_RESOLUTION, StateMachine.resoluted),
            (Process.EVALUATION_RESOLUTION_RESPONSE, RecordState.PENDING_ANSWER, StateMachine.pend_answered),
            (Process.EVALUATION_RESOLUTION_RESPONSE, RecordState.CLOSED, StateMachine.closed),
            (Process.EVALUATION_RESOLUTION_RESPONSE, RecordState.CANCELLED, StateMachine.canceled),

            (Process.RESPONSE, RecordState.PENDING_VALIDATE, StateMachine.pending_validation),
            (Process.RESPONSE, RecordState.PENDING_ANSWER, StateMachine.pend_answered),
            (Process.RESPONSE, RecordState.CLOSED, StateMachine.closed),
            (Process.RESPONSE, RecordState.CANCELLED, StateMachine.canceled),

            (Process.EXTERNAL_PROCESSING, RecordState.PENDING_VALIDATE, StateMachine.pending_validation),
            (Process.EXTERNAL_PROCESSING, RecordState.EXTERNAL_PROCESSING, StateMachine.external_processed),
            (Process.EXTERNAL_PROCESSING, RecordState.EXTERNAL_RETURNED, StateMachine.returned),
            (Process.EXTERNAL_PROCESSING, RecordState.CLOSED, StateMachine.closed),
            (Process.EXTERNAL_PROCESSING, RecordState.CANCELLED, StateMachine.canceled),

            (Process.EXTERNAL_PROCESSING_EMAIL, RecordState.PENDING_VALIDATE, StateMachine.pending_validation),
            (Process.EXTERNAL_PROCESSING_EMAIL, RecordState.EXTERNAL_PROCESSING, StateMachine.external_processed_email),
            (Process.EXTERNAL_PROCESSING_EMAIL, RecordState.CLOSED, StateMachine.closed),
            (Process.EXTERNAL_PROCESSING_EMAIL, RecordState.CANCELLED, StateMachine.canceled),

            (Process.RESOLUTION_EXTERNAL_PROCESSING, RecordState.PENDING_VALIDATE, StateMachine.pending_validation),
            (Process.RESOLUTION_EXTERNAL_PROCESSING, RecordState.IN_RESOLUTION, StateMachine.resoluted),
            (Process.RESOLUTION_EXTERNAL_PROCESSING, RecordState.EXTERNAL_PROCESSING, StateMachine.external_processed),
            (Process.RESOLUTION_EXTERNAL_PROCESSING, RecordState.EXTERNAL_RETURNED, StateMachine.returned),
            (Process.RESOLUTION_EXTERNAL_PROCESSING, RecordState.CLOSED, StateMachine.closed),
            (Process.RESOLUTION_EXTERNAL_PROCESSING, RecordState.CANCELLED, StateMachine.canceled),

            (Process.RESOLUTION_EXTERNAL_PROCESSING_EMAIL, RecordState.PENDING_VALIDATE,
             StateMachine.pending_validation),
            (Process.RESOLUTION_EXTERNAL_PROCESSING_EMAIL, RecordState.IN_RESOLUTION, StateMachine.resoluted),
            (Process.RESOLUTION_EXTERNAL_PROCESSING_EMAIL, RecordState.EXTERNAL_PROCESSING,
             StateMachine.external_processed_email),
            (Process.RESOLUTION_EXTERNAL_PROCESSING_EMAIL, RecordState.PENDING_ANSWER, StateMachine.pend_answered),
            (Process.RESOLUTION_EXTERNAL_PROCESSING_EMAIL, RecordState.EXTERNAL_RETURNED, StateMachine.returned),
            (Process.RESOLUTION_EXTERNAL_PROCESSING_EMAIL, RecordState.CLOSED, StateMachine.closed),
            (Process.RESOLUTION_EXTERNAL_PROCESSING_EMAIL, RecordState.CANCELLED, StateMachine.canceled),
    ))
    def test_current_step(self, process_pk, record_state_pk, current_step):
        record_card = self.create_record_card(process_pk=process_pk, record_state_id=record_state_pk)
        assert StateMachine(record_card).get_current_step() == current_step

    @pytest.mark.parametrize('process_pk,record_state_pk,actions_list', (
            (Process.CLOSED_DIRECTLY, RecordState.PENDING_VALIDATE, [StateMachine.validated, StateMachine.canceled]),
            (Process.CLOSED_DIRECTLY, RecordState.CLOSED, []),
            (Process.CLOSED_DIRECTLY, RecordState.CANCELLED, []),

            (Process.DIRECT_EXTERNAL_PROCESSING, RecordState.PENDING_VALIDATE,
             [StateMachine.validated, StateMachine.canceled]),
            (Process.DIRECT_EXTERNAL_PROCESSING, RecordState.EXTERNAL_PROCESSING,
             [StateMachine.returned, StateMachine.close]),
            (Process.DIRECT_EXTERNAL_PROCESSING, RecordState.EXTERNAL_RETURNED,
             [StateMachine.validated, StateMachine.canceled]),
            (Process.DIRECT_EXTERNAL_PROCESSING, RecordState.CLOSED, []),
            (Process.DIRECT_EXTERNAL_PROCESSING, RecordState.CANCELLED, []),

            (Process.PLANING_RESOLUTION_RESPONSE, RecordState.PENDING_VALIDATE,
             [StateMachine.validated, StateMachine.canceled]),
            (Process.PLANING_RESOLUTION_RESPONSE, RecordState.IN_PLANING,
             [StateMachine.planified, StateMachine.canceled]),
            (Process.PLANING_RESOLUTION_RESPONSE, RecordState.IN_RESOLUTION,
             [StateMachine.resoluted, StateMachine.canceled]),
            (Process.PLANING_RESOLUTION_RESPONSE, RecordState.PENDING_ANSWER,
             [StateMachine.answer_action, StateMachine.canceled]),
            (Process.PLANING_RESOLUTION_RESPONSE, RecordState.CLOSED, []),
            (Process.PLANING_RESOLUTION_RESPONSE, RecordState.CANCELLED, []),

            (Process.RESOLUTION_RESPONSE, RecordState.PENDING_VALIDATE,
             [StateMachine.validated, StateMachine.canceled]),
            (Process.RESOLUTION_RESPONSE, RecordState.IN_RESOLUTION, [StateMachine.resoluted, StateMachine.canceled]),
            (Process.RESOLUTION_RESPONSE, RecordState.PENDING_ANSWER,
             [StateMachine.answer_action, StateMachine.canceled]),
            (Process.RESOLUTION_RESPONSE, RecordState.CLOSED, []),
            (Process.RESOLUTION_RESPONSE, RecordState.CANCELLED, []),

            (Process.EVALUATION_RESOLUTION_RESPONSE, RecordState.PENDING_VALIDATE,
             [StateMachine.validated, StateMachine.canceled]),
            (Process.EVALUATION_RESOLUTION_RESPONSE, RecordState.IN_PLANING,
             [StateMachine.planified, StateMachine.canceled]),
            (Process.EVALUATION_RESOLUTION_RESPONSE, RecordState.IN_RESOLUTION,
             [StateMachine.resoluted, StateMachine.canceled]),
            (Process.EVALUATION_RESOLUTION_RESPONSE, RecordState.PENDING_ANSWER,
             [StateMachine.answer_action, StateMachine.canceled]),
            (Process.EVALUATION_RESOLUTION_RESPONSE, RecordState.CLOSED, []),
            (Process.EVALUATION_RESOLUTION_RESPONSE, RecordState.CANCELLED, []),

            (Process.RESPONSE, RecordState.PENDING_VALIDATE, [StateMachine.validated, StateMachine.canceled]),
            (Process.RESPONSE, RecordState.PENDING_ANSWER, [StateMachine.answer_action, StateMachine.canceled]),
            (Process.RESPONSE, RecordState.CLOSED, []),
            (Process.RESPONSE, RecordState.CANCELLED, []),

            (Process.EXTERNAL_PROCESSING, RecordState.PENDING_VALIDATE,
             [StateMachine.validated, StateMachine.canceled]),
            (Process.EXTERNAL_PROCESSING, RecordState.EXTERNAL_PROCESSING,
             [StateMachine.returned, StateMachine.close]),
            (Process.EXTERNAL_PROCESSING, RecordState.EXTERNAL_RETURNED,
             [StateMachine.validated, StateMachine.canceled]),
            (Process.EXTERNAL_PROCESSING, RecordState.CLOSED, []),
            (Process.EXTERNAL_PROCESSING, RecordState.CANCELLED, []),

            (Process.EXTERNAL_PROCESSING_EMAIL, RecordState.PENDING_VALIDATE,
             [StateMachine.validated, StateMachine.canceled]),
            (Process.EXTERNAL_PROCESSING_EMAIL, RecordState.CLOSED, []),
            (Process.EXTERNAL_PROCESSING_EMAIL, RecordState.CANCELLED, []),

            (Process.RESOLUTION_EXTERNAL_PROCESSING, RecordState.PENDING_VALIDATE,
             [StateMachine.validated, StateMachine.canceled]),
            (Process.RESOLUTION_EXTERNAL_PROCESSING, RecordState.IN_RESOLUTION,
             [StateMachine.resoluted, StateMachine.canceled]),
            (Process.RESOLUTION_EXTERNAL_PROCESSING, RecordState.EXTERNAL_PROCESSING,
             [StateMachine.returned, StateMachine.close]),
            (Process.RESOLUTION_EXTERNAL_PROCESSING, RecordState.EXTERNAL_RETURNED,
             [StateMachine.validated, StateMachine.canceled]),
            (Process.RESOLUTION_EXTERNAL_PROCESSING, RecordState.CLOSED, []),
            (Process.RESOLUTION_EXTERNAL_PROCESSING, RecordState.CANCELLED, []),

            (Process.RESOLUTION_EXTERNAL_PROCESSING_EMAIL, RecordState.PENDING_VALIDATE,
             [StateMachine.validated, StateMachine.canceled]),
            (Process.RESOLUTION_EXTERNAL_PROCESSING_EMAIL, RecordState.IN_RESOLUTION,
             [StateMachine.resoluted, StateMachine.canceled]),
            (Process.RESOLUTION_EXTERNAL_PROCESSING_EMAIL, RecordState.EXTERNAL_PROCESSING,
             [StateMachine.returned, StateMachine.close]),
            (Process.RESOLUTION_EXTERNAL_PROCESSING_EMAIL, RecordState.PENDING_ANSWER,
             [StateMachine.answer_action, StateMachine.canceled]),
            (Process.RESOLUTION_EXTERNAL_PROCESSING_EMAIL, RecordState.EXTERNAL_RETURNED,
             [StateMachine.validated, StateMachine.canceled]),
            (Process.RESOLUTION_EXTERNAL_PROCESSING_EMAIL, RecordState.CLOSED, []),
            (Process.RESOLUTION_EXTERNAL_PROCESSING_EMAIL, RecordState.CANCELLED, []),
    ))
    def test_transitions(self, process_pk, record_state_pk, actions_list):
        record_card = self.create_record_card(process_pk=process_pk, record_state_id=record_state_pk)
        assert list(StateMachine(record_card).get_transitions().keys()) == actions_list

    @pytest.mark.parametrize('process_pk,record_state_pk,next_record_state_pk', (
            (Process.CLOSED_DIRECTLY, RecordState.PENDING_VALIDATE, RecordState.CLOSED),
            (Process.CLOSED_DIRECTLY, RecordState.CLOSED, None),
            (Process.CLOSED_DIRECTLY, RecordState.CANCELLED, None),

            (Process.DIRECT_EXTERNAL_PROCESSING, RecordState.PENDING_VALIDATE, RecordState.EXTERNAL_PROCESSING),
            (Process.DIRECT_EXTERNAL_PROCESSING, RecordState.EXTERNAL_PROCESSING, RecordState.CLOSED),
            (Process.DIRECT_EXTERNAL_PROCESSING, RecordState.EXTERNAL_RETURNED, RecordState.EXTERNAL_PROCESSING),
            (Process.DIRECT_EXTERNAL_PROCESSING, RecordState.CLOSED, None),
            (Process.DIRECT_EXTERNAL_PROCESSING, RecordState.CANCELLED, None),

            (Process.PLANING_RESOLUTION_RESPONSE, RecordState.PENDING_VALIDATE, RecordState.IN_PLANING),
            (Process.PLANING_RESOLUTION_RESPONSE, RecordState.IN_PLANING, RecordState.IN_RESOLUTION),
            (Process.PLANING_RESOLUTION_RESPONSE, RecordState.IN_RESOLUTION, RecordState.PENDING_ANSWER),
            (Process.PLANING_RESOLUTION_RESPONSE, RecordState.PENDING_ANSWER, RecordState.CLOSED),
            (Process.PLANING_RESOLUTION_RESPONSE, RecordState.CLOSED, None),
            (Process.PLANING_RESOLUTION_RESPONSE, RecordState.CANCELLED, None),

            (Process.RESOLUTION_RESPONSE, RecordState.PENDING_VALIDATE, RecordState.IN_RESOLUTION),
            (Process.RESOLUTION_RESPONSE, RecordState.IN_RESOLUTION, RecordState.PENDING_ANSWER),
            (Process.RESOLUTION_RESPONSE, RecordState.PENDING_ANSWER, RecordState.CLOSED),
            (Process.RESOLUTION_RESPONSE, RecordState.CLOSED, None),
            (Process.RESOLUTION_RESPONSE, RecordState.CANCELLED, None),

            (Process.EVALUATION_RESOLUTION_RESPONSE, RecordState.PENDING_VALIDATE, RecordState.IN_PLANING),
            (Process.EVALUATION_RESOLUTION_RESPONSE, RecordState.IN_PLANING, RecordState.IN_RESOLUTION),
            (Process.EVALUATION_RESOLUTION_RESPONSE, RecordState.IN_RESOLUTION, RecordState.PENDING_ANSWER),
            (Process.EVALUATION_RESOLUTION_RESPONSE, RecordState.PENDING_ANSWER, RecordState.CLOSED),
            (Process.EVALUATION_RESOLUTION_RESPONSE, RecordState.CLOSED, None),
            (Process.EVALUATION_RESOLUTION_RESPONSE, RecordState.CANCELLED, None),

            (Process.RESPONSE, RecordState.PENDING_VALIDATE, RecordState.PENDING_ANSWER),
            (Process.RESPONSE, RecordState.PENDING_ANSWER, RecordState.CLOSED),
            (Process.RESPONSE, RecordState.CLOSED, None),
            (Process.RESPONSE, RecordState.CANCELLED, None),

            (Process.EXTERNAL_PROCESSING, RecordState.PENDING_VALIDATE, RecordState.EXTERNAL_PROCESSING),
            (Process.EXTERNAL_PROCESSING, RecordState.EXTERNAL_PROCESSING, RecordState.CLOSED),
            (Process.EXTERNAL_PROCESSING, RecordState.EXTERNAL_RETURNED, RecordState.EXTERNAL_PROCESSING),
            (Process.EXTERNAL_PROCESSING, RecordState.CLOSED, None),
            (Process.EXTERNAL_PROCESSING, RecordState.CANCELLED, None),

            (Process.EXTERNAL_PROCESSING_EMAIL, RecordState.PENDING_VALIDATE, RecordState.EXTERNAL_PROCESSING),
            (Process.EXTERNAL_PROCESSING_EMAIL, RecordState.CLOSED, None),
            (Process.EXTERNAL_PROCESSING_EMAIL, RecordState.CANCELLED, None),

            (Process.RESOLUTION_EXTERNAL_PROCESSING, RecordState.PENDING_VALIDATE, RecordState.IN_RESOLUTION),
            (Process.RESOLUTION_EXTERNAL_PROCESSING, RecordState.IN_RESOLUTION, RecordState.EXTERNAL_PROCESSING),
            (Process.RESOLUTION_EXTERNAL_PROCESSING, RecordState.EXTERNAL_PROCESSING, RecordState.CLOSED),
            (Process.RESOLUTION_EXTERNAL_PROCESSING, RecordState.EXTERNAL_RETURNED, RecordState.IN_RESOLUTION),
            (Process.RESOLUTION_EXTERNAL_PROCESSING, RecordState.CLOSED, None),
            (Process.RESOLUTION_EXTERNAL_PROCESSING, RecordState.CANCELLED, None),

            (Process.RESOLUTION_EXTERNAL_PROCESSING_EMAIL, RecordState.PENDING_VALIDATE, RecordState.IN_RESOLUTION),
            (Process.RESOLUTION_EXTERNAL_PROCESSING_EMAIL, RecordState.IN_RESOLUTION, RecordState.EXTERNAL_PROCESSING),
            (Process.RESOLUTION_EXTERNAL_PROCESSING_EMAIL, RecordState.EXTERNAL_PROCESSING, RecordState.PENDING_ANSWER),
            (Process.RESOLUTION_EXTERNAL_PROCESSING_EMAIL, RecordState.PENDING_ANSWER, RecordState.CLOSED),
            (Process.RESOLUTION_EXTERNAL_PROCESSING_EMAIL, RecordState.EXTERNAL_RETURNED, RecordState.IN_RESOLUTION),
            (Process.RESOLUTION_EXTERNAL_PROCESSING_EMAIL, RecordState.CLOSED, None),
            (Process.RESOLUTION_EXTERNAL_PROCESSING_EMAIL, RecordState.CANCELLED, None),
    ))
    def test_next_step_code(self, process_pk, record_state_pk, next_record_state_pk):
        record_card = self.create_record_card(process_pk=process_pk, record_state_id=record_state_pk)
        assert StateMachine(record_card).get_next_step_code() == next_record_state_pk

    @pytest.mark.parametrize('process_pk,next_state_pk,state_change_method', (
            (Process.CLOSED_DIRECTLY, RecordState.PENDING_VALIDATE, "change_state"),
            (Process.CLOSED_DIRECTLY, RecordState.CLOSED, "change_state"),
            (Process.CLOSED_DIRECTLY, RecordState.CANCELLED, "change_state"),

            (Process.DIRECT_EXTERNAL_PROCESSING, RecordState.PENDING_VALIDATE, "change_state"),
            (Process.DIRECT_EXTERNAL_PROCESSING, RecordState.EXTERNAL_PROCESSING, "change_state"),
            (Process.DIRECT_EXTERNAL_PROCESSING, RecordState.EXTERNAL_RETURNED, "change_state"),
            (Process.DIRECT_EXTERNAL_PROCESSING, RecordState.CLOSED, "change_state"),
            (Process.DIRECT_EXTERNAL_PROCESSING, RecordState.CANCELLED, "change_state"),

            (Process.PLANING_RESOLUTION_RESPONSE, RecordState.PENDING_VALIDATE, "change_state"),
            (Process.PLANING_RESOLUTION_RESPONSE, RecordState.IN_PLANING, "change_state"),
            (Process.PLANING_RESOLUTION_RESPONSE, RecordState.IN_RESOLUTION, "change_state"),
            (Process.PLANING_RESOLUTION_RESPONSE, RecordState.PENDING_ANSWER, "pending_answer_change_state"),
            (Process.PLANING_RESOLUTION_RESPONSE, RecordState.CLOSED, "change_state"),
            (Process.PLANING_RESOLUTION_RESPONSE, RecordState.CANCELLED, "change_state"),

            (Process.RESOLUTION_RESPONSE, RecordState.PENDING_VALIDATE, "change_state"),
            (Process.RESOLUTION_RESPONSE, RecordState.IN_RESOLUTION, "change_state"),
            (Process.RESOLUTION_RESPONSE, RecordState.PENDING_ANSWER, "pending_answer_change_state"),
            (Process.RESOLUTION_RESPONSE, RecordState.CLOSED, "change_state"),
            (Process.RESOLUTION_RESPONSE, RecordState.CANCELLED, "change_state"),

            (Process.EVALUATION_RESOLUTION_RESPONSE, RecordState.PENDING_VALIDATE, "change_state"),
            (Process.EVALUATION_RESOLUTION_RESPONSE, RecordState.IN_PLANING, "change_state"),
            (Process.EVALUATION_RESOLUTION_RESPONSE, RecordState.IN_RESOLUTION, "change_state"),
            (Process.EVALUATION_RESOLUTION_RESPONSE, RecordState.PENDING_ANSWER, "pending_answer_change_state"),
            (Process.EVALUATION_RESOLUTION_RESPONSE, RecordState.CLOSED, "change_state"),
            (Process.EVALUATION_RESOLUTION_RESPONSE, RecordState.CANCELLED, "change_state"),

            (Process.RESPONSE, RecordState.PENDING_VALIDATE, "change_state"),
            (Process.RESPONSE, RecordState.PENDING_ANSWER, "pending_answer_change_state"),
            (Process.RESPONSE, RecordState.CLOSED, "change_state"),
            (Process.RESPONSE, RecordState.CANCELLED, "change_state"),

            (Process.EXTERNAL_PROCESSING, RecordState.PENDING_VALIDATE, "change_state"),
            (Process.EXTERNAL_PROCESSING, RecordState.EXTERNAL_PROCESSING, "change_state"),
            (Process.EXTERNAL_PROCESSING, RecordState.EXTERNAL_RETURNED, "change_state"),
            (Process.EXTERNAL_PROCESSING, RecordState.CLOSED, "change_state"),
            (Process.EXTERNAL_PROCESSING, RecordState.CANCELLED, "change_state"),

            (Process.EXTERNAL_PROCESSING_EMAIL, RecordState.PENDING_VALIDATE, "change_state"),
            (Process.EXTERNAL_PROCESSING_EMAIL, RecordState.EXTERNAL_PROCESSING, "change_state"),
            (Process.EXTERNAL_PROCESSING_EMAIL, RecordState.CLOSED, "change_state"),
            (Process.EXTERNAL_PROCESSING_EMAIL, RecordState.CANCELLED, "change_state"),

            (Process.RESOLUTION_EXTERNAL_PROCESSING, RecordState.PENDING_VALIDATE, "change_state"),
            (Process.RESOLUTION_EXTERNAL_PROCESSING, RecordState.IN_RESOLUTION, "change_state"),
            (Process.RESOLUTION_EXTERNAL_PROCESSING, RecordState.EXTERNAL_PROCESSING, "change_state"),
            (Process.RESOLUTION_EXTERNAL_PROCESSING, RecordState.EXTERNAL_RETURNED, "change_state"),
            (Process.RESOLUTION_EXTERNAL_PROCESSING, RecordState.CLOSED, "change_state"),
            (Process.RESOLUTION_EXTERNAL_PROCESSING, RecordState.CANCELLED, "change_state"),

            (Process.RESOLUTION_EXTERNAL_PROCESSING_EMAIL, RecordState.PENDING_VALIDATE, "change_state"),
            (Process.RESOLUTION_EXTERNAL_PROCESSING_EMAIL, RecordState.IN_RESOLUTION, "change_state"),
            (Process.RESOLUTION_EXTERNAL_PROCESSING_EMAIL, RecordState.EXTERNAL_PROCESSING, "change_state"),
            (Process.RESOLUTION_EXTERNAL_PROCESSING_EMAIL, RecordState.PENDING_ANSWER, "pending_answer_change_state"),
            (Process.RESOLUTION_EXTERNAL_PROCESSING_EMAIL, RecordState.EXTERNAL_RETURNED, "change_state"),
            (Process.RESOLUTION_EXTERNAL_PROCESSING_EMAIL, RecordState.CLOSED, "change_state"),
            (Process.RESOLUTION_EXTERNAL_PROCESSING_EMAIL, RecordState.CANCELLED, "change_state"),
    ))
    def test_get_state_change_method(self, process_pk, next_state_pk, state_change_method):
        record_card = self.create_record_card(process_pk=process_pk)
        assert StateMachine(record_card).get_state_change_method(next_state_pk) == state_change_method
