import logging
from abc import ABCMeta, abstractmethod

from django.conf import settings
from django.db import transaction
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


def get_geocoder_class():
    try:
        Geocoder = import_string(settings.GEOCODER_CLASS)
        return Geocoder
    except ImportError:
        logger.info(
            f"Unable to locate the geocoder class: {settings.GEOCODER_CLASS}.")


def get_geocoder_services_class():
    try:
        GeocoderServices = import_string(settings.GEOCODER_SERVICES_CLASS)
        return GeocoderServices
    except ImportError:
        logger.info(f"Unable to locate the geocoder services class: {settings.GEOCODER_SERVICES_CLASS}.")


class AddressNotFoundException(Exception):
    pass


class BaseGeocoder(metaclass=ABCMeta):

    def __init__(self, record_card=None, ubication=None):
        if ubication is not None:
            self.ubication = ubication
        elif record_card is not None:
            self.record_card = record_card
            self.ubication = record_card.ubication
        self.ubication.adjust_coordinates()
        self.logger = logging.getLogger(__name__)

    @abstractmethod
    def get_polygon_code(self, polygon, address=None) -> str:
        pass

    @abstractmethod
    def update_ubication(self, commit=True):
        pass


class RecordCardUbicationGeocoder(BaseGeocoder):
    """
    Class combination of RecordCardGeocoder and UbicationGeocoder
    """

    def __init__(self, record_card=None, ubication=None):
        super().__init__(record_card, ubication)
        GcodServices = get_geocoder_services_class()
        self.client = GcodServices()

    def get_address_info(self):
        if not settings.POLYGON_GEO_BCN:
            raise AddressNotFoundException({})
        number = self.ubication.street2
        if '-' in number:
            number = number.split('-')[0]
        result = self.client.adress_validation_variable(
            self.ubication.street,
            number,
            lletraIni=self.ubication.letter
        )
        if result.get("ReturnCode", 1) and result.get("Count") > 0:
            result = result.get("Data")[0]
            coord_x = result.get("XNUM_POST")
            coord_y = result.get("YNUM_POST")
            xetrs89 = (int(coord_x)/1000) + 400000
            yetrs89 = (int(coord_y)/1000) + 4500000
            self.ubication.coordinate_x = result.get("XNUM_POST")
            self.ubication.coordinate_y = result.get("YNUM_POST")
            self.ubication.xetrs89a = xetrs89
            self.ubication.yetrs89a = yetrs89
            if not self.ubication.district_id and result.get("DISTRICTE"):
                self.ubication.district_id = int(result.get("DISTRICTE"))
            try:
                self.ubication.save(update_fields=["coordinate_x", "coordinate_y", "district_id", "updated_at",
                                                    "xetrs89a", "yetrs89a"])
            except ValueError:
                # Avoid save, only for derivation checks
                pass

            return {
                "code": result.get("CODI"),
                "x": result.get("XNUM_POST"),
                "y": result.get("YNUM_POST"),
                "ine": result.get("CODI_INE"),
                "solar": result.get("SOLAR"),
                "cens": result.get("SECC_CENS"),
                "district": int(result.get("DISTRICTE")),
                "postal_district": result.get("DIST_POST"),
                "parc": result.get("CODI_PARC"),
                "illa": result.get("CODI_ILLA"),
            }
        raise AddressNotFoundException(result)

    def get_polygon_code(self, polygon, address=None):
        if not settings.POLYGON_GEO_BCN:
            return None

        address = address or self.get_address_info()
        result = self.client.get_dades_xy(polygon, address.get("x"), address.get("y"))
        if result.get("ReturnCode", 1) and result.get("Count") > 0:
            result = result.get("Data")[0]
            return result.get("CODIGO")
        return None

    def update_ubication(self, commit=True):
        if getattr(self.ubication, "extendedgeocodeubication", None):
            return

        if not settings.POLYGON_GEO_BCN:
            raise AddressNotFoundException({})
        number = self.ubication.street2
        if '-' in number:
            number = number.split('-')[0]
        result = self.client.adress_validation_variable(
            self.ubication.street,
            number,
            lletraIni=self.ubication.letter
        )
        if result.get("ReturnCode", 1) and result.get("Count") > 0:
            result = result.get("Data")[0]
            coord_x = result.get("XNUM_POST")
            coord_y = result.get("YNUM_POST")
            xetrs89 = (int(coord_x)/1000) + 400000
            yetrs89 = (int(coord_y)/1000) + 4500000
            with transaction.atomic():
                self.ubication.official_street_name = result.get("NOM27")
                self.ubication.street = result.get("NOM_COMPLET")
                self.ubication.street2 = result.get("NUMPOST_I")
                self.ubication.geocode_validation = result.get("CODI_CARR")
                self.ubication.numbering_type = result.get("TIPUSNUM")
                self.ubication.neighborhood = result.get("BARRI_NOM")
                self.ubication.neighborhood_id = result.get("BARRI")
                self.ubication.coordinate_x = result.get("XNUM_POST")
                self.ubication.coordinate_y = result.get("YNUM_POST")
                self.ubication.statistical_sector = result.get("SECC_EST")
                self.ubication.letter = result.get("LLEPOST_I")
                self.ubication.district_id = result.get("DISTRICTE")
                self.ubication.xetrs89a = xetrs89
                self.ubication.yetrs89a = yetrs89
                if commit:
                    self.ubication.save(update_fields=[
                        "updated_at", "official_street_name", "street", "street2",
                        "geocode_validation", "numbering_type", "neighborhood",
                        "neighborhood_id", "coordinate_x", "coordinate_y",
                        "statistical_sector",
                        "letter", "district_id", "xetrs89a", "yetrs89a"
                    ])
                try:
                    geo_ubication = self.ubication.extendedgeocodeubication
                except Exception:
                    from record_cards.models import ExtendedGeocodeUbication
                    geo_ubication = ExtendedGeocodeUbication(ubication=self.ubication)

                geo_ubication.llepost_f = result.get("LLEPOST_F")
                geo_ubication.numpost_f = result.get("NUMPOST_F")
                geo_ubication.dist_post = result.get("DIST_POST")
                geo_ubication.codi_illa = result.get("CODI_ILLA")
                geo_ubication.solar = result.get("SOLAR")
                geo_ubication.codi_parc = result.get("CODI_PARC") if result.get("CODI_PARC") else ''
                if commit:
                    geo_ubication.save()
            return
        raise AddressNotFoundException(result)


