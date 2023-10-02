from django.urls import path

from . import views

urlpatterns = [
    path("conversations/<int:id>/", views.ConversationListView.as_view(), name="conversations_recordcard_list"),
    path("conversations/<int:id>/messages/", views.ConversationMessagesListView.as_view(),
         name="conversations_messages_list"),
    path("conversations/<int:id>/mark-as-read/", views.ConversationMarkasReadView.as_view(),
         name="conversations_mark_as_read"),
    path("conversations/messages/add/", views.MessageCreateView.as_view(), name="message_create"),
    path("conversations/notifications/internal/", views.InternalConversationNotifications.as_view(),
         name="notifications_internal"),
    path("conversations/notifications/external/", views.ExternalConversationNotifications.as_view(),
         name="notifications_external"),
    path("conversations/notifications/applicant/", views.ApplicantConversationNotifications.as_view(),
         name="notifications_applicant"),
]
