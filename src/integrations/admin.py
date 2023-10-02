from django.contrib import admin

from integrations.tasks import generate_open_data_report
from integrations import models


@admin.register(models.ExternalRecordId)
class ExternalRecordIdAdmin(admin.ModelAdmin):
    search_fields = ('record_card__id', 'record_card__normalized_record_id', 'external_code')
    list_filter = ('service', )
    list_display = ('service', 'normalized_record_id', 'external_code')
    actions = ('generate_open_data_report', )

    def normalized_record_id(self, obj):
        return obj.record_card.normalized_record_id

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('record_card', 'service')

    def generate_open_data_report(self, request, qs):
        generate_open_data_report.delay()


admin.site.register(models.ExternalService)
admin.site.register(models.BatchFile)
admin.site.register(models.GpoHistoric)
admin.site.register(models.GpoIndicators)
admin.site.register(models.BiirisFilesExtractionDetail)
admin.site.register(models.GpoSect)
