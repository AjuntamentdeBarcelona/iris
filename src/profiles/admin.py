from django.contrib import admin
from django.conf import settings

from profiles.models import (Group, ApplicationGroup, UserGroup, GroupReassignation, Permission, Profile,
                             ProfilePermissions, PermissionCategory, GroupProfiles, GroupDeleteRegister,
                             GroupInputChannel, GroupsUserGroup, AccessLog, ProfileUserGroup)
from profiles.tasks import (send_next_to_expire_notifications, send_pending_validate_notifications,
                            send_records_pending_communications_notifications)


def rebuild_group_tree(modeladmin, request, queryset):
    Group.objects.rebuild()


rebuild_group_tree.short_description = "Rebuild group tree"


def send_next_expire_notifications(modeladmin, request, queryset):
    send_next_to_expire_notifications.delay()


def send_pendvalidate_notifications(modeladmin, request, queryset):
    send_pending_validate_notifications.delay()


def send_pending_communications_notifications(modeladmin, request, queryset):
    send_records_pending_communications_notifications.delay()


send_next_expire_notifications.short_description = "Send next to expire notifications"
send_pendvalidate_notifications.short_description = "Send pending validate notifications"
send_pending_communications_notifications.short_description = "Send pending communications notifications"


@admin.register(PermissionCategory)
class PermissionCategoryAdmin(admin.ModelAdmin):
    list_display = ("description", "codename")


@admin.register(GroupInputChannel)
class GroupInputChannelAdmin(admin.ModelAdmin):
    list_display = ("group", "input_channel", "enabled")


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("description", "codename", "category")
    list_editable = ("category",)


class ProfilePermissionsInline(admin.TabularInline):
    model = ProfilePermissions
    extra = 1


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("description",)
    inlines = (ProfilePermissionsInline,)


class GroupInputChannelInline(admin.TabularInline):
    model = GroupInputChannel
    extra = 1


class GroupProfilesInline(admin.TabularInline):
    model = GroupProfiles
    extra = 1


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    if settings.CITIZEN_ND_ENABLED:
        list_display = (
            "description", "group_plate", "deleted", "no_reasigned", "citizen_nd", "certificate", "is_ambit",
            "parent", "records_next_expire", "records_next_expire_freq", "records_allocation", "pend_records",
            "pend_records_freq")
        list_editable = ("no_reasigned", "citizen_nd", "certificate", "is_ambit", "parent", "records_next_expire",
                         "records_next_expire_freq", "records_allocation", "pend_records", "pend_records_freq")
    else:
        list_display = (
            "description", "group_plate", "deleted", "no_reasigned", "certificate", "is_ambit",
            "parent", "records_next_expire", "records_next_expire_freq", "records_allocation", "pend_records",
            "pend_records_freq")
        list_editable = ("no_reasigned", "certificate", "is_ambit", "parent", "records_next_expire",
                         "records_next_expire_freq", "records_allocation", "pend_records", "pend_records_freq")
        exclude = ("citizen_nd",)
    actions = [rebuild_group_tree, send_next_expire_notifications, send_pendvalidate_notifications,
               send_pending_communications_notifications]
    inlines = (GroupInputChannelInline, GroupProfilesInline)


@admin.register(ApplicationGroup)
class ApplicationGroupAdmin(admin.ModelAdmin):
    list_display = ("application", "group", "enabled")
    list_editable = ("enabled",)


class GroupsUserGroupInline(admin.TabularInline):
    model = GroupsUserGroup
    extra = 1


class ProfileUserGroupInline(admin.TabularInline):
    model = ProfileUserGroup
    extra = 1


@admin.register(UserGroup)
class UserGroupAdmin(admin.ModelAdmin):
    list_display = ("user", "group")
    inlines = (GroupsUserGroupInline, ProfileUserGroupInline)


@admin.register(GroupReassignation)
class GroupReassignationAdmin(admin.ModelAdmin):
    list_display = ("origin_group", "reasign_group", "enabled")
    list_editable = ("enabled",)


@admin.register(GroupDeleteRegister)
class GroupDeleteRegisterAdmin(admin.ModelAdmin):
    list_display = ("deleted_group", "reasignation_group", "only_open", "process_finished")


@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ("user_group", "group", "created_at")
