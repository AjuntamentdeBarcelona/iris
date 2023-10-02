from django.utils.functional import cached_property


class RecordCardMapOpenData:

    def __init__(self, record_card) -> None:
        self.record_card = record_card
        super().__init__()

    @cached_property
    def allow_open_data(self):
        return self.record_card.element_detail.allows_open_data

    @cached_property
    def allow_location(self):
        return self.record_card.element_detail.allows_open_data_location

    @cached_property
    def allow_sensible_location(self):
        return self.record_card.element_detail.allows_open_data_sensible_location

    def map(self):
        if not self.allow_open_data:
            return {}

        return {
            "CODI": self.record_card.normalized_record_id,
            "FITXA_ID": self.record_card.pk,
            "TIPUS": self.record_card.record_type.description,
            "AREA": self.record_card.element_detail.element.area.description,
            "ELEMENT": self.record_card.element_detail.element.description,
            "DETALL": self.record_card.element_detail.description,
            "DIA_DATA_ALTA": self.record_card.created_at.day,
            "MES_DATA_ALTA": self.record_card.created_at.month,
            "ANY_DATA_ALTA": self.record_card.created_at.year,
            "DIA_DATA_TANCAMENT": self.record_card.closing_date.day if self.record_card.closing_date else "",
            "MES_DATA_TANCAMENT": self.record_card.closing_date.month if self.record_card.closing_date else "",
            "ANY_DATA_TANCAMENT": self.record_card.closing_date.year if self.record_card.closing_date else "",
            "DISTRICTE": self.get_district_name(),
            "CODI_DISTRICTE": self.get_ubication_attribute("geocode_district_id"),
            "CODI_BARRI": self.get_ubication_attribute("neighborhood_id"),
            "BARRI": self.get_ubication_attribute("neighborhood"),
            "SECCIO_CENSAL": self.get_ubication_attribute("research_zone"),
            "TIPUS_VIA": self.get_ubication_sensible_attribute("via_type"),
            "CARRER": self.get_ubication_sensible_attribute("street"),
            "NUMERO": self.get_ubication_sensible_attribute("street2"),
            "COORDENADA_X": self.get_ubication_sensible_attribute("xetrs89a"),
            "COORDENADA_Y": self.get_ubication_sensible_attribute("yetrs89a"),
            "LONGITUD": self.get_ubication_sensible_attribute("longitude"),
            "LATITUD": self.get_ubication_sensible_attribute("latitude"),
            "SUPORT": self.record_card.support.description,
            "CANALS_RESPOSTA": self.get_response_channel()
        }

    def get_district_name(self):
        if self.allow_location and self.record_card.ubication and self.record_card.ubication.district:
            return self.record_card.ubication.district.name
        return ""

    def get_ubication_attribute(self, ubicationa_attribute):
        if self.allow_location and self.record_card.ubication:
            return getattr(self.record_card.ubication, ubicationa_attribute, "")
        return ""

    def get_ubication_sensible_attribute(self, ubicationa_attribute):
        if self.allow_location and self.allow_sensible_location and self.record_card.ubication:
            return getattr(self.record_card.ubication, ubicationa_attribute, "")
        return ""

    def get_response_channel(self):
        if hasattr(self.record_card, "recordcardresponse"):
            return self.record_card.recordcardresponse.response_channel.name
        return ""
