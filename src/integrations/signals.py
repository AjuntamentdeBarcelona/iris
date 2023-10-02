from django.dispatch import receiver


def register_signals():
    from record_cards.models import (record_card_created, record_card_state_changed,
                                     record_card_directly_closed, RecordCard, record_card_resend_answer)
    from integrations.hooks import (record_card_was_created, record_card_state_was_changed,
                                    send_twitter)

    @receiver(record_card_created, sender=RecordCard, weak=False)
    def created_record_card(sender, **kwargs):
        record_card_was_created(kwargs['record_card'])

    @receiver(record_card_state_changed, sender=RecordCard, weak=False)
    def updated_record_card(sender, **kwargs):
        record_card_state_was_changed(kwargs['record_card'])

    @receiver(record_card_resend_answer, sender=RecordCard, weak=False)
    def resend_answer(sender, **kwargs):
        record_card_state_was_changed(kwargs['record_card'])

    @receiver(record_card_directly_closed, sender=RecordCard, weak=False)
    def closed_directly_record_card(sender, **kwargs):
        send_twitter(kwargs['record_card'])
