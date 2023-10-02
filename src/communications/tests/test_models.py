import pytest
from datetime import timedelta
from mock import patch, Mock
from model_mommy import mommy

from django.utils import timezone

from communications.models import Conversation, ConversationUnreadMessagesGroup, Message
from iris_masters.models import RecordState
from profiles.models import Group
from profiles.tests.utils import create_groups
from record_cards.tests.utils import CreateRecordCardMixin
from communications.tests.utils import load_missing_data
import logging

logger = logging.getLogger(__name__)


@pytest.mark.django_db
class TestConversation(CreateRecordCardMixin):

    @pytest.mark.parametrize("create_conversation_unread,message_number,expected_unread_messages", (
            (True, 3, 5),
            (False, 5, 0),
            (False, 0, 0),
    ))
    def test_unread_messages_by_group(self, create_conversation_unread, message_number, expected_unread_messages):
        load_missing_data()
        record_card = self.create_record_card()
        conversation = mommy.make(Conversation, user_id="2222", record_card=record_card)
        _, group, _, _, _, _ = create_groups()
        if create_conversation_unread:
            ConversationUnreadMessagesGroup.objects.create(conversation=conversation, group=group,
                                                           unread_messages=expected_unread_messages)

        for _ in range(message_number):
            mommy.make(Message, user_id="2222", conversation=conversation, group=group,
                       record_state_id=RecordState.PENDING_VALIDATE)
        assert conversation.unread_messages_by_group(group) == expected_unread_messages

    @pytest.mark.parametrize("initial_res_unread,expected_res_unread,initial_group_unread,expected_group_unread", (
            (0, 0, 0, 1),
            (3, 3, 3, 4),
            (5, 5, 0, 1),
    ))
    def test_update_unread_messages(self, initial_res_unread, expected_res_unread, initial_group_unread,
                                    expected_group_unread):
        load_missing_data()
        record_card = self.create_record_card()
        conversation = mommy.make(Conversation, user_id="2222", record_card=record_card)

        ConversationUnreadMessagesGroup.objects.create(
            conversation=conversation, group=record_card.responsible_profile, unread_messages=initial_res_unread)
        group = mommy.make(Group, user_id="222", profile_ctrl_user_id="2222")
        ConversationUnreadMessagesGroup.objects.create(
            conversation=conversation, group=group, unread_messages=initial_group_unread)

        internal_conversation_groups = Mock(return_value=[group.id])
        with patch("communications.managers.ConversationManager.internal_conversation_groups",
                   internal_conversation_groups):
            conversation.update_unread_messages(record_card.responsible_profile)
            assert ConversationUnreadMessagesGroup.objects.get(
                conversation=conversation,
                group=record_card.responsible_profile).unread_messages == expected_res_unread
            assert ConversationUnreadMessagesGroup.objects.get(
                conversation=conversation,
                group=group).unread_messages == expected_group_unread

    @pytest.mark.parametrize("unread_messages", (0, 1, 5))
    def test_reset_unread_messages_bygroup(self, unread_messages):
        load_missing_data()
        record_card = self.create_record_card()
        conversation = mommy.make(Conversation, user_id="2222", record_card=record_card)
        ConversationUnreadMessagesGroup.objects.create(
            conversation=conversation, group=record_card.responsible_profile, unread_messages=unread_messages)
        conversation.reset_unread_messages_bygroup(record_card.responsible_profile)
        assert ConversationUnreadMessagesGroup.all_objects.get(
            conversation=conversation, group=record_card.responsible_profile).unread_messages == unread_messages


@pytest.mark.django_db
class TestMessage(CreateRecordCardMixin):

    @pytest.mark.parametrize("conv_type", (Conversation.INTERNAL, Conversation.EXTERNAL, Conversation.APPLICANT))
    def test_message_hash(self, conv_type):
        load_missing_data()
        record_card = self.create_record_card()
        conversation = mommy.make(Conversation, user_id="2222", record_card=record_card, type=conv_type)
        message = Message.objects.create(conversation=conversation, group=record_card.responsible_profile,
                                         record_state_id=RecordState.PENDING_VALIDATE, text="text")
        if conv_type in Conversation.HASH_TYPES:
            assert message.hash
        else:
            assert not message.hash

    @pytest.mark.parametrize("is_answered,expire,response_time_expired", (
            (True, False, False),
            (False, False, False),
            (False, True, True),
    ))
    def test_response_time_expired(self, is_answered, expire, response_time_expired):
        load_missing_data()
        record_card = self.create_record_card()
        conversation = mommy.make(Conversation, user_id="2222", record_card=record_card, type=Conversation.APPLICANT)
        message = Message.objects.create(conversation=conversation, group=record_card.responsible_profile,
                                         record_state_id=RecordState.PENDING_VALIDATE, text="text",
                                         is_answered=is_answered)
        if expire:
            message.created_at = timezone.now() - timedelta(days=10)
        assert message.response_time_expired is response_time_expired
