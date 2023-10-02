from django.contrib import admin

from safedelete.admin import SafeDeleteAdmin, highlight_deleted

from themes.tasks import rebuild_theme_tree
from themes import models


@admin.register(models.Element)
class ElementAdmin(admin.ModelAdmin):
    list_display = ("description", "order", "is_favorite")
    list_editable = ("is_favorite",)


@admin.register(models.Area)
class AreaAdmin(SafeDeleteAdmin):
    list_display = (highlight_deleted, "description", "order") + SafeDeleteAdmin.list_display
    list_filter = ("description",) + SafeDeleteAdmin.list_filter


@admin.register(models.Keyword)
class KeywordAdmin(admin.ModelAdmin):
    list_display = ("description", "enabled", "user_id")


class ApplicationElementDetailInline(admin.TabularInline):
    model = models.ApplicationElementDetail
    extra = 1


class ElementDetailFeatureInline(admin.TabularInline):
    model = models.ElementDetailFeature
    extra = 1


class ElementDetailResponseChannelInline(admin.TabularInline):
    model = models.ElementDetailResponseChannel
    extra = 1


class DerivationDirectInline(admin.TabularInline):
    model = models.DerivationDirect
    extra = 1


class DerivationDistrictInline(admin.TabularInline):
    model = models.DerivationDistrict
    extra = 1


class DerivationPolygonInline(admin.TabularInline):
    model = models.DerivationPolygon
    extra = 1


class GroupProfileElementDetailInline(admin.TabularInline):
    model = models.GroupProfileElementDetail
    extra = 1


@admin.register(models.ElementDetail)
class ElementDetailAdmin(admin.ModelAdmin):
    list_display = ("element", "detail_code", "short_description", "order")
    inlines = (ApplicationElementDetailInline, ElementDetailFeatureInline, ElementDetailResponseChannelInline,
               DerivationDirectInline, DerivationDistrictInline, DerivationPolygonInline,
               GroupProfileElementDetailInline)
    actions = (rebuild_theme_tree,)

    def rebuild_tree(self, *args, **kwargs):
        rebuild_theme_tree.delay()


@admin.register(models.ThemeGroup)
class ThemeGroupAdmin(admin.ModelAdmin):
    pass


@admin.register(models.ElementDetailGroup)
class ElementDetailGroupAdmin(admin.ModelAdmin):
    list_display = ("element_detail", "group")


@admin.register(models.ElementDetailDeleteRegister)
class ElementDetailDeleteRegisterAdmin(admin.ModelAdmin):
    list_display = ("group", "deleted_detail", "reasignation_detail", "only_open", "process_finished")
    readonly_fields = ("group", "deleted_detail", "reasignation_detail", "only_open", "process_finished")


@admin.register(models.Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ("description", "deleted")
