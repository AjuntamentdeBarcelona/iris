import pytest

from iris_masters.models import RecordState
from record_cards.models import RecordCardStateHistory, WorkflowComment, RecordCardAudit
from record_cards.record_actions.set_record_audits import SetRecordsAudits
from record_cards.tests.utils import CreateRecordCardMixin


@pytest.mark.django_db
class TestSetRecordAudits(CreateRecordCardMixin):

    def test_set_record_audits(self):
        user_name = "test"
        resol_comment = "resol comment"
        record_card = self.create_record_card(create_worflow=True)
        RecordCardStateHistory.objects.create(record_card=record_card, previous_state_id=RecordState.PENDING_VALIDATE,
                                              next_state_id=RecordState.IN_PLANING, user_id=user_name,
                                              group=record_card.responsible_profile)
        RecordCardStateHistory.objects.create(record_card=record_card, previous_state_id=RecordState.IN_PLANING,
                                              next_state_id=RecordState.CLOSED, user_id=user_name,
                                              group=record_card.responsible_profile)
        WorkflowComment.objects.create(workflow=record_card.workflow, task=WorkflowComment.PLAN, comment="test comment",
                                       user_id=user_name)
        WorkflowComment.objects.create(workflow=record_card.workflow, task=WorkflowComment.RESOLUTION,
                                       comment=resol_comment, user_id=user_name)

        SetRecordsAudits().set_audits()
        audit = RecordCardAudit.objects.get(record_card=record_card)
        assert audit
        assert audit.validation_user == user_name
        assert audit.planif_user == user_name
        assert audit.resol_user == user_name
        assert audit.resol_comment == resol_comment
        assert audit.close_user == user_name
