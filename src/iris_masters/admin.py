from django.contrib import admin

from iris_masters.models import (ResponseChannel, RecordType, Parameter, Application, Support, InputChannelSupport,
                                 InputChannel, ApplicantType, InputChannelApplicantType, ResponseChannelSupport,
                                 RecordState, MediaType, CommunicationMedia, Announcement, Process, District,
                                 ResolutionType, Reason, ResponseType, LetterTemplate, FurniturePickUp)


class GenericAdmin(admin.ModelAdmin):
    list_display = ("description", "enabled",)
    list_editable = ("enabled",)


class GenericOrderAdmin(GenericAdmin):
    list_display = GenericAdmin.list_display + ("order",)
    list_editable = GenericAdmin.list_editable + ("order",)


class GenericSoftDeleteAdmin(admin.ModelAdmin):
    list_display = ("description", "deleted")


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    list_display = ("parameter", "name", "description", "category", "valor", "show", "data_type", "visible")
    list_editable = ("show", "data_type", "visible")
    list_filter = ("visible", "category")
    search_fields = ("parameter", "name", "description", "original_description")


@admin.register(RecordType)
class RecordTypeAdmin(admin.ModelAdmin):
    list_display = ("description", "tri", "trt")


@admin.register(RecordState)
class RecordStateAdmin(admin.ModelAdmin):
    list_display = ("description", "enabled",)


class ResponseChannelSupportInline(admin.TabularInline):
    model = ResponseChannelSupport
    extra = 1


@admin.register(ResponseChannel)
class ResponseChannelAdmin(admin.ModelAdmin):
    list_display = ("name", "order")
    inlines = (ResponseChannelSupportInline,)


@admin.register(Application)
class ApplicationAdmin(GenericAdmin):
    list_display = GenericAdmin.list_display + ("description_hash",)
    readonly_fields = ("description_hash",)


class InputChannelApplicantTypeInline(admin.TabularInline):
    model = InputChannelApplicantType
    extra = 1


class InputChannelSupportInline(admin.TabularInline):
    model = InputChannelSupport
    extra = 1


@admin.register(InputChannel)
class InputChannelAdmin(GenericSoftDeleteAdmin):
    inlines = (InputChannelApplicantTypeInline, InputChannelSupportInline)


@admin.register(Support)
class SupportAdmin(GenericSoftDeleteAdmin):
    inlines = (ResponseChannelSupportInline,)


@admin.register(ApplicantType)
class ApplicantTypeAdmin(GenericSoftDeleteAdmin):
    pass


@admin.register(MediaType)
class MediaTypeAdmin(GenericAdmin):
    pass


@admin.register(CommunicationMedia)
class CommunicationMediaAdmin(GenericSoftDeleteAdmin):
    pass


@admin.register(Reason)
class ReasonAdmin(GenericSoftDeleteAdmin):
    pass


@admin.register(ResponseType)
class ResponseTypeAdmin(GenericSoftDeleteAdmin):
    pass


@admin.register(Process)
class ProcessAdmin(admin.ModelAdmin):
    list_display = ("id",)


@admin.register(Announcement)
class AnnouncementAdmin(GenericSoftDeleteAdmin):
    pass


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    readonly_fields = ("id", "name")


@admin.register(LetterTemplate)
class LetterTemplateAdmin(admin.ModelAdmin):
    pass


@admin.register(ResolutionType)
class ResolutionTypeAdmin(GenericSoftDeleteAdmin):
    pass


@admin.register(FurniturePickUp)
class FurniturePickUpAdmin(admin.ModelAdmin):
    pass
