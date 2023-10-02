from django.contrib import admin

from communications.models import Conversation, ConversationGroup, ConversationUnreadMessagesGroup, Message


class ConversationGroupInline(admin.TabularInline):
    model = ConversationGroup
    extra = 1


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("type", "record_card", "is_opened", "creation_group")
    list_filter = ("type", "is_opened")
    inlines = (ConversationGroupInline,)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "user_id", "group", "created_at", "record_state", "hash")
    readonly_fields = ("hash", )


@admin.register(ConversationUnreadMessagesGroup)
class ConversationUnreadMessagesGroupAdmin(admin.ModelAdmin):
    list_display = ("conversation", "group", "unread_messages")
