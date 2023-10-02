from record_cards.models import RecordCard
from record_cards.tasks import register_possible_similar_records


class RecordCardSetPossibleSimilar:

    def __init__(self, record_cards=None) -> None:
        self.record_cards = record_cards if record_cards else RecordCard.objects.filter(enabled=True)
        super().__init__()

    def set_possible_similar(self):
        for record_card in self.record_cards:
            register_possible_similar_records.delay(record_card.pk)
