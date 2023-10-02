import pytest
from model_mommy import mommy

from communications.models import Conversation, Message, ConversationGroup
from profiles.tests.utils import create_groups
from record_cards.record_actions.group_response_messages import GroupCanResponseMessages
from record_cards.tests.utils import CreateRecordCardMixin


@pytest.mark.django_db
class TestGroupCanResponseMessages(CreateRecordCardMixin):

    @pytest.mark.parametrize("create_conversation,included_in_conversation,responded_message,can_response_messages", (
            (False, True, False, False),
            (False, True, True, False),
            (True, True, False, True),
            (True, False, False, False),
            (True, False, True, False),
            (True, True, True, False),
    ))
    def test_has_unread_messages(self, create_conversation, included_in_conversation, responded_message,
                                 can_response_messages):
        _, parent, soon, _, _, _ = create_groups()
        record_card = self.create_record_card(responsible_profile=parent)
        if create_conversation:
            conversation = mommy.make(Conversation, user_id='22222', record_card=record_card)
            if included_in_conversation:
                ConversationGroup.objects.create(conversation=conversation, group=soon)
            mommy.make(Message, user_id='22222', conversation=conversation, group=parent,
                       record_state_id=record_card.record_state_id)
            if responded_message:
                mommy.make(Message, user_id='22222',  conversation=conversation, group=soon,
                           record_state_id=record_card.record_state_id)
        assert GroupCanResponseMessages(record_card, soon).can_response_messages() is can_response_messages
