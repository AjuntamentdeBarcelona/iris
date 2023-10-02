from django.contrib.gis.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from geo.managers import BoundQuerySet, AreaCategoryQuerySet
from iris_masters.models import District
from themes.models import Zone


class DistrictBorder(models.Model):
    """
    Maps the geographic bounds of the districts or sections in which the city/political area is divided.
    """
    name = models.CharField(max_length=50)
    district = models.ForeignKey(District, on_delete=models.PROTECT)
    mpoly = models.MultiPolygonField(srid=settings.GEO_SRID)

    objects = BoundQuerySet.as_manager()

    def __str__(self):
        return self.name


class AreaCategory(Zone):
    """
    We can classify records in several types of areas. Each theme has to configure them.
    """
    ubication_field = models.CharField(
        max_length=30,
        verbose_name=_('Record Card field'),
        help_text=_('Ubication field to fill with the bound result.'),
        blank=True,
        default=''
    )

    objects = AreaCategoryQuerySet.as_manager()


class AreaBounds(models.Model):
    name = models.CharField(max_length=50)
    category = models.ForeignKey(AreaCategory, related_name='bounds', on_delete=models.PROTECT)
    codename = models.CharField(max_length=3)
    mpoly = models.MultiPolygonField(srid=settings.GEO_SRID)

    objects = BoundQuerySet.as_manager()
