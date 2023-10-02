from django.contrib.gis.admin.options import OSMGeoAdmin
from django.contrib import admin
from geo.models import AreaBounds, AreaCategory, DistrictBorder


@admin.register(DistrictBorder)
class DistrictBorderAdmin(OSMGeoAdmin):
    display_wkt = True
    search_fields = ('name',)
    list_filter = ('district',)
    list_display = ('name', 'district', 'mpoly',)
    fields = ('name', 'district', 'mpoly',)


@admin.register(AreaCategory)
class AreaCategoryAdmin(admin.ModelAdmin):
    search_fields = ('ubication_field',)
    list_display = ('ubication_field',)


@admin.register(AreaBounds)
class AreaBoundsAdmin(OSMGeoAdmin):
    display_wkt = True
    search_fields = ('name', 'codename',)
    list_filter = ('category',)
    list_display = ('name', 'category', 'codename', 'mpoly',)
