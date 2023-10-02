from django.contrib import admin
from iris_templates.models import IrisTemplate, IrisTemplateRecordTypes


class IrisTemplateRecordTypesInline(admin.TabularInline):
    model = IrisTemplateRecordTypes
    extra = 1


@admin.register(IrisTemplate)
class IrisTemplateAdmin(admin.ModelAdmin):
    list_display = ('description', 'response_type')
    inlines = [IrisTemplateRecordTypesInline]
