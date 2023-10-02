import logging

from datetime import datetime

from iris_masters.models import Parameter
from record_cards.models import Comment, RecordCard

logger = logging.getLogger(__name__)


class RecoverAnsLimits:

    PROD_RELEASE_DATE = datetime(2021, 2, 6)

    def __init__(self) -> None:
        super().__init__()

        reason_theme_change_id = int(Parameter.get_parameter_by_key("CANVI_DETALL_MOTIU", 19))

        records_ids = Comment.objects.filter(
            created_at__gt=self.PROD_RELEASE_DATE, reason_id=reason_theme_change_id
        ).order_by("record_card_id").distinct("record_card_id").values_list("record_card_id", flat=True)

        # Record state changes from pending answer to closed after prod deploy
        self.records = RecordCard.objects.filter(pk__in=records_ids)

    def recover_limits(self):
        logger.info(f'Start ans limits recovering! - Total {self.records.count()}')
        for index, record in enumerate(self.records):
            logger.info(f'Recovering number {index+1}')
            record.update_ans_limits()
            logger.info(f'RecordCard {record.normalized_record_id} recovered!')
        logger.info(f'Finish ans limits recovering!')
