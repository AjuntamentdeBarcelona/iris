import pytest

from themes.actions.theme_mandatory_fields import ThemeMandatoryFields
from themes.tests.utils import CreateThemesMixin
from communications.tests.utils import load_missing_data
from iris_masters.tests.utils import load_missing_data_process, load_missing_data_districts


@pytest.mark.django_db
class TestThemeMandatoryFields(CreateThemesMixin):

    @pytest.mark.parametrize(
        'requires_citizen,requires_ubication,requires_ubication_district,aggrupation_first,expected_key', (
                (False, False, False, False, 0),
                (True, False, False, False, 1),
                (False, True, False, False, 2),
                (True, True, False, False, 3),
                (True, False, False, True, 4),
                (True, True, False, True, 5),
                (False, False, True, False, 6),
                (True, False, True, False, 7),
                (True, False, True, True, 8),
                (False, True, True, False, 9),
                (True, True, True, False, 10),
                (True, True, True, True, 11),
                (False, False, True, True, None),
        ))
    def test_theme_mandatory_fields(self, requires_citizen, requires_ubication, requires_ubication_district,
                                    aggrupation_first, expected_key):
        load_missing_data()
        load_missing_data_process()
        load_missing_data_districts()
        element_detail = self.create_element_detail(requires_citizen=requires_citizen,
                                                    requires_ubication=requires_ubication,
                                                    requires_ubication_district=requires_ubication_district,
                                                    aggrupation_first=aggrupation_first)
        assert ThemeMandatoryFields(element_detail).get_mapping_value() == expected_key