class RecordCardGeocoder:

    def __init__(self, record_card):
        self.record_card = record_card
        GcodServices = get_geocoder_services_class()
        self.client = GcodServices()
        self.logger = logging.getLogger(__name__)

    @property
    def ubication(self):
        return self.record_card.ubication

    def get_address_info(self):
        if not settings.POLYGON_GEO_BCN:
            raise AddressNotFoundException({})
        number = self.ubication.street2
        if '-' in number:
            number = number.split('-')[0]
        result = self.client.adress_validation_variable(
            self.ubication.street,
            number,
            lletraIni=self.ubication.letter
        )
        if result.get("ReturnCode", 1) and result.get("Count") > 0:
            result = result.get("Data")[0]
            coord_x = result.get("XNUM_POST")
            coord_y = result.get("YNUM_POST")
            xetrs89 = (int(coord_x)/1000) + 400000
            yetrs89 = (int(coord_y)/1000) + 4500000
            self.ubication.coordinate_x = result.get("XNUM_POST")
            self.ubication.coordinate_y = result.get("YNUM_POST")
            self.ubication.xetrs89a = xetrs89
            self.ubication.yetrs89a = yetrs89
            if not self.ubication.district_id and result.get("DISTRICTE"):
                self.ubication.district_id = int(result.get("DISTRICTE"))
            try:
                self.ubication.save(update_fields=["coordinate_x", "coordinate_y", "district_id", "updated_at",
                                                   "xetrs89a", "yetrs89a"])
            except ValueError:
                # Avoid save, only for derivation checks
                pass

            return {
                "code": result.get("CODI"),
                "x": result.get("XNUM_POST"),
                "y": result.get("YNUM_POST"),
                "ine": result.get("CODI_INE"),
                "solar": result.get("SOLAR"),
                "cens": result.get("SECC_CENS"),
                "district": int(result.get("DISTRICTE")),
                "postal_district": result.get("DIST_POST"),
                "parc": result.get("CODI_PARC"),
                "illa": result.get("CODI_ILLA"),
            }
        raise AddressNotFoundException(result)

    def get_polygon_code(self, polygon, address=None):
        if not settings.POLYGON_GEO_BCN:
            return None

        address = address or self.get_address_info()
        result = self.client.get_dades_xy(polygon, address.get("x"), address.get("y"))
        if result.get("ReturnCode", 1) and result.get("Count") > 0:
            result = result.get("Data")[0]
            return result.get("CODIGO")
        return None


