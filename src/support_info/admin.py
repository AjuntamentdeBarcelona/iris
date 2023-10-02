from django.contrib import admin

from support_info.models import SupportInfo


@admin.register(SupportInfo)
class SupportInfoAdmin(admin.ModelAdmin):
    list_display = ("title", "type", "category")
    list_editable = ("type", "category")
