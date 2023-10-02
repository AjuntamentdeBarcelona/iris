import logging

from datetime import datetime

from iris_masters.models import RecordState
from record_cards.models import RecordCard


logger = logging.getLogger(__name__)


class RecoverClaimsClosingDate:

    PROD_RELEASE_DATE = datetime(2021, 2, 6)

    def __init__(self) -> None:
        super().__init__()
        # Record claimed that are opened
        self.records = RecordCard.objects.filter(created_at__gt=self.PROD_RELEASE_DATE, claimed_from_id__isnull=False,
                                                 record_state_id__in=RecordState.OPEN_STATES)

    def recover_closing_dates(self):
        logger.info(f'Recovering claims closing dates - {self.records.count()}')
        for idx, record in enumerate(self.records):
            record.closing_date = None
            record.save()
            logger.info(f'Record {record.normalized_record_id} recovered! - {idx+1}')

        logger.info(f'Claims closing dates recovered!')