class UbicationGeocoder:

    def __init__(self, ubication):
        self.ubication = ubication
        GcodServices = get_geocoder_services_class()
        self.client = GcodServices()
        self.logger = logging.getLogger(__name__)

    def update_ubication(self):
        if getattr(self.ubication, "extendedgeocodeubication", None):
            return

        if not settings.POLYGON_GEO_BCN:
            raise AddressNotFoundException({})
        number = self.ubication.street2
        if '-' in number:
            number = number.split('-')[0]
        result = self.client.adress_validation_variable(
            self.ubication.street,
            number,
            lletraIni=self.ubication.letter
        )
        if result.get("ReturnCode", 1) and result.get("Count") > 0:
            result = result.get("Data")[0]
            coord_x = result.get("XNUM_POST")
            coord_y = result.get("YNUM_POST")
            xetrs89 = (int(coord_x)/1000) + 400000
            yetrs89 = (int(coord_y)/1000) + 4500000
            with transaction.atomic():
                self.ubication.official_street_name = result.get("NOM27")
                self.ubication.street = result.get("NOM_COMPLET")
                self.ubication.street2 = result.get("NUMPOST_I")
                self.ubication.geocode_validation = result.get("CODI_CARR")
                self.ubication.numbering_type = result.get("TIPUSNUM")
                self.ubication.neighborhood = result.get("BARRI_NOM")
                self.ubication.neighborhood_id = result.get("BARRI")
                self.ubication.coordinate_x = result.get("XNUM_POST")
                self.ubication.coordinate_y = result.get("YNUM_POST")
                self.ubication.statistical_sector = result.get("SECC_EST")
                self.ubication.letter = result.get("LLEPOST_I")
                self.ubication.district_id = result.get("DISTRICTE")
                self.ubication.xetrs89a = xetrs89
                self.ubication.yetrs89a = yetrs89
                self.ubication.save(update_fields=["updated_at", "official_street_name", "street", "street2",
                                                   "geocode_validation", "numbering_type", "neighborhood",
                                                   "neighborhood_id", "coordinate_x", "coordinate_y",
                                                   "statistical_sector",
                                                   "letter", "district_id", "xetrs89a", "yetrs89a"])
                try:
                    geo_ubication = self.ubication.extendedgeocodeubication
                except Exception:
                    from record_cards.models import ExtendedGeocodeUbication
                    geo_ubication = ExtendedGeocodeUbication(ubication=self.ubication)

                geo_ubication.llepost_f = result.get("LLEPOST_F")
                geo_ubication.numpost_f = result.get("NUMPOST_F")
                geo_ubication.dist_post = result.get("DIST_POST")
                geo_ubication.codi_illa = result.get("CODI_ILLA")
                geo_ubication.solar = result.get("SOLAR")
                geo_ubication.codi_parc = result.get("CODI_PARC") if result.get("CODI_PARC") else ''
                geo_ubication.save()

            return
        raise AddressNotFoundException(result)
