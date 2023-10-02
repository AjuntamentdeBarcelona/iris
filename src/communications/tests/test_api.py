import pytest
from django.core import mail
from mock import patch, Mock

from model_mommy import mommy
from rest_framework.status import (HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN,
                                   HTTP_404_NOT_FOUND, HTTP_409_CONFLICT)

from communications.models import Conversation, Message, ConversationUnreadMessagesGroup, ConversationGroup
from iris_masters.models import RecordState, Process
from main.open_api.tests.base import (BaseOpenAPITest, OpenAPIResourceListMixin, OpenAPIResourceCreateMixin,
                                      PostOperationMixin, PreparePathIDMixin)
from profiles.models import Group, UserGroup
from iris_templates.data_checks.visible_parameters import check_template_parameters
from profiles.tests.utils import create_groups
from record_cards.models import RecordCard, RecordFile
from record_cards.permissions import MAYORSHIP, RECARD_NOTIFICATIONS
from record_cards.tests.utils import CreateRecordCardMixin, SetPermissionMixin, SetUserGroupMixin
from iris_masters.tests.utils import load_missing_data_parameters


class TestConversationList(OpenAPIResourceListMixin, CreateRecordCardMixin, PreparePathIDMixin, BaseOpenAPITest):
    path = "/communications/conversations/{id}/"
    base_api_path = "/services/iris/api"

    @pytest.mark.parametrize("object_number", (0, 1, 3))
    def test_list(self, object_number):
        record_card = self.create_record_card()
        [self.given_an_object(record_card) for _ in range(0, object_number)]
        response = self.list(force_params={"page_size": self.paginate_by, "id": record_card.pk})
        self.should_return_list(object_number, self.paginate_by, response)

    def given_an_object(self, record_card):
        return mommy.make(Conversation, user_id="2222", record_card=record_card,
                          creation_group=mommy.make(Group, user_id="2222", profile_ctrl_user_id="ssssssss"))


class TestMessageList(OpenAPIResourceListMixin, CreateRecordCardMixin, PreparePathIDMixin, BaseOpenAPITest):
    path = "/communications/conversations/{id}/messages/"
    base_api_path = "/services/iris/api"

    @pytest.mark.parametrize("object_number", (0, 1, 3))
    def test_list(self, object_number):
        record_card = self.create_record_card(applicant_response=True, response_to_responsible=True)
        conversation = mommy.make(Conversation, user_id="2222", record_card=record_card,
                                  creation_group=mommy.make(Group, user_id="2222", profile_ctrl_user_id="ssssssss"))
        ConversationUnreadMessagesGroup.objects.create(
            conversation=conversation, group=self.user.usergroup.group, unread_messages=object_number)
        [self.given_an_object(conversation) for _ in range(0, object_number)]
        response = self.list(force_params={"page_size": self.paginate_by, "id": conversation.pk})
        self.should_return_list(object_number, self.paginate_by, response)
        assert ConversationUnreadMessagesGroup.all_objects.get(
            conversation=conversation, group=self.user.usergroup.group).unread_messages == object_number
        record_card = RecordCard.objects.get(pk=record_card.pk)
        if object_number:
            assert record_card.applicant_response is False
            assert record_card.response_to_responsible is False
        else:
            assert record_card.applicant_response is True
            assert record_card.response_to_responsible is True

    def given_an_object(self, conversation):
        _, _, soon, _, _, _ = create_groups()
        return mommy.make(Message, user_id="2222", conversation=conversation, group=soon,
                          record_state_id=RecordState.PENDING_VALIDATE)


