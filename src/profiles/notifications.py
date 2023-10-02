from django.conf import settings
from django.utils import timezone

from emails.emails import (NextExpireRecordsEmail, PendingValidateRecordsEmail, RecordAllocationEmail,
                           RecordsPendCommunications)
from iris_masters.models import RecordState


class GroupNotifications:
    """
    Check and send group notifications
    """
    group = None

    def __init__(self, group) -> None:
        super().__init__()
        self.group = group

    def next_to_expire_notification(self):
        """
        Check if next to expire notification has to be sent.
        If the notification is not set up or there are no emails to notify, it does nothing.
        Else check the last time that the notification was sent and if there are next to expire records.
        If both conditions are true, send the notification email and update the notification date

        :return:
        """
        if not self.group.records_next_expire or not self.group.notifications_emails:
            return

        notif_date = self.group.records_next_expire_notif_date
        today = timezone.now().date()
        if not notif_date or (today - notif_date).days >= self.group.records_next_expire_freq:
            next_to_expire_records = self.group.recordcard_set.near_to_expire_records()
            if next_to_expire_records:
                NextExpireRecordsEmail(self.group, next_to_expire_records).send(
                    from_email=settings.DEFAULT_FROM_EMAIL, to=self.group.notifications_emails.split(","))
                self.group.records_next_expire_notif_date = today
                self.group.save()

    def pending_validate_notification(self):
        """
        Check if pending validate records notification has to be sent.
        If the notification is not set up or there are no emails to notify, it does nothing.
        Else check the last time that the notification was sent and if there are pending records.
        If both conditions are true, send the notification email and update the notification date

        :return:
        """
        if not self.group.pend_records or not self.group.notifications_emails:
            return

        notif_date = self.group.pend_records_notif_date
        today = timezone.now().date()
        if not notif_date or (today - notif_date).days >= self.group.pend_records_freq:
            pend_states = [RecordState.PENDING_VALIDATE, RecordState.IN_PLANING, RecordState.IN_RESOLUTION,
                           RecordState.PENDING_ANSWER, RecordState.EXTERNAL_RETURNED]
            pend_records = self.group.recordcard_set.filter(enabled=True, record_state_id__in=pend_states)
            if pend_records:
                PendingValidateRecordsEmail(self.group, pend_records).send(
                    from_email=settings.DEFAULT_FROM_EMAIL, to=self.group.notifications_emails.split(","))
                self.group.pend_records_notif_date = today
                self.group.save()

    def records_allocation_notification(self, record_card):
        """
        Check if allocation notification has to be sent.
        If records allotcation is not set up or there are no emails to notify or the responsible profile of the record
        card is not the group, it does nothing.
        Otherwise, it sends an email warning about the record assignation

        :param record_card: Record card that has been assigned to the group
        :return:
        """
        if not self.group.records_allocation or not self.group.notifications_emails or \
                self.group != record_card.responsible_profile:
            return

        RecordAllocationEmail(self.group, record_card).send(
            from_email=settings.DEFAULT_FROM_EMAIL, to=self.group.notifications_emails.split(","))

    def records_pending_communications(self):
        """
        Check if records with pending communications notification has to be sent.
        If the notification is not set up or there are no emails to notify, it does nothing.
        Else check the last time that the notification was sent and if there are pending communications.
        If both conditions are true, send the notification email and update the notification date

        :return:
        """
        if not self.group.pend_communication or not self.group.notifications_emails:
            return

        notif_date = self.group.pend_communication_notif_date
        today = timezone.now().date()
        if not notif_date or (today - notif_date).days >= self.group.pend_communication_freq:

            pend_communications = self.group.conversationunreadmessagesgroup_set.filter(
                conversation__record_card__element_detail__pend_commmunications=True)

            record_cards = []
            for pend_communication in pend_communications:
                if pend_communication.conversation.record_card not in record_cards:
                    record_cards.append(pend_communication.conversation.record_card)

            if record_cards:
                RecordsPendCommunications(self.group, record_cards).send(
                    from_email=settings.DEFAULT_FROM_EMAIL, to=self.group.notifications_emails.split(","))
                self.group.pend_communication_notif_date = today
                self.group.save()
