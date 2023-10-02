import pytest
from model_mommy import mommy

from communications.models import Conversation, Message, ConversationUnreadMessagesGroup
from profiles.tests.utils import create_groups
from record_cards.record_actions.conversations_alarms import RecordCardConversationAlarms
from record_cards.tests.utils import CreateRecordCardMixin


@pytest.mark.django_db
class TestRecordCardConversationAlarms(CreateRecordCardMixin):

    @pytest.mark.parametrize("conversations,excluded_convs", ((0, 3), (1, 0), (0, 0), (3, 3)))
    def test_set_conversations(self, conversations, excluded_convs):
        dair, parent, _, _, _, _ = create_groups()
        record_card = self.create_record_card(responsible_profile=dair)

        [mommy.make(Conversation, is_opened=True, type=Conversation.APPLICANT, record_card=record_card,
                    creation_group=record_card.responsible_profile, user_id="asdads") for _ in range(conversations)]

        excluded_ids = [mommy.make(Conversation, is_opened=True, type=Conversation.APPLICANT, record_card=record_card,
                                   creation_group=record_card.responsible_profile, user_id="asdads").pk
                        for _ in range(excluded_convs)]
        conversation_alarms = RecordCardConversationAlarms(record_card, [Conversation.APPLICANT], excluded_ids)
        assert conversation_alarms.opened_conversations.count() == conversations

    @pytest.mark.parametrize("notification", (True, False))
    def test_response_to_responsible(self, notification):
        dair, parent, _, _, _, _ = create_groups()
        record_card = self.create_record_card(responsible_profile=dair)

        conversation = mommy.make(Conversation, is_opened=True, type=Conversation.APPLICANT, record_card=record_card,
                                  creation_group=record_card.responsible_profile, user_id="asdads")

        if notification:
            ConversationUnreadMessagesGroup.objects.create(group=record_card.responsible_profile,
                                                           conversation=conversation, unread_messages=3)

        conversation_alarms = RecordCardConversationAlarms(record_card, [Conversation.APPLICANT])

        if notification:
            assert conversation_alarms.response_to_responsible is True
        else:
            assert conversation_alarms.response_to_responsible is False

    @pytest.mark.parametrize("responsible_message", (True, False))
    def test_pend_response_responsible(self, responsible_message):
        dair, parent, _, _, _, _ = create_groups()
        record_card = self.create_record_card(responsible_profile=dair)

        conversation = mommy.make(Conversation, is_opened=True, type=Conversation.APPLICANT, record_card=record_card,
                                  creation_group=record_card.responsible_profile, user_id="asdads")

        if responsible_message:
            Message.objects.create(conversation=conversation, group=dair, record_state_id=record_card.record_state_id,
                                   text="text message", user_id="asdads")
        else:
            Message.objects.create(conversation=conversation, group=parent, record_state_id=record_card.record_state_id,
                                   text="text message", user_id="asdads")

        conversation_alarms = RecordCardConversationAlarms(record_card, [Conversation.APPLICANT])

        if responsible_message:
            assert conversation_alarms.pend_response_responsible is True
        else:
            assert conversation_alarms.pend_response_responsible is False
