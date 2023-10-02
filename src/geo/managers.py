from django.db.models import QuerySet


class BoundQuerySet(QuerySet):
    def contains_point(self, etrs_x, etrs_y):
        if etrs_x and etrs_y:
            return self.filter(mpoly__contains=f'POINT({etrs_x} {etrs_y})')
        return self.none()


class AreaCategoryQuerySet(QuerySet):
    def which_update_records(self):
        """
        Returns all the categories set for updating record card fields.
        """
        return self.exclude(ubication_field='')
