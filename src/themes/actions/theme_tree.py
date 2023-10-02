import uuid
from collections import OrderedDict

from django.conf import settings
from django.core.cache import cache
from django.db.models import Prefetch

from themes.models import ElementDetail, Keyword, ApplicationElementDetail, Area, Element


class ThemeTreeBuilder:
    DEFAULT_CACHE_VERSION = 5

    def __init__(self, cache_version=None):
        self.cache_version = cache_version or self.DEFAULT_CACHE_VERSION
        self.response = None

    def rebuild(self):
        self.build(force=True)

    def build(self, force=False):
        self.response = cache.get("themes_tree", None, version=self.cache_version)
        if not self.response or force:
            self.response = OrderedDict()
            element_details = self.get_active_element_details()
            element_areas = {}
            for area in Area.objects.filter(**Area.ENABLED_AREA_FILTERS).only('pk', 'description_es', 'order'):
                if area.pk not in self.response:
                    self.set_default_area(area.pk, area.description_es, area.order)

            for element in Element.objects.filter(**Element.ENABLED_ELEMENT_FILTERS).only(
                    'pk', 'area_id', 'description_es', 'order'):
                if element.pk not in self.response[element.area_id]["elements"]:
                    self.set_default_element(element.area_id, element.pk, element.description_es, element.order)
                    element_areas[element.pk] = element.area_id

            for detail in element_details:
                area_pk = element_areas[detail.element_id]
                element_pk = detail.element_id

                if detail.pk not in self.response[area_pk]["elements"][element_pk]["details"]:
                    self.response[area_pk]["elements"][element_pk]["details"][detail.pk] = {
                        'description': detail.description,
                        ** {'description_' + language: getattr(detail, 'description_' + language)
                            for language, name in settings.LANGUAGES},
                        'record_type_id': detail.record_type_id,
                        'active': detail.active,
                        'order': detail.order,
                        'activation_date': detail.activation_date,
                        'visible': detail.visible,
                        'visible_date': detail.visible_date,
                        'detail_code': detail.detail_code,
                    }

                detail_pk = detail.pk
                self.set_detail_keywords(area_pk, element_pk, detail_pk, detail)
                self.set_detail_applications(area_pk, element_pk, detail_pk, detail)
            cache.set("themes_tree", self.response, version=self.cache_version, timeout=None)
            cache.set("themes_tree_mark", str(uuid.uuid4()), version=self.cache_version, timeout=None)
        return self.response

    def get_cache_mark(self):
        return cache.get("themes_tree_mark", None, version=self.cache_version)

    def clear_cache(self):
        cache.set("themes_tree", "", timeout=0, version=self.cache_version)
        cache.set("themes_tree_mark", "", timeout=0, version=self.cache_version)

    @staticmethod
    def get_active_element_details():
        return ElementDetail.objects.filter(
            **ElementDetail.ENABLED_ELEMENTDETAIL_FILTERS
        ).prefetch_related(
            Prefetch("keyword_set", queryset=Keyword.objects.filter(enabled=True)),
            Prefetch("applicationelementdetail_set", queryset=ApplicationElementDetail.objects.filter(enabled=True))
        ).only("id", "order", "description", "record_type_id", "active", "activation_date",
               "visible", "visible_date", "detail_code")

    def set_default_area(self, area_pk, area_description, area_order):
        self.response[area_pk] = {
            "description": area_description,
            "order": area_order,
            "elements": OrderedDict()
        }

    def set_default_element(self, area_pk, element_pk, element_description, element_order):
        self.response[area_pk]["elements"][element_pk] = {
            "description": element_description,
            "order": element_order,
            "details": OrderedDict()
        }

    def set_detail_attribute(self, area_pk, element_pk, detail_pk, detail, attribute_key, has_translations=False):
        self.response[area_pk]["elements"][element_pk]["details"][detail_pk][attribute_key] = getattr(
            detail, attribute_key)
        if has_translations:
            for language in settings.LANGUAGES:
                translated_key = "{}_{}".format(attribute_key, language[0])
                self.response[area_pk]["elements"][element_pk]["details"][detail_pk][translated_key] = getattr(
                    detail, translated_key)
                self.response[area_pk]["elements"][element_pk]["details"][detail_pk]["order"] = detail.order

    def set_detail_keywords(self, area_pk, element_pk, detail_pk, detail):
        self.response[area_pk]["elements"][element_pk]["details"][detail_pk]["keywords"] = []

        for keyword in detail.keyword_set.all():
            self.response[area_pk]["elements"][element_pk]["details"][detail_pk]["keywords"].append(keyword.description)

    def set_detail_applications(self, area_pk, element_pk, detail_pk, detail):
        self.response[area_pk]["elements"][element_pk]["details"][detail_pk]["applications"] = []

        for app in detail.applicationelementdetail_set.all():
            self.response[area_pk]["elements"][element_pk]["details"][detail_pk][
                "applications"].append(app.application_id)
