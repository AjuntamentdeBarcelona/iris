from communications.models import Conversation, ConversationUnreadMessagesGroup


class RecordCardConversationAlarms:

    def __init__(self, record_card, conversation_types, exclude_conversations=None):
        """

        :param record_card: record to check conversations alarms
        :param conversation_types: list of conversations types to check
        :param exclude_conversations: list of conversations ids to exclude
        """
        self.record_card = record_card
        self.record_responsible_profile = record_card.responsible_profile
        assert isinstance(conversation_types, list)
        self.conversation_types = conversation_types
        self.opened_conversations = self.set_conversations(exclude_conversations)

    def set_conversations(self, exclude_conversations):
        conversations = Conversation.objects.filter(is_opened=True, record_card_id=self.record_card.pk,
                                                    type__in=self.conversation_types)
        if exclude_conversations:
            assert isinstance(exclude_conversations, list)
            conversations = conversations.exclude(pk__in=exclude_conversations)
        return conversations

    @property
    def response_to_responsible(self):
        conversation_ids = self.opened_conversations.values_list("id", flat=True)
        return ConversationUnreadMessagesGroup.objects.filter(group=self.record_responsible_profile,
                                                              conversation__in=conversation_ids).exists()

    @property
    def pend_response_responsible(self):
        pend_response_responsible = False
        for conversation in self.opened_conversations:
            last_message = conversation.message_set.first()
            if last_message and last_message.group == self.record_responsible_profile:
                pend_response_responsible = True
                break
        return pend_response_responsible