class TestMessageCreateView(OpenAPIResourceCreateMixin, CreateRecordCardMixin, SetPermissionMixin,
                            BaseOpenAPITest):
    path = "/communications/conversations/messages/add/"
    base_api_path = "/services/iris/api"

    def get_default_data(self):
        return {
            "conversation_id": mommy.make(
                Conversation, user_id="2222", record_card=self.create_record_card(),
                creation_group=self.user.usergroup.group).pk,
            "text": "test message"
        }

    def given_create_rq_data(self):
        return {
            "conversation_id": mommy.make(
                Conversation, user_id="2222", record_card=self.create_record_card(),
                creation_group=self.user.usergroup.group).pk,
            "text": "test message"
        }

    def when_data_is_invalid(self, data):
        data["conversation_id"] = None

    def test_create_valid(self):
        rq_data = self.given_create_rq_data()
        self.when_is_authenticated()
        group = mommy.make(Group, user_id="222", profile_ctrl_user_id="2222")
        internal_conversation_groups = Mock(return_value=[group.id])
        with patch("communications.managers.ConversationManager.internal_conversation_groups",
                   internal_conversation_groups):
            response = self.create(rq_data)
            assert response.status_code == HTTP_201_CREATED
            self.should_create_object(response, rq_data)

    def test_create_conversation_closed(self):
        rq_data = self.given_create_rq_data()
        Conversation.objects.filter(pk=rq_data["conversation_id"]).update(is_opened=False)
        self.when_is_authenticated()
        group = mommy.make(Group, user_id="222", profile_ctrl_user_id="2222")
        internal_conversation_groups = Mock(return_value=[group.id])
        with patch("communications.managers.ConversationManager.internal_conversation_groups",
                   internal_conversation_groups):
            response = self.create(rq_data)
            assert response.status_code == HTTP_400_BAD_REQUEST
            self.should_be_invalid(response, rq_data)

    @pytest.mark.parametrize("group_responsible,create_groups_involved,add_creategroup,expected_response", (
            (True, True, False, HTTP_201_CREATED),
            (True, True, True, HTTP_400_BAD_REQUEST),
            (False, True, False, HTTP_403_FORBIDDEN),
            (True, False, False, HTTP_400_BAD_REQUEST),
    ))
    def test_create_message_new_internal_conversation(self, group_responsible, create_groups_involved, add_creategroup,
                                                      expected_response):

        dair, parent, soon, second_soon, noambit_parent, _ = create_groups()

        UserGroup.objects.create(user=self.user, group=noambit_parent)
        responsible_profile = noambit_parent if group_responsible else parent
        record_card_pk = self.create_record_card(responsible_profile=responsible_profile,
                                                 create_record_card_response=True).pk

        if create_groups_involved:
            groups_involved = [{"group": parent.pk}, {"group": soon.pk}]
            if add_creategroup:
                groups_involved.append({"group": responsible_profile.pk})
        else:
            groups_involved = []

        rq_data = {
            "text": "test message",
            "record_card_id": record_card_pk,
            "groups_involved": groups_involved,
            "type": Conversation.INTERNAL,
        }
        self.when_is_authenticated()
        group = mommy.make(Group, user_id="222", profile_ctrl_user_id="2222")
        internal_conversation_groups = Mock(return_value=[group.id])
        with patch("communications.managers.ConversationManager.internal_conversation_groups",
                   internal_conversation_groups):
            response = self.create(rq_data)
            assert response.status_code == expected_response

    @pytest.mark.parametrize("group_responsible,external_email,expected_response", (
            (True, "test@test.com", HTTP_201_CREATED),
            (False, "test@test.com", HTTP_403_FORBIDDEN),
            (True, "", HTTP_400_BAD_REQUEST),
    ))
    def test_create_message_new_conversation_external(self, group_responsible, external_email, expected_response):

        dair, parent, soon, second_soon, noambit_parent, _ = create_groups()
        check_template_parameters(None)
        UserGroup.objects.create(user=self.user, group=noambit_parent)
        responsible_profile = noambit_parent if group_responsible else parent
        record_card_pk = self.create_record_card(responsible_profile=responsible_profile,
                                                 create_record_card_response=True).pk

        rq_data = {
            "text": "test message",
            "record_card_id": record_card_pk,
            "type": Conversation.EXTERNAL,
            "external_email": external_email
        }
        self.when_is_authenticated()
        group = mommy.make(Group, user_id="222", profile_ctrl_user_id="2222")
        internal_conversation_groups = Mock(return_value=[group.id])
        with patch("communications.managers.ConversationManager.internal_conversation_groups",
                   internal_conversation_groups):
            response = self.create(rq_data)
            assert response.status_code == expected_response
            self.should_create_object(response, rq_data)
            if expected_response == HTTP_201_CREATED:
                assert len(mail.outbox) == 1

    @pytest.mark.parametrize("group_responsible,expected_response", (
            (True, HTTP_201_CREATED),
            (False, HTTP_403_FORBIDDEN),
    ))
    def test_create_message_new_conversation_applicant(self, group_responsible, expected_response):

        dair, parent, soon, second_soon, noambit_parent, _ = create_groups()

        UserGroup.objects.create(user=self.user, group=noambit_parent)
        responsible_profile = noambit_parent if group_responsible else parent
        record_card_pk = self.create_record_card(responsible_profile=responsible_profile,
                                                 create_record_card_response=True).pk

        rq_data = {
            "text": "test message",
            "record_card_id": record_card_pk,
            "type": Conversation.APPLICANT,
        }
        self.when_is_authenticated()
        group = mommy.make(Group, user_id="222", profile_ctrl_user_id="2222")
        internal_conversation_groups = Mock(return_value=[group.id])
        with patch("communications.managers.ConversationManager.internal_conversation_groups",
                   internal_conversation_groups):
            response = self.create(rq_data)
            assert response.status_code == expected_response
            self.should_create_object(response, rq_data)
            if expected_response == HTTP_201_CREATED:
                assert len(mail.outbox) == 1
                record_card = RecordCard.objects.get(pk=record_card_pk)
                assert record_card.pend_applicant_response is True

    @pytest.mark.parametrize("attachments", (0, 1, 3))
    def test_create_message_attachments(self, test_file, attachments):
        load_missing_data_parameters()
        dair, parent, soon, second_soon, noambit_parent, _ = create_groups()

        UserGroup.objects.create(user=self.user, group=parent)
        record_card = self.create_record_card(responsible_profile=parent, create_record_card_response=True)
        conversation = mommy.make(Conversation, type=Conversation.EXTERNAL, creation_group=parent, is_opened=True,
                                  record_card=record_card, require_answer=True, external_email="test@test.com",
                                  user_id="22222")
        record_file_ids = []
        for _ in range(attachments):
            record_file = RecordFile.objects.create(record_card=record_card, file=test_file.name,
                                                    filename=test_file.name)
            record_file_ids.append(record_file.pk)

        rq_data = {
            "text": "test message",
            "conversation_id": conversation.pk,
            "record_file_ids": record_file_ids
        }
        self.when_is_authenticated()
        response = self.create(rq_data)
        assert response.status_code == HTTP_201_CREATED
        self.should_create_object(response, rq_data)
        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        assert len(email.attachments) == attachments

    def test_repeat_groups_on_conversation(self):
        responsible_profile = mommy.make(Group, profile_ctrl_user_id="GRP0001", user_id="2222")
        UserGroup.objects.create(user=self.user, group=responsible_profile)

        record_card_pk = self.create_record_card(create_record_card_response=True,
                                                 responsible_profile=responsible_profile).pk
        _, parent, soon, _, _, _ = create_groups()

        rq_data = {
            "text": "test message",
            "record_card_id": record_card_pk,
            "groups_involved": [{"group": parent.pk}, {"group": soon.pk}, {"group": parent.pk}],
            "type": Conversation.INTERNAL
        }
        self.when_is_authenticated()
        group = mommy.make(Group, user_id="222", profile_ctrl_user_id="2222")
        internal_conversation_groups = Mock(return_value=[group.id])
        with patch("communications.managers.ConversationManager.internal_conversation_groups",
                   internal_conversation_groups):
            response = self.create(rq_data)

            assert response.status_code == HTTP_201_CREATED
            assert Conversation.objects.get(
                pk=response.json()["conversation_id"]).conversationgroup_set.filter(enabled=True).count() == 2

    @pytest.mark.parametrize("initial_res_unread,expected_res_unread,initial_group_unread,expected_group_unread", (
            (0, 0, 0, 1),
            (3, 3, 3, 4),
            (5, 5, 0, 1),
    ))
    def test_update_unread_messages(self, initial_res_unread, expected_res_unread, initial_group_unread,
                                    expected_group_unread):
        record_card = self.create_record_card()
        conversation = mommy.make(Conversation, user_id="2222", record_card=record_card,
                                  creation_group=record_card.responsible_profile)

        ConversationUnreadMessagesGroup.objects.create(
            conversation=conversation, group=record_card.responsible_profile, unread_messages=initial_res_unread)
        group = mommy.make(Group, user_id="222", profile_ctrl_user_id="2222")
        ConversationUnreadMessagesGroup.objects.create(
            conversation=conversation, group=group, unread_messages=initial_group_unread)

        internal_conversation_groups = Mock(return_value=[group.id])
        with patch("communications.managers.ConversationManager.internal_conversation_groups",
                   internal_conversation_groups):
            rq_data = self.given_create_rq_data()
            rq_data["conversation_id"] = conversation.pk
            self.when_is_authenticated()
            response = self.create(rq_data)
            assert response.status_code == HTTP_201_CREATED
            self.should_create_object(response, rq_data)

            assert ConversationUnreadMessagesGroup.objects.get(
                conversation=conversation,
                group=record_card.responsible_profile).unread_messages == expected_res_unread
            assert ConversationUnreadMessagesGroup.objects.get(
                conversation=conversation,
                group=group).unread_messages == expected_group_unread

    @pytest.mark.parametrize("mayorship,mayorship_permission,pending_message,expected_response", (
            (True, True, True, HTTP_201_CREATED),
            (True, False, True, HTTP_201_CREATED),
            (True, True, False, HTTP_201_CREATED),
            (True, False, False, HTTP_403_FORBIDDEN),

            (False, True, True, HTTP_201_CREATED),
            (False, False, True, HTTP_201_CREATED),
            (False, True, False, HTTP_201_CREATED),
            (False, False, False, HTTP_201_CREATED),
    ))
    def test_mayorship_action(self, mayorship, mayorship_permission, pending_message, expected_response):
        _, parent, soon, _, _, _ = create_groups()
        record_kwargs = {
            "record_state_id": RecordState.IN_RESOLUTION,
            "process_pk": Process.EXTERNAL_PROCESSING,
            "mayorship": mayorship
        }
        if mayorship_permission:
            record_kwargs["responsible_profile"] = self.set_permission(MAYORSHIP, group=parent)

        record_card = self.create_record_card(**record_kwargs)
        conversation = Conversation.objects.create(type=Conversation.INTERNAL,
                                                   creation_group=record_card.responsible_profile,
                                                   record_card=record_card, is_opened=True)
        if pending_message:
            ConversationGroup.objects.create(conversation=conversation, group=self.user.usergroup.group)
            mommy.make(Message, user_id="22222", conversation=conversation, group=parent,
                       record_state_id=record_card.record_state_id)

        internal_conversation_groups = Mock(return_value=[self.user.usergroup.group.id])
        with patch("communications.managers.ConversationManager.internal_conversation_groups",
                   internal_conversation_groups):
            response = self.create(force_params={"conversation_id": conversation.pk, "text": "test message"})
            assert response.status_code == expected_response

    @pytest.mark.parametrize("initial_state", (RecordState.CLOSED, RecordState.CANCELLED))
    def test_create_message_close_states(self, initial_state):

        _, parent, _, _, _, _ = create_groups()
        UserGroup.objects.create(user=self.user, group=parent)
        record_card_pk = self.create_record_card(record_state_id=initial_state, responsible_profile=parent,
                                                 create_record_card_response=True).pk

        rq_data = {
            "text": "test message",
            "record_card_id": record_card_pk,
            "type": Conversation.APPLICANT,
        }
        self.when_is_authenticated()
        group = mommy.make(Group, user_id="222", profile_ctrl_user_id="2222")
        internal_conversation_groups = Mock(return_value=[group.id])
        with patch("communications.managers.ConversationManager.internal_conversation_groups",
                   internal_conversation_groups):
            response = self.create(rq_data)
            assert response.status_code == HTTP_409_CONFLICT


