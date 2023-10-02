from django.conf import settings

from iris_masters.models import RecordType
from main.caches import DescriptionCache
from themes.models import Area


class RecordTypeDescriptionsCache(DescriptionCache):
    def get_queryset(self):
        return RecordType.objects.all()

    def load_data(self):
        queryset = self.get_queryset()
        for item in queryset:
            if item.pk not in self.items:
                self.items[item.pk] = {"description": item.description,
                                       "description_es": getattr(item, "description_es", item.description)}

    def _get_item(self, item_id):
        return self.items.get(item_id)

    def get_item_description(self, item_id):
        item = self._get_item(item_id)
        return item["description_es"] if item else ""


class AreaCache(DescriptionCache):
    def get_queryset(self):
        return Area.objects.all()

    def load_data(self):
        queryset = self.get_queryset()
        for item in queryset:
            item_d = {
                f"description_{lang}": getattr(item, f"description_{lang}")
                for lang, _ in settings.LANGUAGES
            }
            item_d.update({
                "description": item.description,
                "icon_name": item.icon_name
            })
            if item.pk not in self.items:
                self.items[item.pk] = item_d

    def get_translated_description(self, item_id, lang):
        item = self._get_item(item_id)
        return item.get(f"description_{lang}") if item else ""

    def get_item_icon_name(self, item_id):
        item = self._get_item(item_id)
        return item["icon_name"] if item else ""


class ElementDetailListCache:

    def __init__(self) -> None:
        super().__init__()
        self.record_type = RecordTypeDescriptionsCache()
        self.area = AreaCache()
