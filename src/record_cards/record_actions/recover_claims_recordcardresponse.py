import logging

from copy import deepcopy
from datetime import datetime

from record_cards.models import RecordCard


logger = logging.getLogger(__name__)


class RecoverClaimsRecordCardResponse:

    PROD_RELEASE_DATE = datetime(2021, 2, 6)

    def __init__(self) -> None:
        super().__init__()
        # Record claimed and that has recordcardresponse after iris release.
        self.records = RecordCard.objects.filter(created_at__gt=self.PROD_RELEASE_DATE, claimed_from_id__isnull=False,
                                                 recordcardresponse__isnull=False)

    def recover_recordcard_response(self):
        for record_with_response in self.records:

            base_normalized_record_id = record_with_response.normalized_record_id.split("-")[0]
            logger.info(f'Recovering recordcardresponses from {base_normalized_record_id}')

            claimed_records = RecordCard.objects.filter(normalized_record_id__contains=base_normalized_record_id,
                                                        recordcardresponse__isnull=True)
            for claimed_record in claimed_records:
                logger.info(f'Recovering {claimed_record.normalized_record_id}!')
                rc_resp = deepcopy(record_with_response.recordcardresponse)
                rc_resp.pk = None
                rc_resp.record_card = claimed_record
                rc_resp.save()

            logger.info(f'Recordcardresponses from {base_normalized_record_id} recovered!')
