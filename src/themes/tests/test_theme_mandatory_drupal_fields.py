import pytest

from themes.actions.theme_mandatory_drupal_fields import ThemeMandatoryDrupalFields
from themes.tests.utils import CreateThemesMixin
from communications.tests.utils import load_missing_data
from iris_masters.tests.utils import load_missing_data_process, load_missing_data_districts


@pytest.mark.django_db
class TestThemeMandatoryDrupalFields(CreateThemesMixin):

    @pytest.mark.parametrize(
        'requires_citizen,requires_ubication,requires_ubication_district,aggrupation_first', (
                (False, False, False, False),
                (True, False, False, False),
                (False, True, False, False),
                (True, True, False, False),
                (True, False, False, True),
                (True, True, False, True),
                (False, False, True, False),
                (True, False, True, False),
                (True, False, True, True),
                (False, True, True, False),
                (True, True, True, False),
                (True, True, True, True),
        ))
    def test_theme_mandatory_drupal_fields(self, requires_citizen, requires_ubication, requires_ubication_district,
                                           aggrupation_first):
        load_missing_data()
        load_missing_data_process()
        load_missing_data_districts()
        element_detail = self.create_element_detail(requires_citizen=requires_citizen,
                                                    requires_ubication=requires_ubication,
                                                    requires_ubication_district=requires_ubication_district,
                                                    aggrupation_first=aggrupation_first)
        mandatory_fields = ThemeMandatoryDrupalFields(element_detail).get_mandatory_fields()
        assert mandatory_fields['citizen']['name'] is requires_citizen
        assert mandatory_fields['citizen']['first_surname'] is requires_citizen
        assert mandatory_fields['citizen']['document_type'] is requires_citizen
        assert mandatory_fields['citizen']['document'] is requires_citizen
        assert mandatory_fields['social_entity']['social_reason'] is aggrupation_first
        assert mandatory_fields['social_entity']['cif'] is aggrupation_first
        assert mandatory_fields['social_entity']['contact'] is aggrupation_first
        assert mandatory_fields['ubication']['street_name'] is requires_ubication
        assert mandatory_fields['ubication']['number'] is requires_ubication
        assert mandatory_fields['ubication']['district_ubication'] is requires_ubication_district
