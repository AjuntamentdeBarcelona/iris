from model_mommy import mommy

from record_cards.models import Ubication


class TestGisGeocode:

    def test_get_address(self):
        pass

    def test_update_ubication(self):
        pass

    def test_update_ubication_when_not_exists(self):
        pass

    def test_get_polygon_code_when_exists(self):
        pass

    def given_an_ubication(self):
        self.ubication = mommy.make(
            Ubication,
            user_id='TEST',
            district_id=None,
            xetrs89a=20,
            yetrs89a=30,
        )

    def geocoder(self):
        pass

    def when_there_is_bound_for(self, attribute):
        pass