class TestConversationMarkAsRead(PostOperationMixin, CreateRecordCardMixin, SetUserGroupMixin, BaseOpenAPITest):
    path = "/communications/conversations/{id}/mark-as-read/"
    base_api_path = "/services/iris/api"

    @pytest.mark.parametrize(
        "set_conversation_pk,change_request_group,expected_response,unread", (
                (True, False, HTTP_200_OK, 10),
                (False, False, HTTP_404_NOT_FOUND, 3),
                (True, True, HTTP_400_BAD_REQUEST, 10),
        ))
    def test_conversation_mark_as_read(self, set_conversation_pk, change_request_group, expected_response, unread):
        dair, parent, soon, _, _, _ = create_groups()
        record_card = self.create_record_card()
        conversation = mommy.make(Conversation, type=Conversation.INTERNAL, record_card=record_card, is_opened=True,
                                  creation_group=record_card.responsible_profile, user_id="2222")
        for gr in [parent, soon]:
            ConversationGroup.objects.create(conversation=conversation, group=gr, user_id="222222")

        if change_request_group:
            UserGroup.objects.filter(user=self.user).delete()
            self.set_usergroup(dair)

        ConversationUnreadMessagesGroup.objects.create(
            conversation=conversation, group=record_card.responsible_profile, unread_messages=unread)
        resp = self.post(force_params={"id": conversation.pk if set_conversation_pk else None})
        assert resp.status_code == expected_response
        if resp.status_code == HTTP_200_OK:
            assert ConversationUnreadMessagesGroup.all_objects.get(
                conversation=conversation, group=record_card.responsible_profile).unread_messages == unread
        else:
            assert ConversationUnreadMessagesGroup.objects.get(
                conversation=conversation, group=record_card.responsible_profile).unread_messages == unread


