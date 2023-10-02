from django.contrib import admin

from record_cards.models import (Ubication, Citizen, SocialEntity, Applicant, ApplicantResponse, Request, RecordCard,
                                 RecordCardFeatures, RecordCardSpecialFeatures, RecordCardHistory, Comment,
                                 RecordCardResponse, RecordCardStateHistory, RecordCardTextResponse, Workflow,
                                 WorkflowComment, WorkflowResolution, RecordFile, RecordCardBlock, WorkflowPlan,
                                 RecordCardReasignation, RecordChunkedFile, MonthIndicator, InternalOperator,
                                 RecordCardAudit, RecordCardTextResponseFiles, ExtendedGeocodeUbication)
from main.tasks import celery_test_task


@admin.register(Ubication)
class UbicationAdmin(admin.ModelAdmin):
    list_display = ("via_type", "street", "enabled", "nexus", "numbering_type")
    list_editable = ("enabled", "nexus", "numbering_type")


@admin.register(ExtendedGeocodeUbication)
class ExtendedGeocodeUbicationAdmin(admin.ModelAdmin):
    list_display = ("ubication_id", "llepost_f")
    readonly_fields = ("ubication", )


@admin.register(Citizen)
class CitizenAdmin(admin.ModelAdmin):
    list_display = ("name", "first_surname", "dni", "response", "deleted", "doc_type", "blocked")
    list_editable = ("response", "doc_type", "blocked")


@admin.register(SocialEntity)
class SocialEntityAdmin(admin.ModelAdmin):
    list_display = ("social_reason", "contact", "cif", "response", "deleted", "blocked")
    list_editable = ("response", "blocked")


@admin.register(Applicant)
class ApplicantAdmin(admin.ModelAdmin):
    list_display = ("citizen", "social_entity", "flag_ca", "deleted")
    list_editable = ("flag_ca",)


@admin.register(InternalOperator)
class InternalOperatorAdmin(admin.ModelAdmin):
    list_display = ("document", "input_channel", "applicant_type")
    list_editable = ("input_channel", "applicant_type")


@admin.register(ApplicantResponse)
class ApplicantResponseAdmin(admin.ModelAdmin):
    list_display = ("applicant", "street", "number", "language", "response_channel", "enabled", "authorization")
    list_editable = ("number", "language", "enabled", "authorization")


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = ("applicant", "applicant_type", "application", "input_channel", "communication_media", "enabled",
                    "normalized_id")
    list_editable = ("enabled",)


class RecordCardFeaturesInline(admin.TabularInline):
    model = RecordCardFeatures
    extra = 1


class RecordCardSpecialFeaturesInline(admin.TabularInline):
    model = RecordCardSpecialFeatures
    extra = 1


def test_celery(modeladmin, request, queryset):
    celery_test_task.delay()


test_celery.short_description = "Test celery task"


@admin.register(RecordCard)
class RecordCardAdmin(admin.ModelAdmin):
    list_display = ("__str__", "created_at", "enabled", "alarm", "urgent", "ans_limit_date", "record_state", "process",
                    "responsible_profile")
    list_filter = ("record_state", "urgent")
    list_editable = ("alarm", "urgent", "ans_limit_date", "process", "responsible_profile")
    readonly_fields = ("request", "record_parent_claimed", "process", "multirecord_from", "possible_similar_records",
                       "workflow")
    exclude = ["possible_similar_records", "possible_similar"]
    inlines = (RecordCardFeaturesInline, RecordCardSpecialFeaturesInline)
    actions = [test_celery]


@admin.register(RecordCardFeatures)
class RecordCardFeaturesAdmin(admin.ModelAdmin):
    list_display = ("record_card", "feature", "value", "enabled", "is_theme_feature")


@admin.register(RecordCardSpecialFeatures)
class RecordCardSpecialFeaturesAdmin(admin.ModelAdmin):
    list_display = ("record_card", "feature", "value", "enabled", "is_theme_feature")


