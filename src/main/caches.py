from abc import abstractmethod, ABCMeta


class DescriptionCache(metaclass=ABCMeta):

    def __init__(self) -> None:
        self.items = {}
        self.load_data()

    def load_data(self):
        queryset = self.get_queryset().only("description")
        for item in queryset:
            if item.pk not in self.items:
                self.items[item.pk] = {"description": item.description}

    @abstractmethod
    def get_queryset(self):
        pass

    def _get_item(self, item_id):
        try:
            return self.items.get(int(item_id))
        except ValueError:
            return self.items.get(item_id)

    def get_item_description(self, item_id):
        item = self._get_item(item_id)
        return item["description"] if item else ""
