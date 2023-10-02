from django.contrib import admin
from ariadna.models import Ariadna, AriadnaRecord


@admin.register(Ariadna)
class AriadnaAdmin(admin.ModelAdmin):
    pass


@admin.register(AriadnaRecord)
class AriadnaRecordAdmin(admin.ModelAdmin):
    pass
