from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate


class FeaturesConfig(AppConfig):
    name = "features"

    def ready(self):
        if settings.EXECUTE_DATA_CHEKS:
            from features.masks import check_masks
            post_migrate.connect(check_masks, sender=self)
