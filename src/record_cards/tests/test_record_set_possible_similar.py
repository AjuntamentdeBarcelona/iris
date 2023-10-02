import pytest
from mock import patch

from record_cards.tests.utils import CreateRecordCardMixin
from record_cards.record_actions.record_set_possible_similar import RecordCardSetPossibleSimilar


@pytest.mark.django_db
class TestRecordCardSetPossibleSimilar(CreateRecordCardMixin):

    @pytest.mark.parametrize('object_number', (0, 1, 3))
    def test_theme_set_ambit(self, object_number):
        [self.create_record_card() for _ in range(object_number)]

        delay = 'record_cards.record_actions.record_set_possible_similar.register_possible_similar_records.delay'
        with patch(delay) as mock_delay:
            RecordCardSetPossibleSimilar().set_possible_similar()
            assert mock_delay.call_count == object_number
            if object_number > 0:
                mock_delay.assert_called()
