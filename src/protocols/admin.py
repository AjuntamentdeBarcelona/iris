from django.contrib import admin
from protocols.models import Protocols


@admin.register(Protocols)
class ProtocolsAdmin(admin.ModelAdmin):
    list_display = ("id", "protocol_id", "description", "short_description", "deleted")
