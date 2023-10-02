from iris_masters.models import RecordState
from record_cards.models import RecordCard, WorkflowComment


class SetRecordsAudits:

    def set_audits(self):
        for record in RecordCard.objects.all():

            audit = record.get_record_audit()
            self.register_validation_user(record, audit)
            self.register_close_user(record, audit)
            if record.workflow:
                self.register_plan_user(record, audit)
                self.register_resol_information(record, audit)
            audit.save()

    @staticmethod
    def register_validation_user(record, audit):
        validate = record.recordcardstatehistory_set.filter(previous_state_id=RecordState.PENDING_VALIDATE).exclude(
            next_state_id=RecordState.PENDING_VALIDATE).first()
        if validate:
            audit.validation_user = validate.user_id

    @staticmethod
    def register_close_user(record, audit):
        close_state_history = record.recordcardstatehistory_set.filter(
            next_state_id__in=RecordState.CLOSED_STATES).first()
        if close_state_history:
            audit.close_user = close_state_history.user_id

    @staticmethod
    def register_plan_user(record, audit):
        workflow_plan = record.workflow.workflowcomment_set.filter(task=WorkflowComment.PLAN).first()
        if workflow_plan:
            audit.planif_user = workflow_plan.user_id

    @staticmethod
    def register_resol_information(record, audit):
        workflow_resolute = record.workflow.workflowcomment_set.filter(task=WorkflowComment.RESOLUTION).first()
        if workflow_resolute:
            audit.resol_user = workflow_resolute.user_id
            audit.resol_comment = workflow_resolute.comment