@admin.register(RecordCardHistory)
class RecordCardHistoryAdmin(admin.ModelAdmin):
    list_display = ("record_card", "element_detail", "request", "record_state", "record_type", "enabled", "alarm",
                    "responsible_profile", "ans_limit_date", "closing_date")
    readonly_fields = ("record_card", "description", "element_detail", "request", "responsible_profile", "ubication",
                       "process", "record_state", "record_type", "enabled", "mayorship", "normalized_record_id",
                       "alarm", "applicant_type", "auxiliary", "closing_date", "ans_limit_date",
                       "communication_media", "communication_media_date", "notify_quality",
                       "communication_media_detail", "support", "lopd", "record_parent_claimed", "similar_process",
                       "reassignment_not_allowed", "urgent", "page_origin", "email_external_derivation",
                       "user_displayed", "historicized", "multi_complaint", "allow_multiderivation", "response_state",
                       "start_date_process")


@admin.register(RecordCardStateHistory)
class RecordCardStateHistoryAdmin(admin.ModelAdmin):
    list_display = ("record_card_id", "previous_state", "next_state", "record_card_created_at", "created_at",
                    "user_id", "group")
    readonly_fields = ("record_card", "previous_state", "next_state", "created_at", "user_id", "updated_at", "group")


@admin.register(RecordCardBlock)
class RecordCardBlockAdmin(admin.ModelAdmin):
    list_display = ("record_card", "user_id", "expire_time")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("record_card", "enabled", "reason", "created_at")
    list_editable = ("enabled",)
    date_hierarchy = "created_at"


@admin.register(RecordCardResponse)
class RecordCardResponseAdmin(admin.ModelAdmin):
    list_display = ("record_card", "response_channel", "address_mobile_email", "answered", "enabled",
                    "correct_response_data")
    list_editable = ("response_channel", "answered", "enabled", "correct_response_data")


@admin.register(RecordCardTextResponse)
class RecordCardTextResponseAdmin(admin.ModelAdmin):
    list_display = ("record_card", "send_date", "text_date", "enabled")
    list_editable = ("enabled",)


@admin.register(RecordCardTextResponseFiles)
class RecordCardTextResponseFilesAdmin(admin.ModelAdmin):
    list_display = ("text_response", "record_file", "enabled")


@admin.register(RecordFile)
class RecordFileAdmin(admin.ModelAdmin):
    list_display = ("pk", "record_card", "file")


@admin.register(RecordCardReasignation)
class RecordCardReasignationAdmin(admin.ModelAdmin):
    list_display = ("record_card", "group", "previous_responsible_profile", "next_responsible_profile", "reason")


@admin.register(RecordCardAudit)
class RecordCardAuditAdmin(admin.ModelAdmin):
    list_display = ("record_card", "validation_user", "planif_user", "resol_user", "close_user")


@admin.register(RecordChunkedFile)
class RecordChunkedFileAdmin(admin.ModelAdmin):
    pass


@admin.register(MonthIndicator)
class MonthIndicatorAdmin(admin.ModelAdmin):
    list_display = ("__str__", "entries", "pending_validation", "processing", "closed", "cancelled",
                    "external_processing", "pending_records", "average_close_days", "average_age_days")
    readonly_fields = ("group", "year", "month", "pending_validation", "processing", "closed", "cancelled",
                       "external_processing", "pending_records", "average_close_days", "average_age_days")


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ("main_record_card", "state", "enabled", "close_date", "element_detail_modified")
    list_editable = ("enabled", "element_detail_modified")


@admin.register(WorkflowComment)
class WorkflowCommentAdmin(admin.ModelAdmin):
    list_display = ("workflow", "enabled", "task")
    list_editable = ("enabled",)


@admin.register(WorkflowPlan)
class WorkflowPlanAdmin(admin.ModelAdmin):
    list_display = ("workflow", "responsible_profile", "start_date_process", "action_required")


@admin.register(WorkflowResolution)
class WorkflowResolutionAdmin(admin.ModelAdmin):
    list_display = ("__str__", "service_person_incharge", "resolution_type", "resolution_date")
