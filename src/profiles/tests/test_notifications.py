from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone
from model_mommy import mommy

from communications.models import Conversation, ConversationUnreadMessagesGroup
from profiles.models import Group
from profiles.notifications import GroupNotifications
from profiles.tests.utils import create_notification_group
from record_cards.tests.utils import CreateRecordCardMixin
from communications.tests.utils import load_missing_data

@pytest.mark.django_db
class TestGroupNotifications(CreateRecordCardMixin):

    @pytest.mark.parametrize(
        "create_record,notifications_emails,records_next_expire,records_next_expire_freq,orig_notif_date,"
        "expected_outbox,expected_to,expected_notif_date", (
                (True, "test@test.com,test2@test.com", True, 1, None, 1, 2, timezone.now().date()),
                (True, "test@test.com", True, 1, None, 1, 1, timezone.now().date()),
                (True, "", True, 1, None, 0, 0, None),
                (True, "test@test.com,test2@test.com", False, 1, None, 0, 0, None),
                (True, "test@test.com,test2@test.com", True, 3, None, 1, 2, timezone.now().date()),
                (True, "test@test.com,test2@test.com", True, 1, timezone.now().date(), 0, 0, timezone.now().date()),
                (True, "test@test.com,test2@test.com", True, 1, timezone.now().date() - timedelta(days=1), 1, 2,
                 timezone.now().date()),
                (True, "test@test.com,test2@test.com", True, 5, timezone.now().date() - timedelta(days=1), 0, 0,
                 timezone.now().date() - timedelta(days=1)),
                (False, "test@test.com,test2@test.com", True, 1, None, 0, 0, None),
        ))
    def test_next_to_expire_notification(self, create_record, notifications_emails, records_next_expire,
                                         records_next_expire_freq, orig_notif_date, expected_outbox, expected_to,
                                         expected_notif_date):
        load_missing_data()
        group = create_notification_group(notifications_emails=notifications_emails,
                                          records_next_expire=records_next_expire,
                                          records_next_expire_freq=records_next_expire_freq,
                                          records_next_expire_notif_date=orig_notif_date)
        if create_record:
            self.create_record_card(responsible_profile=group, ans_limit_date=timezone.now().date() + timedelta(days=1),
                                    ans_limit_nearexpire=timezone.now().date() - timedelta(days=1))
        GroupNotifications(group).next_to_expire_notification()
        assert len(mail.outbox) == expected_outbox
        if mail.outbox:
            assert len(mail.outbox[0].to) == expected_to
        group = Group.objects.get(pk=group.pk)
        assert group.records_next_expire_notif_date == expected_notif_date

    @pytest.mark.parametrize(
        "create_record,notifications_emails,pend_records,pend_records_freq,orig_notif_date,expected_outbox,expected_to,"
        "expected_notif_date", (
                (True, "test@test.com,test2@test.com", True, 1, None, 1, 2, timezone.now().date()),
                (True, "test@test.com", True, 1, None, 1, 1, timezone.now().date()),
                (True, "", True, 1, None, 0, 0, None),
                (True, "test@test.com,test2@test.com", False, 1, None, 0, 0, None),
                (True, "test@test.com,test2@test.com", True, 3, None, 1, 2, timezone.now().date()),
                (True, "test@test.com,test2@test.com", True, 1, timezone.now().date(), 0, 0, timezone.now().date()),
                (True, "test@test.com,test2@test.com", True, 1, timezone.now().date() - timedelta(days=1), 1, 2,
                 timezone.now().date()),
                (True, "test@test.com,test2@test.com", True, 5, timezone.now().date() - timedelta(days=1), 0, 0,
                 timezone.now().date() - timedelta(days=1)),
                (False, "test@test.com,test2@test.com", True, 1, None, 0, 0, None),
        ))
    def test_pending_validate_notification(self, create_record, notifications_emails, pend_records, pend_records_freq,
                                           orig_notif_date, expected_outbox, expected_to, expected_notif_date):
        load_missing_data()
        group = create_notification_group(notifications_emails=notifications_emails, pend_records=pend_records,
                                          pend_records_freq=pend_records_freq, pend_records_notif_date=orig_notif_date)
        if create_record:
            self.create_record_card(responsible_profile=group)
        GroupNotifications(group).pending_validate_notification()
        assert len(mail.outbox) == expected_outbox
        if mail.outbox:
            assert len(mail.outbox[0].to) == expected_to
        group = Group.objects.get(pk=group.pk)
        assert group.pend_records_notif_date == expected_notif_date

    @pytest.mark.parametrize("set_responsible,notifications_emails,records_allocation,expected_outbox,expected_to", (
            (True, "test@test.com,test2@test.com", True, 1, 2),
            (True, "test@test.com", True, 1, 1),
            (True, "", True, 0, 0),
            (True, "test@test.com,test2@test.com", False, 0, 0),
            (False, "test@test.com,test2@test.com", True, 0, 0),
    ))
    def test_records_allocation_notification(self, set_responsible, notifications_emails, records_allocation,
                                             expected_outbox, expected_to):
        load_missing_data()
        group = create_notification_group(notifications_emails=notifications_emails,
                                          records_allocation=records_allocation)
        kwargs = {}
        if set_responsible:
            kwargs["responsible_profile"] = group
        record_card = self.create_record_card(**kwargs)
        GroupNotifications(group).records_allocation_notification(record_card)
        assert len(mail.outbox) == expected_outbox
        if mail.outbox:
            assert len(mail.outbox[0].to) == expected_to

    @pytest.mark.parametrize(
        "create_record,notifications_emails,pend_communication,pend_communication_freq,expected_outbox", (
                (True, "test@test.com,test3@email.com", True, 3, 1),
                (False, "test@test.com,test3@email.com", True, 3, 0),
                (True, "test@test.com,test3@email.com", False, 3, 0),
        ))
    def test_records_pending_communications(self, create_record, notifications_emails, pend_communication,
                                            pend_communication_freq, expected_outbox):
        load_missing_data()
        group = create_notification_group(notifications_emails=notifications_emails,
                                          pend_communication=pend_communication,
                                          pend_communication_freq=pend_communication_freq)
        if create_record:
            record_card = self.create_record_card(responsible_profile=group)
            conv = mommy.make(Conversation, user_id="11111", type=Conversation.EXTERNAL, external_email="test@test.com",
                              record_card=record_card, creation_group=group)
            mommy.make(ConversationUnreadMessagesGroup, conversation=conv, unread_messages=7, group=group)
        GroupNotifications(group).records_pending_communications()
        assert len(mail.outbox) == expected_outbox
        if create_record and pend_communication:
            group = Group.objects.get(pk=group.pk)
            assert group.pend_communication_notif_date == timezone.now().date()
