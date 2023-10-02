from datetime import timedelta
from math import ceil

from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from iris_masters.models import RecordState, Parameter
from record_cards.models import RecordCardStateHistory, Comment
from record_cards.record_actions.claim_validate import ClaimValidation
from record_cards.record_actions.exceptions import RecordClaimException
from record_cards.record_actions.get_recode_from_text import get_record_code_from_text


class RecordCardStatePublicTexts:

    def __init__(self, record_card) -> None:
        super().__init__()
        self.record_card = record_card

    def get_state_text(self):
        if self.record_card.record_state_id == RecordState.CANCELLED:
            message = self.check_record_duplicity()
            if message:
                return message

        if self.record_card.is_claimed:
            return _("The requested petition {} is closed and has a claim. The status of the petition corresponding"
                     " to this claim is displayed.").format(self.record_card.normalized_record_id)

        if self.record_card.record_state_id in [RecordState.CLOSED, RecordState.CANCELLED]:
            message = _("The record that you were looking for is closed.")
            can_be_claimed = self.record_can_be_claimed()
            if can_be_claimed:
                message = "{} {}".format(message,
                                         _("If you have not received any answer, you do not agree with its resolution "
                                           "or you want to provide new information or documentation you can fill in "
                                           "your request again by doing a Claim."))
            else:
                extra_claim_message = self.set_extra_claim_message()
                if extra_claim_message:
                    message = "{} {}".format(message, extra_claim_message)
        elif self.record_card.record_state_id == RecordState.NO_PROCESSED:
            message = _("The record that you were looking for is not being processed.")
        else:
            message = self.set_message_ans()
        return message

    def record_can_be_claimed(self):
        try:
            ClaimValidation(self.record_card).validate()
            return True
        except RecordClaimException:
            return False

    def set_extra_claim_message(self):
        message_claim_date = self.set_message_claim_date()
        if message_claim_date:
            return message_claim_date
        else:
            message_expected_resolution = self.set_message_expected_resolution()
            if message_expected_resolution:
                return message_expected_resolution

    def set_message_ans(self):
        if self.record_card.ans_limit_date and self.record_card.ans_limit_date > timezone.now():
            days = ceil(self.record_card.element_detail.ans_delta_hours / 24)
            return _("This request is still within the expected time of resolution {} day/s, and for this "
                     "reason we cannot accept its claim. It will be solved shortly.").format(days)
        return ""

    def set_message_expected_resolution(self):
        if hasattr(self.record_card.workflow, 'workflowresolution'):
            resolution_type = self.record_card.workflow.workflowresolution.resolution_type
            if not resolution_type.can_claim_inside_ans and self.record_card.ans_limit_date > timezone.now():
                days = ceil(self.record_card.element_detail.ans_delta_hours / 24)
                return _("This request is still within the expected time of resolution {} day/s, and for this "
                         "reason we cannot accept its claim. It will be solved shortly.").format(days)
        return ""

    def check_record_duplicity(self):
        duplicity_repetition_reason_id = int(Parameter.get_parameter_by_key("DEMANAR_FITXA", 1))
        record_duplicy = Comment.objects.filter(record_card=self.record_card,
                                                reason_id=duplicity_repetition_reason_id).first()
        if record_duplicy:
            processed = get_record_code_from_text(record_duplicy.comment)
            return _("The petition has been canceled due to duplication or reiteration. "
                     "The petition processed is {}. If desired, you can claim the processed petition.").format(
                processed)

    def set_message_claim_date(self):
        state_close_change = RecordCardStateHistory.objects.filter(
            next_state__in=RecordState.CLOSED_STATES, record_card_id=self.record_card.pk).order_by(
            "-created_at").first()
        if state_close_change:
            claim_days_limit = int(Parameter.get_parameter_by_key("DIES_PER_RECLAMAR", 60))
            claim_date_limit = state_close_change.created_at + timedelta(days=claim_days_limit)
            if timezone.now() > claim_date_limit:
                return _("This request has been closed for more than {} days. To contact again with us "
                         "you are required to go back to the main menu and open a new request.").format(
                    claim_days_limit)
        return ""
