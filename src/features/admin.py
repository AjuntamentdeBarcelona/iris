from django.contrib import admin

from iris_masters.admin import GenericSoftDeleteAdmin
from features.models import ValuesType, Values, Feature, Mask


@admin.register(ValuesType)
class ValuesTypeAdmin(GenericSoftDeleteAdmin):
    pass


@admin.register(Values)
class ValuesAdmin(GenericSoftDeleteAdmin):
    pass


@admin.register(Mask)
class MaskAdmin(admin.ModelAdmin):
    list_display = ("id", "description", "type")
    readonly_fields = ("id", "description")


@admin.register(Feature)
class FeatureAdmin(GenericSoftDeleteAdmin):
    pass
