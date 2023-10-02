from datetime import timedelta

from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from iris_masters.models import RecordState, Parameter
from record_cards.record_actions.exceptions import RecordClaimException
from record_cards.models import RecordCardStateHistory


class ClaimValidation:
    """
    Class to check if a claim Record can be created.
    If it can not be created, an RecordClaimException is raised with the reason on a message attribute.
    The exception includes another attribute "must_be_comment" to indicate that the claim must be processed as a comment
    """

    def __init__(self, record_card) -> None:
        self.record_card = record_card
        super().__init__()

    def validate(self):
        self.record_not_in_closed_states()
        self.exists_ongoing_claim()
        self.claim_limit_date_not_overcome()
        self.applicant_blocked()
        self.ans_date_limit_not_overcome()

    def record_not_in_closed_states(self):
        if self.record_card.record_state_id not in RecordState.CLOSED_STATES:
            message = _("A claim can not be created due to RecordCard state is not closed or cancelled."
                        "Current Record State is {}").format(self.record_card.record_state.description)
            raise RecordClaimException(message, must_be_comment=True)

    def exists_ongoing_claim(self):
        if self.record_card.is_claimed:
            raise RecordClaimException(_("A claim can not be created due to RecordCard has an existent claim"))

    def claim_limit_date_not_overcome(self):
        state_close_change = RecordCardStateHistory.objects.filter(next_state__in=RecordState.CLOSED_STATES,
                                                                   record_card_id=self.record_card.pk
                                                                   ).order_by('-created_at').first()
        if state_close_change:
            claim_days_limit = int(Parameter.get_parameter_by_key('DIES_PER_RECLAMAR', 60))
            claim_date_limit = state_close_change.created_at + timedelta(days=claim_days_limit)
            if timezone.now() > claim_date_limit:
                message = _("A claim can not be created due to RecordCard claim date limit has been overcome."
                            "Claim date limit was {}").format(claim_date_limit.strftime("%d-%m-%Y"))
                raise RecordClaimException(message)

    def applicant_blocked(self):
        applicant = self.record_card.request.applicant
        if not applicant:
            return False
        no_block_theme_pk = int(Parameter.get_parameter_by_key("TEMATICA_NO_BLOQUEJADA", 392))
        if applicant.blocked and no_block_theme_pk != self.record_card.element_detail_id:
            raise RecordClaimException(_("A claim can not be created due to RecordCard Applicant is blocked."
                                         "Applicant is {}").format(applicant.__str__()))

    def ans_date_limit_not_overcome(self):
        if hasattr(self.record_card.workflow, 'workflowresolution'):
            resolution_type = self.record_card.workflow.workflowresolution.resolution_type
            if self.record_card.element_detail.sla_allows_claims and resolution_type.can_claim_inside_ans:
                return
            if self.record_card.ans_limit_date > timezone.now():

                remaining_time = self.record_card.ans_limit_date - timezone.now()
                if remaining_time.days == 0:
                    remaining_text = _("There are a few hours left to claim. ANS limit date: {}").format(
                        self.record_card.ans_limit_date.strftime("%d-%m-%Y %H:%M"))
                else:
                    remaining_text = _("It remains {} days to claim.").format(remaining_time.days)

                message = _("A claim can not be created due to RecordCard ANS date limit has not overcome. {}"
                            ).format(remaining_text)

                raise RecordClaimException(message, must_be_comment=True)

    def validate_email(self, email):
        if not email and not self.record_card.recordcardresponse.address_mobile_email:
            raise RecordClaimException(_("You must provide an email."))
