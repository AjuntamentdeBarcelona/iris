from communications.models import Message


class GroupCanResponseMessages:
    """
    Class to check if a group can respond messages on a conversation
    """

    def __init__(self, record_card, group) -> None:
        self.record_card = record_card
        self.group = group
        super().__init__()

    def can_response_messages(self):
        record_open_conversations = self.record_card.conversation_set.filter(is_opened=True)

        for conversation in record_open_conversations:
            group_involved = self.group in conversation.groups_involved.all()
            # Messages are ordered by -created_at. Then, the last chronological message is the first one
            last_message = Message.objects.filter(conversation=conversation).first()
            if group_involved and last_message and last_message.group != self.group:
                return True
        return False
