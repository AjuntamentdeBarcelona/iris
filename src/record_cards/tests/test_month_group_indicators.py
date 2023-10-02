import pytest
from mock import Mock, patch

from iris_masters.models import RecordState
from profiles.tests.utils import create_groups, dict_groups
from record_cards.models import MonthIndicator
from record_cards.record_actions.month_group_indicators import MonthGroupIndicators


@pytest.mark.django_db
class TestMonthGroupIndicators:

    def test_set_initial_indicators(self):
        average_close_days = 23
        average_age_days = 10
        num_entries_records = 10
        initial_indicators = MonthGroupIndicators(2019, 10).set_initial_indicators(average_close_days, average_age_days,
                                                                                   num_entries_records)
        assert initial_indicators["pending_validation"] == 0
        assert initial_indicators["processing"] == 0
        assert initial_indicators["closed"] == 0
        assert initial_indicators["cancelled"] == 0
        assert initial_indicators["external_processing"] == 0
        assert initial_indicators["pending_records"] == 0
        assert initial_indicators["average_close_days"] == average_close_days
        assert initial_indicators["average_age_days"] == average_age_days
        assert initial_indicators["entries"] == num_entries_records

    def test_set_indicators(self):
        average_close_days = 23
        average_age_days = 10
        num_entries_records = 5
        indicators = MonthGroupIndicators(2019, 10).set_indicators(self.mock_records(), average_close_days,
                                                                   average_age_days, num_entries_records)

        assert indicators["pending_validation"] == 3
        assert indicators["processing"] == 4
        assert indicators["closed"] == 3
        assert indicators["cancelled"] == 1
        assert indicators["external_processing"] == 1
        assert indicators["pending_records"] == 8
        assert indicators["average_close_days"] == average_close_days
        assert indicators["average_age_days"] == average_age_days
        assert indicators["entries"] == num_entries_records

    def test_save_group_indicators(self):
        year = 2019
        month = 10
        dair, _, _, _, _, _ = create_groups()
        indicators = {
            "pending_validation": 3, "processing": 4, "closed": 3, "cancelled": 1, "external_processing": 1,
            "pending_records": 8, "average_close_days": 23, "average_age_days": 10, "entries": 5}
        MonthGroupIndicators(year, month).save_group_indicators(indicators, dair)

        indicators.update({"group": dair, "year": year, "month": month})
        assert MonthIndicator.objects.get(**indicators)

    def test_register_group_indicators_no_records(self):
        groups = dict_groups()
        year, month = 2019, 6

        records = Mock(return_value=[])
        calculate_average_close_days = Mock(return_value=0)
        calculate_average_age_days = Mock(return_value=0)
        calculate_entries_records = Mock(return_value=0)

        with patch("record_cards.record_actions.month_group_indicators.MonthGroupIndicators.get_group_records",
                   records):
            close = "record_cards.record_actions.month_group_indicators." \
                    "MonthGroupIndicators.calculate_average_close_days"
            with patch(close, calculate_average_close_days):
                age = "record_cards.record_actions.month_group_indicators." \
                      "MonthGroupIndicators.calculate_average_age_days"
                with patch(age, calculate_average_age_days):
                    entries = "record_cards.record_actions.month_group_indicators." \
                              "MonthGroupIndicators.calculate_entries_records"
                    with patch(entries, calculate_entries_records):
                        MonthGroupIndicators(year, month).register_month_indicators()
                        for _, group in groups.items():
                            indicator = MonthIndicator.objects.get(group=group, year=year, month=month)
                            assert indicator
                            assert indicator.pending_validation == 0
                            assert indicator.processing == 0
                            assert indicator.closed == 0
                            assert indicator.cancelled == 0
                            assert indicator.external_processing == 0
                            assert indicator.pending_records == 0
                            assert indicator.average_close_days == 0
                            assert indicator.average_age_days == 0
                            assert indicator.entries == 0

    def test_register_group_indicators_records(self):
        groups = dict_groups()
        year, month = 2019, 6

        records = Mock(return_value=self.mock_records())
        average_close_days = 15
        calculate_average_close_days = Mock(return_value=average_close_days)
        average_age_days = 11
        calculate_average_age_days = Mock(return_value=average_age_days)
        entries_records = 7
        calculate_entries_records = Mock(return_value=entries_records)

        with patch("record_cards.record_actions.month_group_indicators.MonthGroupIndicators.get_group_records",
                   records):
            close = "record_cards.record_actions.month_group_indicators." \
                    "MonthGroupIndicators.calculate_average_close_days"
            with patch(close, calculate_average_close_days):
                age = "record_cards.record_actions.month_group_indicators." \
                      "MonthGroupIndicators.calculate_average_age_days"
                with patch(age, calculate_average_age_days):
                    entries = "record_cards.record_actions.month_group_indicators." \
                              "MonthGroupIndicators.calculate_entries_records"
                    with patch(entries, calculate_entries_records):
                        MonthGroupIndicators(year, month).register_month_indicators()
                        for _, group in groups.items():
                            indicator = MonthIndicator.objects.get(group=group, year=year, month=month)
                            assert indicator
                            assert indicator.pending_validation == 3
                            assert indicator.processing == 4
                            assert indicator.closed == 3
                            assert indicator.cancelled == 1
                            assert indicator.external_processing == 1
                            assert indicator.pending_records == 8
                            assert indicator.average_close_days == average_close_days
                            assert indicator.average_age_days == average_age_days
                            assert indicator.entries == entries_records

    @staticmethod
    def mock_records():
        record_states = [RecordState.PENDING_VALIDATE, RecordState.IN_RESOLUTION, RecordState.CLOSED,
                         RecordState.EXTERNAL_RETURNED, RecordState.IN_PLANING, RecordState.CLOSED,
                         RecordState.PENDING_VALIDATE, RecordState.IN_RESOLUTION, RecordState.CLOSED,
                         RecordState.CANCELLED, RecordState.EXTERNAL_PROCESSING, RecordState.IN_PLANING]

        records = []
        for record_state in record_states:
            records.append({"temp_state": record_state})
        return records
