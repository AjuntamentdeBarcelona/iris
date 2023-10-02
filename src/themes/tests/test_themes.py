import pytest
from mock import patch

from themes.models import ElementDetail
from themes.tests.utils import CreateThemesMixin
from themes.actions.theme_set_ambits import ThemeSetAmbits
from communications.tests.utils import load_missing_data
from iris_masters.tests.utils import load_missing_data_process, load_missing_data_districts


@pytest.mark.django_db
class TestThemeSetAmbits(CreateThemesMixin):

    @pytest.mark.parametrize('object_number', (0, 1, 3))
    def test_theme_set_ambit(self, object_number):
        load_missing_data()
        load_missing_data_process()
        load_missing_data_districts()
        ElementDetail.objects.all().delete()
        [self.create_element_detail(create_direct_derivations=True, create_district_derivations=True)
         for _ in range(object_number)]

        with patch('themes.actions.theme_set_ambits.register_theme_ambits.delay') as mock_delay:
            ThemeSetAmbits().set_theme_ambits()
            assert mock_delay.call_count == object_number
            if object_number > 0:
                mock_delay.assert_called()
