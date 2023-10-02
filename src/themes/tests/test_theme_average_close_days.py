import pytest
from mock import Mock, patch

from record_cards.tests.utils import CreateRecordCardMixin
from themes.actions.theme_average_close_days import ThemeAverageCloseDays
from themes.models import ElementDetail
from communications.tests.utils import load_missing_data
from iris_masters.tests.utils import load_missing_data_process


@pytest.mark.django_db
class TestThemeAverageCloseDays(CreateRecordCardMixin):

    def test_get_themes(self):
        load_missing_data()
        load_missing_data_process()
        ElementDetail.objects.all().delete()
        self.create_element_detail()
        themes = ThemeAverageCloseDays().get_themes()
        assert themes.count() == 1

    def test_calculate_average_close_days(self):
        load_missing_data()
        load_missing_data_process()
        element_detail = self.create_element_detail()
        average_close_days = Mock(return_value=2)
        with patch("themes.actions.theme_average_close_days.ThemeAverageCloseDays.get_theme_average_close_days",
                   average_close_days):
            ThemeAverageCloseDays().calculate_average_close_days()
            element_detail = ElementDetail.objects.get(pk=element_detail.pk)
            assert element_detail.average_close_days == average_close_days.return_value
