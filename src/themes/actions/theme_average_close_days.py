from django.db.models import Avg, F

from iris_masters.models import RecordState
from record_cards.models import RecordCard
from themes.models import ElementDetail


class ThemeAverageCloseDays:

    def calculate_average_close_days(self):
        themes = self.get_themes()
        for theme in themes:
            theme.average_close_days = self.get_theme_average_close_days(theme.pk)
            theme.save()

    def get_themes(self):
        return ElementDetail.objects.filter(**ElementDetail.ENABLED_ELEMENTDETAIL_FILTERS)

    def get_theme_average_close_days(self, theme_pk):
        average_close_days = RecordCard.objects.filter(
            element_detail_id=theme_pk, recordcardstatehistory__next_state_id=RecordState.CLOSED
        ).aggregate(close_days=Avg(F("recordcardstatehistory__created_at") - F("created_at")))
        return average_close_days["close_days"].days if average_close_days["close_days"] else None
