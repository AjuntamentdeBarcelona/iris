from bs4 import BeautifulSoup

from django.conf import settings
from django.utils import translation
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework.exceptions import ValidationError, ParseError
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import IsAuthenticated

from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.status import (HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND,
                                   HTTP_409_CONFLICT, HTTP_403_FORBIDDEN)
from rest_framework.views import APIView

from communications.models import Conversation, Message, ConversationUnreadMessagesGroup
from communications.serializers import (ConversationSerializer, MessageSerializer, MessageCreateSerializer,
                                        ConversationUnreadMessagesGroupSerializer)
from emails.emails import ResponseHashMessageEmail
from iris_masters.models import RecordState, Parameter
from iris_masters.views import BasicMasterListApiView
from iris_templates.answer import get_signature
from iris_templates.data_checks.visible_parameters import CARTA_ICONA
from main.api.pagination import MessagesPagination
from main.api.schemas import create_swagger_auto_schema_factory
from profiles.permissions import IrisPermission
from record_cards.models import RecordCard
from record_cards.permissions import RECARD_NOTIFICATIONS
from record_cards.record_actions.alarms import RecordCardAlarms
from record_cards.record_actions.conversations_alarms import RecordCardConversationAlarms
from record_cards.views import CheckRecordCardPermissionsMixin, RecordCardRestrictedConversationPermissionsMixin

ANSWER_LINK_TAG = "link_resposta"
AJUNTAMENT_ICON_TAG = "icona_ajuntament"


class ConversationListView(BasicMasterListApiView):
    """
    Retrieve the list of conversations of a given RecordCard (id)
    """

    serializer_class = ConversationSerializer

    def get_queryset(self):
        return Conversation.objects.filter(record_card_id=self.kwargs["id"]).prefetch_related("conversationgroup_set")


class ConversationMessagesListView(BasicMasterListApiView):
    """
    Retrieve the list of messages of a given conversation (id)
    """

    serializer_class = MessageSerializer
    pagination_class = MessagesPagination

    def get_queryset(self):
        """
        Update conversations alarms, unread notifications and retrieve the messages list from a conversation

        :return:
        """
        conversation = get_object_or_404(Conversation, id=self.kwargs["id"])
        self.update_conversation_alarms_notifications(conversation)
        return Message.objects.filter(conversation=conversation).select_related("group", "record_state")

    def update_conversation_alarms_notifications(self, conversation):
        """
        Update conversation alarms (applicant response and response to responsible) and remove the unread notification
        """
        group = self.request.user.usergroup.group
        unread, created = ConversationUnreadMessagesGroup.objects.get_or_create(conversation=conversation, group=group)
        if not created and unread.unread_messages > 0 and group == conversation.record_card.responsible_profile:
            self.check_response_alarm(conversation, [Conversation.APPLICANT], "applicant_response")
            self.check_response_alarm(conversation, [Conversation.INTERNAL, Conversation.EXTERNAL],
                                      "response_to_responsible")
            record_alarms = RecordCardAlarms(conversation.record_card, group)
            conversation.record_card.alarm = record_alarms.check_alarms(
                ["applicant_response", "response_to_responsible"])
            conversation.record_card.save(update_fields=["applicant_response", "response_to_responsible", "alarm"])

        unread.delete()

    @staticmethod
    def check_response_alarm(conversation, conversation_types, alarm_indicator):
        conversation_alarms = RecordCardConversationAlarms(conversation.record_card, conversation_types,
                                                           [conversation.pk])
        setattr(conversation.record_card, alarm_indicator, conversation_alarms.response_to_responsible)


@method_decorator(name="post", decorator=swagger_auto_schema(
    responses={
        HTTP_200_OK: "Conversation marked as read",
        HTTP_400_BAD_REQUEST: "Bad Request - Group is not involved on conversation",
        HTTP_404_NOT_FOUND: "Conversation not found",
    }
))
class ConversationMarkasReadView(APIView):
    """
    Set a given conversation as read by a given group, if it's involved in it.
    """

    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        conversation = get_object_or_404(Conversation, id=self.kwargs["id"])
        group = self.request.user.usergroup.group
        # Conversation can only be created by recordCard responsible profile.
        # Then, a group involved in conversation will be the creator or will be included in the groups_involved
        if group != conversation.creation_group and group not in conversation.groups_involved.all():
            raise ParseError(detail=_("User's group is not involved in conversation"), code="invalid")

        conversation.reset_unread_messages_bygroup(group)
        return Response(data={}, status=HTTP_200_OK)


class BaseNotiticationsView(BasicMasterListApiView):
    serializer_class = ConversationUnreadMessagesGroupSerializer
    conversation_type = None

    def get_permissions(self):
        return [IsAuthenticated(), IrisPermission(RECARD_NOTIFICATIONS), ]

    def get_queryset(self):
        return ConversationUnreadMessagesGroup.objects.filter(
            conversation__is_opened=True, group=self.request.user.usergroup.group,
            conversation__type=self.get_conversation_type()).order_by("created_at").select_related(
            "conversation", "conversation__record_card")

    def get_conversation_type(self):
        if not self.conversation_type and self.conversation_type != Conversation.INTERNAL:
            raise Exception("Set conversation type")
        return self.conversation_type


class InternalConversationNotifications(BaseNotiticationsView):
    """
    Get the list of the INTERNAL conversations pending to read for the user's group
    """
    conversation_type = Conversation.INTERNAL


class ExternalConversationNotifications(BaseNotiticationsView):
    """
    Get the list of the EXTERNAL conversations pending to read for the user's group
    """
    conversation_type = Conversation.EXTERNAL


class ApplicantConversationNotifications(BaseNotiticationsView):
    """
    Get the list of the APPLICANT conversations pending to read for the user's group
    """
    conversation_type = Conversation.APPLICANT


