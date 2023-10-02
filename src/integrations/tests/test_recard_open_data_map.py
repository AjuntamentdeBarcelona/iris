import pytest
from model_mommy import mommy

from django.utils import timezone

from integrations.services.batch_processes.opendata.recard_open_data_map import RecordCardMapOpenData
from iris_masters.models import District
from record_cards.models import Ubication
from record_cards.tests.utils import CreateRecordCardMixin
from communications.tests.utils import load_missing_data

@pytest.mark.django_db
class TestRecordCardMapOpenData(CreateRecordCardMixin):

    def element_detail_open_data(self, allows_open_data=False, allows_open_data_location=False,
                                 allows_open_data_sensible_location=False):
        element_detail = self.create_element_detail()
        element_detail.allows_open_data = allows_open_data
        element_detail.allows_open_data_location = allows_open_data_location
        element_detail.allows_open_data_sensible_location = allows_open_data_sensible_location
        element_detail.save()
        return element_detail

    def test_map(self):
        district_id = 1
        if not District.objects.filter(id=district_id):
            district = District(id=district_id, name='Test District')
            district.save()
        load_missing_data()
        element_detail = self.element_detail_open_data(True, True, True)
        record_card = self.create_record_card(create_record_card_response=True, district_id=district_id,
                                              element_detail=element_detail)
        record_dict = RecordCardMapOpenData(record_card).map()

        assert record_dict["CODI"] == record_card.normalized_record_id
        assert record_dict["FITXA_ID"] == record_card.pk
        assert record_dict["TIPUS"] == record_card.record_type.description
        assert record_dict["AREA"] == record_card.element_detail.element.area.description
        assert record_dict["ELEMENT"] == record_card.element_detail.element.description
        assert record_dict["DETALL"] == record_card.element_detail.description
        assert record_dict["DIA_DATA_ALTA"] == record_card.created_at.day
        assert record_dict["MES_DATA_ALTA"] == record_card.created_at.month
        assert record_dict["ANY_DATA_ALTA"] == record_card.created_at.year
        assert record_dict["DIA_DATA_TANCAMENT"] == ""
        assert record_dict["MES_DATA_TANCAMENT"] == ""
        assert record_dict["ANY_DATA_TANCAMENT"] == ""
        assert record_dict["DISTRICTE"] == record_card.ubication.district.name
        assert record_dict["CODI_DISTRICTE"] == record_card.ubication.geocode_district_id
        assert record_dict["CODI_BARRI"] == record_card.ubication.neighborhood_id
        assert record_dict["BARRI"] == record_card.ubication.neighborhood
        assert record_dict["SECCIO_CENSAL"] == record_card.ubication.research_zone
        assert record_dict["TIPUS_VIA"] == record_card.ubication.via_type
        assert record_dict["CARRER"] == record_card.ubication.street
        assert record_dict["NUMERO"] == record_card.ubication.street2
        assert record_dict["COORDENADA_X"] == record_card.ubication.xetrs89a
        assert record_dict["COORDENADA_Y"] == record_card.ubication.yetrs89a
        assert record_dict["LONGITUD"] == record_card.ubication.longitude
        assert record_dict["LATITUD"] == record_card.ubication.latitude
        assert record_dict["SUPORT"] == record_card.support.description
        assert record_dict["CANALS_RESPOSTA"] == record_card.recordcardresponse.response_channel.name

    def test_map_no_ubication(self):
        load_missing_data()
        element_detail = self.element_detail_open_data(True, True, True)
        record_card = self.create_record_card(create_record_card_response=True, element_detail=element_detail)
        record_card.ubication = None
        record_card.save()
        record_dict = RecordCardMapOpenData(record_card).map()

        ubication_fields = ["DISTRICTE", "CODI_DISTRICTE", "CODI_BARRI", "BARRI", "SECCIO_CENSAL", "TIPUS_VIA",
                            "CARRER", "NUMERO", "COORDENADA_X", "COORDENADA_Y", "LONGITUD", "LATITUD"]

        for field in ubication_fields:
            assert record_dict[field] == ""

    def test_map_ubication_without_district(self):
        load_missing_data()
        element_detail = self.element_detail_open_data(True, True, True)
        ubication = mommy.make(Ubication, user_id="user_id", district=None)
        record_card = self.create_record_card(create_record_card_response=True, ubication=ubication,
                                              element_detail=element_detail)
        record_dict = RecordCardMapOpenData(record_card).map()
        assert record_dict["DISTRICTE"] == ""

    def test_map_closing_date(self):
        load_missing_data()
        element_detail = self.element_detail_open_data(True, True, True)
        closing_date = timezone.now()
        record_card = self.create_record_card(create_record_card_response=True, closing_date=closing_date,
                                              element_detail=element_detail)
        record_dict = RecordCardMapOpenData(record_card).map()
        assert record_dict["DIA_DATA_TANCAMENT"] == closing_date.day
        assert record_dict["MES_DATA_TANCAMENT"] == closing_date.month
        assert record_dict["ANY_DATA_TANCAMENT"] == closing_date.year

    def test_map_record_no_open_data(self):
        load_missing_data()
        element_detail = self.element_detail_open_data(False, False, False)
        record_card = self.create_record_card(create_record_card_response=True, element_detail=element_detail)
        record_dict = RecordCardMapOpenData(record_card).map()
        assert record_dict == {}

    def test_map_record_opendata_nolocation(self):
        load_missing_data()
        element_detail = self.element_detail_open_data(True, False, False)
        record_card = self.create_record_card(create_record_card_response=True, element_detail=element_detail)
        record_dict = RecordCardMapOpenData(record_card).map()

        ubication_fields = ["DISTRICTE", "CODI_DISTRICTE", "CODI_BARRI", "BARRI", "SECCIO_CENSAL", "TIPUS_VIA",
                            "CARRER", "NUMERO", "COORDENADA_X", "COORDENADA_Y", "LONGITUD", "LATITUD"]

        for field in ubication_fields:
            assert record_dict[field] == ""

    def test_map_recordcard_opendata_no_sensible_location(self):
        district_id = 1
        if not District.objects.filter(id=district_id):
            district = District(id=district_id, name='Test District')
            district.save()
        load_missing_data()
        element_detail = self.element_detail_open_data(True, True, False)
        record_card = self.create_record_card(create_record_card_response=True, district_id=district_id,
                                              element_detail=element_detail)
        record_dict = RecordCardMapOpenData(record_card).map()

        assert record_dict["DISTRICTE"] == record_card.ubication.district.name
        assert record_dict["CODI_DISTRICTE"] == record_card.ubication.geocode_district_id
        assert record_dict["CODI_BARRI"] == record_card.ubication.neighborhood_id
        assert record_dict["BARRI"] == record_card.ubication.neighborhood
        assert record_dict["SECCIO_CENSAL"] == record_card.ubication.research_zone

        sensible_ubication_fields = ["TIPUS_VIA", "CARRER", "NUMERO", "COORDENADA_X", "COORDENADA_Y", "LONGITUD",
                                     "LATITUD"]

        for field in sensible_ubication_fields:
            assert record_dict[field] == ""

    @pytest.mark.parametrize("allow_open_data", (True, False))
    def test_map_allow_open_data(self, allow_open_data):
        district_id = 1
        if not District.objects.filter(id=district_id):
            district = District(id=district_id, name='Test District')
            district.save()
        load_missing_data()
        element_detail = self.element_detail_open_data(allow_open_data, False, False)
        record_card = self.create_record_card(create_record_card_response=True, district_id=district_id,
                                              element_detail=element_detail)
        assert RecordCardMapOpenData(record_card).allow_open_data is allow_open_data

    @pytest.mark.parametrize("allow_location", (True, False))
    def test_map_allow_location(self, allow_location):
        district_id = 1
        if not District.objects.filter(id=district_id):
            district = District(id=district_id, name='Test District')
            district.save()
        load_missing_data()
        element_detail = self.element_detail_open_data(False, allow_location, False)
        record_card = self.create_record_card(create_record_card_response=True, district_id=district_id,
                                              element_detail=element_detail)
        assert RecordCardMapOpenData(record_card).allow_location is allow_location

    @pytest.mark.parametrize("allow_sensible_location", (True, False))
    def test_map_allow_sensible_location(self, allow_sensible_location):
        district_id = 1
        if not District.objects.filter(id=district_id):
            district = District(id=district_id, name='Test District')
            district.save()
        load_missing_data()
        element_detail = self.element_detail_open_data(False, False, allow_sensible_location)
        record_card = self.create_record_card(create_record_card_response=True, district_id=district_id,
                                              element_detail=element_detail)
        assert RecordCardMapOpenData(record_card).allow_sensible_location is allow_sensible_location
