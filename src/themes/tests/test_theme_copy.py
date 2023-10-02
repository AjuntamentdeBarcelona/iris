from copy import deepcopy

import pytest
from model_mommy import mommy

from themes.actions.theme_copy import ElementDetailCopy
from themes.models import Keyword, ElementDetail
from themes.tests.utils import CreateThemesMixin
from communications.tests.utils import load_missing_data
from iris_masters.tests.utils import load_missing_data_process


@pytest.mark.django_db
class TestElementDetailCopy(CreateThemesMixin):

    @pytest.mark.parametrize("related_objects", (0, 1, 3))
    def test_copy_related_objects(self, related_objects):
        load_missing_data()
        load_missing_data_process()
        prev_element_detail = self.create_element_detail()
        [mommy.make(Keyword, user_id="2322", detail=prev_element_detail) for _ in range(related_objects)]

        copy_class = ElementDetailCopy(prev_element_detail)
        copy_class.element_detail = deepcopy(prev_element_detail)
        copy_class.element_detail.pk = None
        copy_class.element_detail.save()
        copy_class._copy_related_objects("keyword_set", "detail")

        assert copy_class.element_detail.keyword_set.count() == related_objects
        assert prev_element_detail.keyword_set.count() == related_objects

    @pytest.mark.parametrize("related_objects", (0, 1, 3))
    def test_copy_detail_relations(self, related_objects):
        load_missing_data()
        load_missing_data_process()
        prev_element_detail = self.create_element_detail()
        [mommy.make(Keyword, user_id="2322", detail=prev_element_detail) for _ in range(related_objects)]

        copy_class = ElementDetailCopy(prev_element_detail)
        copy_class.element_detail = deepcopy(prev_element_detail)
        copy_class.element_detail.pk = None
        copy_class.element_detail.save()

        copy_class._copy_detail_relations()

        assert copy_class.element_detail.keyword_set.count() == related_objects
        assert prev_element_detail.keyword_set.count() == related_objects

    def test_copy_new_fields(self):
        load_missing_data()
        load_missing_data_process()
        prev_element_detail = self.create_element_detail()
        new_fields = {"description_ca": "description_ca", "description_es": "description_es",
                      "description_en": "description_en", "element": self.create_element()}

        copy_class = ElementDetailCopy(prev_element_detail)
        copy_class.element_detail = deepcopy(prev_element_detail)
        copy_class.element_detail.pk = None
        copy_class.element_detail.save()
        copy_class._copy_new_fields(new_fields)
        for field, value in new_fields.items():
            assert getattr(copy_class.element_detail, field, None) == value

    @pytest.mark.parametrize("related_objects", (0, 1, 3))
    def test_copy(self, related_objects):
        load_missing_data()
        load_missing_data_process()
        prev_element_detail = self.create_element_detail()
        [mommy.make(Keyword, user_id="2322", detail=prev_element_detail) for _ in range(related_objects)]
        new_fields = {"description_ca": "description_ca", "description_es": "description_es",
                      "description_en": "description_en", "element": self.create_element()}

        user_id = "22222"
        new_element_detail = ElementDetailCopy(prev_element_detail).copy(user_id, new_fields)
        assert isinstance(new_element_detail, ElementDetail)
        assert prev_element_detail != new_element_detail
        for field, value in new_fields.items():
            assert getattr(new_element_detail, field, None) == value
        assert new_element_detail.keyword_set.count() == related_objects
        assert new_element_detail.user_id == user_id
        assert prev_element_detail.keyword_set.count() == related_objects
