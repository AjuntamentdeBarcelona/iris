from django.db.models import QuerySet


class ConversationManager(QuerySet):

    def internal_conversation_groups(self, conversation, groups_messages_ids, message_group):
        """
        Get internal conversation groups
        :param conversation: conversation to get groups ids
        :param groups_messages_ids: groups ids from
        :param message_group:
        :return:
        """
        return groups_messages_ids.union(conversation.conversationgroup_set.filter(
                enabled=True).exclude(group=message_group).values_list("group_id", flat=True))

    def close_conversations(self, record_card_id=None):
        """
        Close conversations related to a RecordCard
        :param record_card_id: RecordCard id, if the initial qs
        :return: Closed conversations
        """
        qs = self.filter(is_opened=True)
        if record_card_id:
            qs.filter(record_card_id=record_card_id,)
        return qs.update(is_opened=False)
