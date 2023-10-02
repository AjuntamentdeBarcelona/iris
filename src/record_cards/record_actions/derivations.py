import logging

from django.conf import settings

from themes.models import DerivationDirect, DerivationDistrict, DerivationPolygon
from record_cards.record_actions.geocode import get_geocoder_class

logger = logging.getLogger(__name__)


def derivate(record_card, next_state_id, next_district_id, is_check=False):
    """

    :param is_check:
    :param record_card: Record Card to derivate
    :param next_state_id: RecordState to derivate
    :param next_district_id: District to derivate
    :return: If derivation group exist, derivation group else None
    """
    derivation_class = get_derivation_class(record_card, next_state_id=next_state_id)
    return derivation_class(record_card, next_state_id, next_district_id, is_check=is_check).get_derivation_group()


def get_derivation_class(record_card, next_state_id):
    if record_card.element_detail.derivationdirect_set.filter(enabled=True, record_state_id=next_state_id,
                                                              group__deleted__isnull=True).exists():
        return DirectDerivation
    return SpatialDerivation


class Derivation:

    def __init__(self, record_card, next_state_id, next_district_id, is_check=False):
        self.record_card = record_card
        self.next_state_id = next_state_id
        self.next_district_id = next_district_id
        self.is_check = is_check

    def get_derivation_group(self):
        """
        :return: Group id to derivate the record card or None if it not exists
        """
        raise NotImplementedError("Derivate method must be implemented")


class DirectDerivation(Derivation):

    def get_derivation_group(self):
        """
        :return: Group id to derivate the record card or None if it not exists
        """
        try:
            return self.record_card.element_detail.derivationdirect_set.only("element_detail_id", "group").get(
                enabled=True, record_state_id=self.next_state_id).group
        except DerivationDirect.DoesNotExist:
            return None


class DistrictDerivation(Derivation):

    def get_derivation_group(self):
        """
        :return: Group id to derivate the record card or None if it not exists
        """
        if not self.next_district_id and (not self.record_card.ubication or self.record_card.ubication.is_empty()):
            return None

        if (not self.record_card.ubication.district or not self.next_district_id) and settings.POLYGON_GEO_BCN:
            try:
                record_card_ubication_geocoder = get_geocoder_class()
                record_card_ubication_geocoder(record_card=self.record_card).update_ubication(commit=not self.is_check)
            except AttributeError as err:
                logger.info(f"{err}, {type(err)}")
                return None
            except BaseException as err:
                logger.info(f"{err}, {type(err)}")
                return None
            if not self.record_card.ubication.district:
                return None

        if not self.next_district_id:
            self.next_district_id = self.record_card.ubication.district_id

        try:
            return self.record_card.element_detail.derivationdistrict_set.only("element_detail_id", "group").get(
                enabled=True, group__deleted__isnull=True, district_id=self.next_district_id,
                record_state_id=self.next_state_id).group
        except DerivationDistrict.DoesNotExist:
            return None


class PolygonDerivation(Derivation):

    all_polygon_code = "_tots"

    def get_derivation_group(self):
        """
        :return: Group id to derivate the record card or None if it not exists
        """
        if not self.record_card.ubication or self.record_card.ubication.is_empty():
            return None

        polygon_derivations = self.record_card.element_detail.derivationpolygon_set.only(
            "element_detail_id", "group", "polygon_code", "zone", "district_mode").select_related("zone").filter(
            enabled=True, group__deleted__isnull=True, record_state_id=self.next_state_id, zone__deleted__isnull=True)
        if not polygon_derivations:
            return None

        polygon_code = self.get_record_polygon_code(polygon_derivations.first())
        if not polygon_code:
            return None

        try:
            return polygon_derivations.get(polygon_code=polygon_code).group
        except DerivationPolygon.DoesNotExist:
            pass

        try:
            return polygon_derivations.get(polygon_code=self.all_polygon_code).group
        except DerivationPolygon.DoesNotExist:
            return None

    def get_record_polygon_code(self, zone):
        if self.record_card.ubication.polygon_code:
            return self.record_card.ubication.polygon_code

        if settings.POLYGON_GEO_BCN:
            polygon_code = self.get_geo_bcn_polygon_code(zone)
            if polygon_code:
                self.record_card.ubication.polygon_code = polygon_code
                if not self.is_check:
                    self.record_card.ubication.save(update_fields=["polygon_code", "updated_at"])
            return polygon_code
        else:
            return None

    def get_geo_bcn_polygon_code(self, derivation) -> str or None:
        """
        Search polygon code with geocoder and geocod services.
        :return: str or None
        """
        zone = derivation.zone
        try:
            record_card_ubication_geocoder = get_geocoder_class()
            geo = record_card_ubication_geocoder(record_card=self.record_card)
            # Find by polygon
            code = geo.get_polygon_code(zone.description)
            if code and derivation.district_mode:
                return self.record_card.ubication.district_id
            return code
        except AttributeError as err:
            logger.info(f"{err}, {type(err)}, couldn't get polygon code.")
            return None
        except BaseException as err:
            logger.info(f"{err}, {type(err)}, couldn't get polygon code.")
            return None


class DummyDerivation(Derivation):
    def __init__(self, return_value, is_check=False, exception=False):
        self.return_value = return_value
        self.is_check = is_check
        self.exception = exception

    def get_derivation_group(self):
        """
        :return: Return value assigned
        """
        if self.exception:
            raise Exception("BROKE DERIVATION")
        return self.return_value


class SpatialDerivation(Derivation):
    SPATIAL_DERIVATION = [PolygonDerivation, DistrictDerivation]

    def __init__(self, record_card, next_state_id, next_district_id, spatial_derivations=None, is_check=False):
        super().__init__(record_card, next_state_id, next_district_id, is_check=is_check)
        self.spatial_derivations = spatial_derivations if spatial_derivations else self.SPATIAL_DERIVATION

    def get_derivation_group(self):
        """
        :return: Group id to derivate the record card or None if it not exists
        """
        try:
            for spatial_derivation in self.spatial_derivations:
                if isinstance(spatial_derivation, DummyDerivation):
                    derivation = spatial_derivation.get_derivation_group()
                else:
                    derivation = spatial_derivation(
                        self.record_card, self.next_state_id, self.next_district_id, is_check=self.is_check
                    ).get_derivation_group()
                if derivation:
                    return derivation
        except Exception as e:
            if self.has_spatial():
                # If not has spatial, we can ignore those exceptions
                logger.exception('GEOCOD EXCEPTION')
                raise e
        return

    def has_spatial(self):
        """
        :return: True if theme has configured any derivation.
        """
        return self.record_card.element_detail.derivationdistrict_set.filter(
            enabled=True, group__deleted__isnull=True, record_state_id=self.next_state_id
        ).exists() or self.record_card.element_detail.derivationpolygon_set.filter(
            enabled=True, group__deleted__isnull=True, record_state_id=self.next_state_id
        ).exists()
