from datetime import timedelta

import pytest
from django.utils import timezone
from model_mommy import mommy

from iris_masters.models import RecordState, ResolutionType, Parameter, Process, RecordType
from record_cards.models import WorkflowResolution, RecordCardStateHistory, Citizen, Applicant
from record_cards.record_actions.claim_validate import ClaimValidation
from record_cards.record_actions.exceptions import RecordClaimException
from record_cards.tests.utils import CreateRecordCardMixin
from themes.models import ElementDetail


@pytest.mark.django_db
class TestClaimValidation(CreateRecordCardMixin):

    @pytest.mark.parametrize("record_state_id,raise_exception", (
            (RecordState.PENDING_VALIDATE, True),
            (RecordState.IN_RESOLUTION, True),
            (RecordState.CANCELLED, False),
            (RecordState.CLOSED, False)
    ))
    def test_record_not_in_closed_states(self, record_state_id, raise_exception):
        record_card = self.create_record_card(record_state_id=record_state_id)
        try:
            ClaimValidation(record_card).record_not_in_closed_states()
            assert raise_exception is False
        except Exception as e:
            assert raise_exception is True
            assert isinstance(e, RecordClaimException)
            assert e.must_be_comment is True

    @pytest.mark.parametrize("previuos_claim,raise_exception", (
            (True, True),
            (False, False)
    ))
    def test_exists_ongoing_claim(self, previuos_claim, raise_exception):
        record_card = self.create_record_card(claims_number=1 if previuos_claim else 0)
        if previuos_claim:
            self.create_record_card(claimed_from_id=record_card.pk,
                                    normalized_record_id=record_card.normalized_record_id + '02',
                                    claims_number=2)
        try:
            ClaimValidation(record_card).exists_ongoing_claim()
            assert raise_exception is False
        except Exception as e:
            assert raise_exception is True
            assert isinstance(e, RecordClaimException)
            assert e.must_be_comment is False

    @pytest.mark.parametrize("claim_limit_exceded,next_state_id,raise_exception", (
            (True, RecordState.CLOSED, True),
            (True, RecordState.PENDING_VALIDATE, False),
            (False, RecordState.CLOSED, False),
            (False, RecordState.PENDING_VALIDATE, False),
    ))
    def test_claim_limit_date_not_overcome(self, claim_limit_exceded, next_state_id, raise_exception):
        record_card = self.create_record_card()
        if claim_limit_exceded:
            RecordCardStateHistory.objects.create(record_card=record_card, group=record_card.responsible_profile,
                                                  previous_state_id=RecordState.PENDING_VALIDATE,
                                                  next_state_id=next_state_id, user_id='22222', automatic=False)
            claim_days_limit = int(Parameter.get_parameter_by_key('DIES_PER_RECLAMAR', 60))
            RecordCardStateHistory.objects.filter(next_state__in=RecordState.CLOSED_STATES,
                                                  record_card_id=record_card.pk).update(
                created_at=timezone.now() - timedelta(days=claim_days_limit))
        try:
            ClaimValidation(record_card).claim_limit_date_not_overcome()
            assert raise_exception is False
        except Exception as e:
            assert raise_exception is True
            assert isinstance(e, RecordClaimException)
            assert e.must_be_comment is False

    @pytest.mark.parametrize("applicant_blocked,allowed_theme,raise_exception", (
            (True, False, True),
            (False, False, False),
            (True, True, False),
            (False, True, False)
    ))
    def test_applicant_blocked(self, applicant_blocked, allowed_theme, raise_exception):
        citizen = mommy.make(Citizen, blocked=applicant_blocked, user_id='2222')
        applicant = mommy.make(Applicant, citizen=citizen, user_id='2222')
        if allowed_theme:
            element = self.create_element()
            no_block_theme_pk = int(Parameter.get_parameter_by_key("TEMATICA_NO_BLOQUEJADA", 392))
            element_detail = mommy.make(ElementDetail, user_id="22222", pk=no_block_theme_pk, element=element,
                                        process_id=Process.CLOSED_DIRECTLY,
                                        record_type_id=mommy.make(RecordType, user_id="user_id").pk)
        else:
            element_detail = self.create_element_detail()
        record_card = self.create_record_card(applicant=applicant, element_detail=element_detail)

        try:
            ClaimValidation(record_card).applicant_blocked()
            assert raise_exception is False
        except Exception as e:
            assert raise_exception is True
            assert isinstance(e, RecordClaimException)
            assert e.must_be_comment is False

    def test_ans_date_limit_overcome(self):
        resolution_type_id = ResolutionType.PROGRAM_ACTION
        resolution_type, _ = ResolutionType.objects.get_or_create(id=resolution_type_id)
        ans_limit_delta = -24 * 365
        record_card = self.create_record_card(record_state_id=RecordState.CLOSED, ans_limit_delta=ans_limit_delta,
                                              create_worflow=True)
        WorkflowResolution.objects.create(workflow=record_card.workflow, resolution_type_id=resolution_type_id)

        assert ClaimValidation(record_card).ans_date_limit_not_overcome() is None

    def test_ans_date_limit_can_claim_inside_ans(self):
        resolution_type_id = ResolutionType.PROGRAM_ACTION
        resolution_type, _ = ResolutionType.objects.get_or_create(id=resolution_type_id)

        record_card = self.create_record_card(record_state_id=RecordState.CLOSED, create_worflow=True)
        record_card.element_detail.sla_allows_claims = True
        record_card.element_detail.save()
        WorkflowResolution.objects.create(workflow=record_card.workflow, resolution_type_id=resolution_type_id)

        assert ClaimValidation(record_card).ans_date_limit_not_overcome() is None

    def test_ans_date_limit_not_overcome_raise_record_claim_exception(self):
        record_card = self.create_record_card(record_state_id=RecordState.CLOSED, create_worflow=True)
        resolution_type_id = mommy.make(ResolutionType, user_id='222', can_claim_inside_ans=True).pk
        WorkflowResolution.objects.create(workflow=record_card.workflow, resolution_type_id=resolution_type_id)

        try:
            ClaimValidation(record_card).ans_date_limit_not_overcome()
        except Exception as e:
            assert isinstance(e, RecordClaimException)
            assert e.must_be_comment is True

    @pytest.mark.parametrize(
        'initial_state,exists_previous_claim,claim_limit_exceded,applicant_blocked,resolution_type_id,ans_limit_delta,'
        'raise_exception,must_be_comment', (
                (RecordState.CLOSED, False, False, False, None, None, False, False),
                (RecordState.CANCELLED, False, False, False, None, None, False, False),
                (RecordState.PENDING_VALIDATE, False, False, False, None, None, True, True),
                (RecordState.CLOSED, True, False, False, None, None, True, False),
                (RecordState.CLOSED, False, True, False, None, None, True, False),
                (RecordState.CLOSED, False, False, True, None, None, True, False),
                (RecordState.CLOSED, False, False, False, ResolutionType.PROGRAM_ACTION, True, False, False),
                (RecordState.CLOSED, False, False, False, ResolutionType.PROGRAM_ACTION, None, True, True),
        ))
    def test_claim_validate(self, initial_state, exists_previous_claim, claim_limit_exceded, applicant_blocked,
                            resolution_type_id, ans_limit_delta, raise_exception, must_be_comment):
        if not ResolutionType.objects.filter(id=ResolutionType.PROGRAM_ACTION):
            resolution_type = ResolutionType(id=ResolutionType.PROGRAM_ACTION)
            resolution_type.save()

        citizen = mommy.make(Citizen, blocked=applicant_blocked, user_id='2222')
        applicant = mommy.make(Applicant, citizen=citizen, user_id='2222')

        if ans_limit_delta:
            ans_limit_delta = -24 * 365

        record_card = self.create_record_card(record_state_id=initial_state, applicant=applicant, create_worflow=True,
                                              ans_limit_delta=ans_limit_delta,
                                              claims_number=1 if exists_previous_claim else 0)

        if not resolution_type_id:
            resolution_type_id = mommy.make(ResolutionType, user_id='222', can_claim_inside_ans=True).pk

        WorkflowResolution.objects.create(workflow=record_card.workflow, resolution_type_id=resolution_type_id)

        if exists_previous_claim:
            self.create_record_card(claimed_from_id=record_card.pk,
                                    normalized_record_id=record_card.normalized_record_id + '-02')

        if claim_limit_exceded:
            RecordCardStateHistory.objects.create(record_card=record_card, group=record_card.responsible_profile,
                                                  previous_state_id=RecordState.PENDING_VALIDATE,
                                                  next_state_id=initial_state, user_id='22222', automatic=False)
            claim_days_limit = int(Parameter.get_parameter_by_key('DIES_PER_RECLAMAR', 60))
            RecordCardStateHistory.objects.filter(next_state__in=RecordState.CLOSED_STATES,
                                                  record_card_id=record_card.pk).update(
                created_at=timezone.now() - timedelta(days=claim_days_limit))

        try:
            ClaimValidation(record_card).validate()
            assert raise_exception is False
        except Exception as e:
            if raise_exception:
                if isinstance(e, AssertionError):
                    assert True
                else:
                    assert isinstance(e, RecordClaimException)
                    assert e.must_be_comment is must_be_comment
