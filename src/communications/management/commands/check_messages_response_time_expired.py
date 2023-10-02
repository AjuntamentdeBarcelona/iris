from django.core.management.base import BaseCommand

from communications.models import Message, Conversation


class Command(BaseCommand):
    """
    Command to clean ApplicationElementDetail values tu allow uniquetogether constraint
    """

    help = "Check Messages response time expired"

    def handle(self, *args, **options):
        self.stdout.write('Start checking if response time of messages has expired')

        messages_no_answered = Message.objects.filter(is_answered=False, conversation__type=Conversation.APPLICANT,
                                                      conversation__record_card__response_time_expired=False,
                                                      ).select_related('conversation', 'conversation__record_card')

        for message in messages_no_answered:
            if message.response_time_expired:
                self.stdout.write('Response time of message {} has expired'.format(message.__str__()))
                record_card = message.conversation.record_card
                record_card.response_time_expired = True
                record_card.alarm = True
                record_card.save(update_fields=["response_time_expired", "alarm"])
                self.stdout.write('Record Card {} set response time expired alarm'.format(
                    record_card.normalized_record_id))