class NotificationsTestBase(OpenAPIResourceListMixin, CreateRecordCardMixin, BaseOpenAPITest, SetPermissionMixin):
    conversation_type = None
    base_api_path = "/services/iris/api"

    @pytest.mark.parametrize("object_number", (0, 1, 11))
    def test_list(self, object_number):
        record_card = self.create_record_card()
        self.set_permission(RECARD_NOTIFICATIONS, group=record_card.responsible_profile)
        [self.given_an_object(record_card) for _ in range(0, object_number)]
        response = self.list(force_params={"page_size": self.paginate_by})
        self.should_return_list(object_number, self.paginate_by, response)

    def given_an_object(self, record_card):
        conversation = mommy.make(Conversation, user_id="2222", record_card=record_card, type=self.conversation_type,
                                  creation_group=mommy.make(Group, user_id="2222", profile_ctrl_user_id="ssssssss"),
                                  is_opened=True)
        return ConversationUnreadMessagesGroup.objects.create(conversation=conversation, unread_messages=5,
                                                              group=record_card.responsible_profile)


class TestNotificationsInternal(NotificationsTestBase):
    path = "/communications/conversations/notifications/internal/"
    conversation_type = Conversation.INTERNAL


class TestNotificationsExternal(NotificationsTestBase):
    path = "/communications/conversations/notifications/external/"
    conversation_type = Conversation.EXTERNAL


class TestNotificationsApplicant(NotificationsTestBase):
    path = "/communications/conversations/notifications/applicant/"
    conversation_type = Conversation.APPLICANT