@method_decorator(name="post", decorator=create_swagger_auto_schema_factory(MessageCreateSerializer, responses={
    HTTP_201_CREATED: MessageCreateSerializer,
    HTTP_400_BAD_REQUEST: "Bad request: Validation Error",
    HTTP_403_FORBIDDEN: "Acces not allowed",
    HTTP_409_CONFLICT: "Action can not be done with a closed or cancelled record",
}))
class MessageCreateView(RecordCardRestrictedConversationPermissionsMixin, CheckRecordCardPermissionsMixin,
                        CreateAPIView):
    """
    Create a new message in a conversation.
    If it's the first message in a new conversation, the information to create the conversation must be sent.
    Only the responsible profile of the RecordCard can open new conversations.
    - If conversation type is INTERNAL, the list of the involved groups is required.
    - If conversation type is EXTERNAL, the external email is required
    - For a conversation of type APPLICANT, the response channel of the response of the RecordCard must be EMAIL

    A user can create a message in a conversation if it's involved on it. A user is involved on a conversation if
    its group is the creator of the conversation, or it's inside the involved groups.

    When the messages are for a person without acces to IRIS, an email will be sent. This emails can have
     attached files.
    """
    serializer_class = MessageCreateSerializer
    permission_classes = (IsAuthenticated,)

    def create(self, request, *args, **kwargs):
        serializer_data = request.data
        self.set_record_state_id(serializer_data)
        serializer = self.get_serializer(data=serializer_data)
        permissions_response = self.check_record_card_permissions(request, serializer)
        if permissions_response:
            return permissions_response

        record_card = self.get_record_from_data(serializer_data)
        if record_card.record_state_id in RecordState.CLOSED_STATES:
            return Response(_("Action can not be done with a closed or cancelled record"), status=HTTP_409_CONFLICT)

        serializer.is_valid(raise_exception=True)
        message = self.perform_create(serializer)
        response_data = MessageSerializer(message).data
        headers = self.get_success_headers(response_data)
        return Response(response_data, status=HTTP_201_CREATED, headers=headers)

    def get_record_card(self, serializer):
        return self.get_record_from_data(serializer.initial_data)

    @staticmethod
    def get_record_from_data(data):
        try:
            conversation = Conversation.objects.select_related("record_card").get(pk=data.get("conversation_id"))
            return conversation.record_card
        except Conversation.DoesNotExist:
            try:
                return RecordCard.objects.get(pk=data.get("record_card_id"))
            except RecordCard.DoesNotExist:
                raise ValidationError(_("No RecordCard matches the given query."))

    def set_record_state_id(self, serializer_data):
        """
        Set the current record state id from record card of the conversation on the data to the serializer
        :param serializer_data:
        :return:
        """

        serializer_data["record_state_id"] = self.get_record_from_data(serializer_data).record_state_id

    def perform_create(self, serializer):
        message = serializer.save()
        if message.conversation.type in Conversation.HASH_TYPES:
            old_lang = translation.get_language()
            try:
                lang = message.conversation.record_card.recordcardresponse.language
            except AttributeError:
                lang = settings.LANGUAGE_CODE
            translation.activate(lang)

            mail_context = self.set_mail_context(message, lang)
            attachments = self.set_attachments(serializer)
            to_email = self.get_to_email(message)
            ResponseHashMessageEmail().send(from_email=settings.DEFAULT_FROM_EMAIL, to=(to_email,),
                                            extra_context=mail_context, attachments=attachments)
            translation.activate(old_lang)
        return message

    def get_to_email(self, message) -> str:
        if message.conversation.type == Conversation.EXTERNAL:
            return message.conversation.external_email
        return message.conversation.record_card.recordcardresponse.address_mobile_email

    def set_attachments(self, serializer) -> list:
        attach_record_files = serializer.validated_data.get("record_files", [])
        attachments = []

        for attachment in attach_record_files:
            attachments.append({"filename": attachment.filename, "attachment": attachment.file.read()})
        return attachments

    def set_mail_context(self, message, lang) -> dict:

        com_external_url = Parameter.get_parameter_by_key("URL_COMMUNICACIONS_EXTERNES",
                                                          "https://atencioenlinia.bcn.cat/fitxa/solicitud-informacio")
        answer_url = f"{com_external_url}?request={message.conversation.record_card.normalized_record_id}" \
                     f"&hash={message.hash}"

        mail_context = {
            "text": self.set_mail_text(message, answer_url),
            "answer_url": answer_url,
            "show_header": False,
            "record_card": message.conversation.record_card
        }
        if message.conversation.type == Conversation.EXTERNAL:
            signature = get_signature(self.request.user.usergroup.group, lang)
            signature = self.replace_icon_tag(signature)
            mail_context.update({
                "signature": signature.replace('icona_grup', ''),
                "show_link": True,
                "show_header": True,
                "require_answer": message.conversation.require_answer,
            })
        return mail_context

    def set_mail_text(self, message, answer_url):
        mail_text = message.text.replace(ANSWER_LINK_TAG,
                                         f"<a href=\"{answer_url}\" target=\"_blank\">{answer_url}</a>")
        mail_text = self.replace_icon_tag(mail_text)
        soup = BeautifulSoup(mail_text, 'html.parser')
        mail_text = soup.prettify()
        return mail_text

    @staticmethod
    def replace_icon_tag(mail_text):
        image_link = Parameter.get_parameter_by_key(CARTA_ICONA,
                                                    "http://w10.bcn.es/StpQueixesWEB/imatges/AJSignatura.gif")
        return mail_text.replace(AJUNTAMENT_ICON_TAG, f"<img src=\"{image_link}\" alt=\"Ajuntament de Barcelona\" />")
