import logging

from datetime import datetime

from iris_masters.models import RecordState
from record_cards.models import RecordCardStateHistory


logger = logging.getLogger(__name__)


class RecoverCloseUserAudit:

    PROD_RELEASE_DATE = datetime(2021, 2, 6)

    def __init__(self) -> None:
        super().__init__()
        # Record state changes from pending answer to closed after prod deploy
        self.records_state_close = RecordCardStateHistory.objects.filter(created_at__gt=self.PROD_RELEASE_DATE,
                                                                         previous_state_id=RecordState.PENDING_ANSWER,
                                                                         next_state_id=RecordState.CLOSED)

    def recover_close_user(self):
        logger.info(f'Start close user recovering! - Total {self.records_state_close.count()}')
        for index, state_change in enumerate(self.records_state_close):
            logger.info(f'Recovering number {index+1}')
            record_card_audit = getattr(state_change.record_card, "recordcardaudit", False)
            if record_card_audit and not record_card_audit.close_user:
                record_card_audit.close_user = state_change.user_id
                record_card_audit.save()

                logger.info(f'RecordAudit from {state_change.record_card.normalized_record_id} recovered!')
        logger.info(f'Finish close user recovering!')
