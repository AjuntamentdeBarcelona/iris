from themes.models import ElementDetail
from themes.tasks import register_theme_ambits


class ThemeSetAmbits:

    themes = []

    def __init__(self, themes=None) -> None:
        self.themes = themes if themes else ElementDetail.objects.filter(**ElementDetail.ENABLED_ELEMENTDETAIL_FILTERS)
        super().__init__()

    def set_theme_ambits(self):
        for theme in self.themes:
            register_theme_ambits.delay(theme.pk)
