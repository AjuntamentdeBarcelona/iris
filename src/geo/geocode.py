from geo.models import DistrictBorder, AreaCategory, AreaBounds
from record_cards.record_actions.geocode import BaseGeocoder


class GisGeocoder(BaseGeocoder):
    def update_ubication(self, commit=True):
        """
        Tries to set the district and other geoinformation for the record.
        """
        self.ubication.district = self.find_district()
        category_fields = self.update_category_fields()
        if commit:
            self.ubication.save(update_fields=['district', 'xetrs89a', 'yetrs89a'] + category_fields)

    def get_polygon_code(self, polygon, address=None) -> str:
        """
        Returns the code for an AreaCategory polygon.
        """
        cat = AreaCategory.objects.get(codename=polygon)
        bound = self.find_bounds(cat)
        return bound

    def update_category_fields(self) -> list:
        """
        Updates ubication fields related to spatial polygons stored in AreaBounds and by AreaCategory. Each ubication
        field can be set by an AreaCategory. For example, for filling statistical_sector we need to check the AreaBounds
        belonging to an AreaCategory with ubication_field = 'statistical_sector'.
        """
        updated_fields = []
        for cat in AreaCategory.objects.which_update_records():
            value = self.find_bounds(cat)
            updated_fields.append(cat.ubication_field)
            setattr(self.ubication, cat.ubication_field, value)
        return updated_fields

    def find_district(self):
        try:
            district_bound = DistrictBorder.objects.contains_point(
                self.ubication.xetrs89a, self.ubication.yetrs89a
            ).get()
            return district_bound.district
        except DistrictBorder.DoesNotExist:
            pass
        except DistrictBorder.MultipleObjectsReturned:
            self.logger.exception()
            self.logger.error(f"GEOCODE | INVALID BOUNDS | Districts are intersecting")

    def find_bounds(self, cat: AreaCategory):
        try:
            bound = cat.bounds.contains_point(self.ubication.xetrs89a, self.ubication.yetrs89a).get()
            return bound.codename
        except AreaBounds.DoesNotExist:
            pass
        except AreaBounds.MultipleObjectsReturned:
            self.logger.exception()
            self.logger.error(f"GEOCODE | INVALID BOUNDS | {cat.codename} bounds are intersecting")
        return ''
