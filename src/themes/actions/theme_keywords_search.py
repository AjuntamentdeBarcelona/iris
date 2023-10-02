import unicodedata

from iris_masters.models import Parameter
from themes.models import Keyword, ElementDetail


class KeywordSearch:
    keywords = []

    def __init__(self, keywords) -> None:
        super().__init__()
        if keywords:
            self.keywords = keywords

    def details_search(self):
        details_ids = []
        keyword_details_ids = []
        min_length_keyword = int(Parameter.get_parameter_by_key("CERCA_MINIM_PARAULA", 4))
        for keyword_text in self.keywords:
            keyword = self.strip_accents(keyword_text.upper())
            keyword_details = Keyword.objects.filter(description__exact=keyword,
                                                     enabled=True).values_list("detail_id", flat=True)
            keyword_details_ids += keyword_details
            details_ids += keyword_details

            if len(keyword_text) >= min_length_keyword or keyword_details:
                details_ids += self.find_details_element_description(keyword_text)

        return details_ids, keyword_details_ids

    @staticmethod
    def find_details_element_description(keyword_text):
        return ElementDetail.objects.filter(element__description__unaccent__icontains=keyword_text,
                                            **ElementDetail.ENABLED_ELEMENTDETAIL_FILTERS
                                            ).values_list("id", flat=True)

    @staticmethod
    def strip_accents(string, accents=('COMBINING ACUTE ACCENT', 'COMBINING GRAVE ACCENT')):
        accents = set(map(unicodedata.lookup, accents))
        chars = [c for c in unicodedata.normalize('NFD', string) if c not in accents]
        return unicodedata.normalize('NFC', ''.join(chars))
