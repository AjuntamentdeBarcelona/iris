import pytest
from mock import Mock, patch

from model_mommy import mommy

from communications.models import Conversation, Message, ConversationGroup, ConversationUnreadMessagesGroup
from communications.serializers import (ConversationSerializer, ConversationCreateSerializer, MessageSerializer,
                                        MessageCreateSerializer, ConversationUnreadMessagesGroupSerializer)
from iris_masters.models import RecordState, Parameter
from iris_masters.permissions import ADMIN
from main.test.mixins import FieldsTestSerializerMixin
from profiles.models import Group
from profiles.tests.utils import create_groups
from record_cards.models import RecordFile, RecordCard
from record_cards.tests.utils import CreateRecordCardMixin, SetGroupRequestMixin, SetPermissionMixin
from communications.tests.utils import load_missing_data


@pytest.mark.django_db
class TestConversationSerializer(CreateRecordCardMixin, FieldsTestSerializerMixin):
    serializer_class = ConversationSerializer
    data_keys = ["id", "user_id", "created_at", "type", "is_opened", "groups_involved", "external_email",
                 "unread_messages", "creation_group", "require_answer"]

    def test_serializer(self):
        load_missing_data()
        super().test_serializer()

    def get_instance(self):
        return mommy.make(Conversation, user_id="2222", record_card=self.create_record_card(),
                          creation_group=mommy.make(Group, user_id="2222", profile_ctrl_user_id="ssssssss"))


@pytest.mark.django_db
class TestConversationCreationSerializer(CreateRecordCardMixin, SetPermissionMixin, SetGroupRequestMixin):

    @pytest.mark.parametrize(
        "group_responsible,create_groups_involved,add_creategroup,valid", (
                (True, True, False, True),
                (True, True, True, False),
                (False, True, False, False),
                (True, False, False, False),
        ))
    def test_internal_conversation(self, group_responsible, create_groups_involved, add_creategroup, valid):
        load_missing_data()
        group, request = self.set_group_request()
        group.group_plate = 'XXXX'
        group.save()
        responsible_profile = group if group_responsible else None
        record_card_pk = self.create_record_card(responsible_profile=responsible_profile).pk
        if create_groups_involved:
            _, parent, soon, _, _, _ = create_groups()
            groups_involved = [{"group": parent.pk}, {"group": soon.pk}]
            if add_creategroup:
                groups_involved.append({"group": group.pk})
        else:
            groups_involved = []

        data = {
            "record_card_id": record_card_pk,
            "type": Conversation.INTERNAL,
            "groups_involved": groups_involved,
        }
        ser = ConversationCreateSerializer(data=data, context={"request": request})
        assert ser.is_valid() is valid
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize("group_responsible,external_email,create_record_card_response,valid", (
            (True, "test@test.com", False, True),
            (False, "test@test.com", False, False),
            (True, "", False, False),
    ))
    def test_external_conversation(self, group_responsible, external_email, create_record_card_response, valid):
        load_missing_data()
        group, request = self.set_group_request()
        group.group_plate = 'XXXX'
        group.save()
        responsible_profile = group if group_responsible else None
        record_card_pk = self.create_record_card(create_record_card_response=create_record_card_response,
                                                 responsible_profile=responsible_profile).pk

        data = {
            "record_card_id": record_card_pk,
            "type": Conversation.EXTERNAL,
            "external_email": external_email
        }
        ser = ConversationCreateSerializer(data=data, context={"request": request})
        assert ser.is_valid() is valid
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize("group_responsible,create_record_card_response,valid", (
            (True, True, True),
            (True, False, False),
    ))
    def test_applicant_conversation_serializer(self, group_responsible, create_record_card_response, valid):
        load_missing_data()
        group, request = self.set_group_request()
        group.group_plate = 'XXXX'
        group.save()
        responsible_profile = group if group_responsible else None
        record_card_pk = self.create_record_card(create_record_card_response=create_record_card_response,
                                                 responsible_profile=responsible_profile).pk
        data = {
            "record_card_id": record_card_pk,
            "type": Conversation.APPLICANT,
        }
        ser = ConversationCreateSerializer(data=data, context={"request": request})
        assert ser.is_valid() is valid
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize("is_admin,valid", ((True, True), (False, True)))
    def test_group_no_responsible(self, is_admin, valid):
        load_missing_data()
        dair, parent, _, _, _, _ = create_groups()
        if is_admin:
            self.set_permission(ADMIN, dair)

        _, request = self.set_group_request(group=dair)

        record_card_pk = self.create_record_card(create_record_card_response=True, responsible_profile=parent).pk
        data = {
            "record_card_id": record_card_pk,
            "type": Conversation.APPLICANT,
        }
        ser = ConversationCreateSerializer(data=data, context={"request": request})
        assert ser.is_valid() is valid
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestMessageSerializer(CreateRecordCardMixin, FieldsTestSerializerMixin):
    serializer_class = MessageSerializer
    data_keys = ["id", "created_at", "user_id", "group", "record_state", "text", "conversation_id"]

    def test_serializer(self):
        load_missing_data()
        super().test_serializer()

    def get_instance(self):
        conversation = mommy.make(Conversation, user_id="2222", record_card=self.create_record_card(),
                                  creation_group=mommy.make(Group, user_id="2222", profile_ctrl_user_id="ssssssss"))
        _, _, soon, _, _, _ = create_groups()
        return mommy.make(Message, user_id="2222", conversation=conversation, group=soon,
                          record_state_id=RecordState.PENDING_VALIDATE)


@pytest.mark.django_db
class TestMessageCreateSerializer(CreateRecordCardMixin, SetGroupRequestMixin):

    @pytest.mark.parametrize("create_conversation,conversation_opened,record_state_id,other_creator,message,valid", (
            (True, True, RecordState.PENDING_VALIDATE, False, "Text message", True),
            (True, True, None, False, "Text message", False),
            (True, True, RecordState.PENDING_VALIDATE, True, "Text message", False),
            (True, False, RecordState.PENDING_VALIDATE, False, "Text message", False),
            (False, True, RecordState.PENDING_VALIDATE, False, "Text message", False),
            (True, True, RecordState.PENDING_VALIDATE, False, "", False),
    ))
    def test_validate_serializer(self, create_conversation, conversation_opened, record_state_id, other_creator,
                                 message, valid):
        load_missing_data()
        creation_group, request = self.set_group_request()
        creation_group.group_plate = 'YYY'
        creation_group.save()
        record_file_ids = [1, 2]
        record_card = self.create_record_card()
        for file_id in record_file_ids:
            if not RecordFile.objects.filter(id=file_id):
                record_file = RecordFile(id=file_id, record_card=record_card)
                record_file.save()

        if record_state_id is not None:
            if not RecordState.objects.filter(id=record_state_id):
                record_state = RecordState(id=record_state_id)
                record_state.save()

        if other_creator:
            # Different group tree from YYY
            creation_group = mommy.make(Group, group_plate='xxxxx', user_id="2222", profile_ctrl_user_id="2222")
        if create_conversation:
            conversation_pk = mommy.make(
                Conversation, is_opened=conversation_opened, user_id="2222", record_card=record_card,
                creation_group=creation_group, type=1).pk
        else:
            conversation_pk = None
        data = {
            "conversation_id": conversation_pk,
            "record_state_id": record_state_id,
            "text": message,
            "record_file_ids": record_file_ids
        }

        ser = MessageCreateSerializer(data=data, context={"request": request})
        assert ser.is_valid() is valid
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize("conversation_type,other_creator,author_involved,valid", (
            (Conversation.INTERNAL, False, False, True),
            (Conversation.INTERNAL, True, False, False),
            (Conversation.INTERNAL, True, True, True),
            (Conversation.EXTERNAL, False, False, True),
            (Conversation.EXTERNAL, True, False, False),
            (Conversation.APPLICANT, False, False, True),
            (Conversation.APPLICANT, True, False, False),
    ))
    def test_validate_message_creator(self, conversation_type, other_creator, author_involved, valid):
        load_missing_data()
        message_creator, request = self.set_group_request()
        message_creator.group_plate = 'YYY'
        message_creator.save()
        record_state_id = RecordState.PENDING_VALIDATE
        if other_creator:
            # Different group tree from YYY
            conversation_creator = mommy.make(Group, group_plate='XXX', user_id="2222", profile_ctrl_user_id="2222")
        else:
            conversation_creator = message_creator

        conversation_pk = mommy.make(
            Conversation, is_opened=True, user_id="2222", record_card=self.create_record_card(), type=conversation_type,
            creation_group=conversation_creator).pk

        if conversation_type == Conversation.INTERNAL and author_involved:
            ConversationGroup.objects.create(conversation_id=conversation_pk, group=message_creator)

        if record_state_id is not None:
            if not RecordState.objects.filter(id=record_state_id):
                record_state = RecordState(id=record_state_id)
                record_state.save()

        data = {
            "conversation_id": conversation_pk,
            "record_state_id": record_state_id,
            "text": "Text message"
        }

        ser = MessageCreateSerializer(data=data, context={"request": request})
        ser.is_valid()
        assert ser.is_valid() is valid
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize(
        "conversation_type,group_responsible,create_groups_involved,external_email,create_record_card_response,valid", (
                (Conversation.INTERNAL, True, True, "", False, True),
                (Conversation.INTERNAL, False, True, "", False, False),
                (Conversation.INTERNAL, True, False, "", False, False),
                (Conversation.EXTERNAL, True, False, "test@test.com", False, True),
                (Conversation.EXTERNAL, True, False, "", False, False),
                (Conversation.APPLICANT, True, False, "", True, True),
                (Conversation.APPLICANT, True, False, "", False, False),
        ))
    def test_create_message_new_conversation_serializer(
            self, conversation_type, group_responsible, create_groups_involved, external_email,
            create_record_card_response, valid):
        load_missing_data()
        record_state_id = RecordState.PENDING_VALIDATE

        if create_groups_involved:
            _, parent, soon, _, _, _ = create_groups()
            groups_involved = [{"group": parent.pk}, {"group": soon.pk}]
        else:
            groups_involved = []

        group, request = self.set_group_request()
        group.group_plate = 'XXX'
        group.save()
        responsible_profile = group if group_responsible else None
        record_card_pk = self.create_record_card(create_record_card_response=create_record_card_response,
                                                 responsible_profile=responsible_profile).pk

        if record_state_id is not None:
            if not RecordState.objects.filter(id=record_state_id):
                record_state = RecordState(id=record_state_id)
                record_state.save()

        data = {
            "record_state_id": record_state_id,
            "text": "test message",
            "record_card_id": record_card_pk,
            "groups_involved": groups_involved,
            "type": conversation_type,
            "external_email": external_email
        }

        ser = MessageCreateSerializer(data=data, context={"request": request})
        assert ser.is_valid() is valid
        assert isinstance(ser.errors, dict)

    def test_record_files_ids_internal(self, test_file):
        load_missing_data()
        record_state_id = RecordState.IN_PLANING
        if record_state_id is not None:
            if not RecordState.objects.filter(id=record_state_id):
                record_state = RecordState(id=record_state_id)
                record_state.save()
        creation_group, request = self.set_group_request()
        record_card = self.create_record_card(record_state_id=record_state_id)
        record_file = RecordFile.objects.create(record_card=record_card, file=test_file.name, filename=test_file.name)

        conversation_pk = mommy.make(Conversation, is_opened=True, user_id="2222", record_card=record_card,
                                     creation_group=creation_group).pk
        data = {
            "conversation_id": conversation_pk,
            "record_state_id": record_state_id,
            "text": "test message",
            "record_file_ids": [record_file.pk]
        }

        ser = MessageCreateSerializer(data=data, context={"request": request})
        assert ser.is_valid() is False
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize("conv_type,repeat_file,valid", (
            (Conversation.EXTERNAL, False, True),
            (Conversation.EXTERNAL, True, False),
            (Conversation.APPLICANT, False, True),
            (Conversation.APPLICANT, True, False),
    ))
    def test_record_files_ids_external(self, test_file, conv_type, repeat_file, valid):
        load_missing_data()
        record_state_id = RecordState.IN_PLANING
        if record_state_id is not None:
            if not RecordState.objects.filter(id=record_state_id):
                record_state = RecordState(id=record_state_id)
                record_state.save()
        creation_group, request = self.set_group_request()
        record_card = self.create_record_card(record_state_id=record_state_id)
        record_file = RecordFile.objects.create(record_card=record_card, file=test_file.name, filename=test_file.name)

        conversation_pk = mommy.make(Conversation, is_opened=True, user_id="2222", record_card=record_card,
                                     creation_group=creation_group, type=conv_type).pk

        record_file_ids = [record_file.pk]
        if repeat_file:
            record_file_ids.append(record_file.pk)

        data = {
            "conversation_id": conversation_pk,
            "record_state_id": record_state_id,
            "text": "test message",
            "record_file_ids": record_file_ids
        }

        ser = MessageCreateSerializer(data=data, context={"request": request})
        assert ser.is_valid() is valid
        assert isinstance(ser.errors, dict)

    def test_record_files_attach_disabled(self, test_file):
        load_missing_data()
        record_state_id = RecordState.IN_PLANING
        if record_state_id is not None:
            if not RecordState.objects.filter(id=record_state_id):
                record_state = RecordState(id=record_state_id)
                record_state.save()
        if not Parameter.objects.filter(parameter="FITXERS_PERMETRE_ANEXAR"):
            param = Parameter(parameter="FITXERS_PERMETRE_ANEXAR")
        else:
            param = Parameter.objects.get(parameter="FITXERS_PERMETRE_ANEXAR")
        param.valor = "0"
        param.save()
        creation_group, request = self.set_group_request()
        record_card = self.create_record_card(record_state_id=record_state_id)
        record_file = RecordFile.objects.create(record_card=record_card, file=test_file.name, filename=test_file.name)

        conversation_pk = mommy.make(Conversation, is_opened=True, user_id="2222", record_card=record_card,
                                     creation_group=creation_group, type=Conversation.APPLICANT).pk

        data = {
            "conversation_id": conversation_pk,
            "record_state_id": record_state_id,
            "text": "test message",
            "record_file_ids": [record_file.pk]
        }
        ser = MessageCreateSerializer(data=data, context={"request": request})
        assert ser.is_valid() is False
        assert isinstance(ser.errors, dict)

    def test_record_files_ids_from_another_record(self, test_file):
        load_missing_data()
        record_state_id = RecordState.IN_PLANING
        if record_state_id is not None:
            if not RecordState.objects.filter(id=record_state_id):
                record_state = RecordState(id=record_state_id)
                record_state.save()
        creation_group, request = self.set_group_request()
        record_card = self.create_record_card(record_state_id=record_state_id)
        RecordFile.objects.create(record_card=record_card, file=test_file.name, filename=test_file.name)
        conversation_pk = mommy.make(Conversation, is_opened=True, user_id="2222", record_card=record_card,
                                     creation_group=creation_group, type=Conversation.EXTERNAL).pk

        record_card = self.create_record_card(record_state_id=RecordState.IN_PLANING)
        record_file = RecordFile.objects.create(record_card=record_card, file=test_file.name, filename=test_file.name)

        data = {
            "conversation_id": conversation_pk,
            "record_state_id": record_state_id,
            "text": "test message",
            "record_file_ids": [record_file.pk]
        }

        ser = MessageCreateSerializer(data=data, context={"request": request})
        assert ser.is_valid() is False
        assert isinstance(ser.errors, dict)
        assert "record_file_ids" in ser.errors

    def test_applicant_message_alarm(self):
        load_missing_data()
        record_state_id = RecordState.PENDING_VALIDATE
        if record_state_id is not None:
            if not RecordState.objects.filter(id=record_state_id):
                record_state = RecordState(id=record_state_id)
                record_state.save()
        message_creator, request = self.set_group_request()
        record_card = self.create_record_card(responsible_profile=message_creator)
        conversation_pk = mommy.make(
            Conversation, is_opened=True, user_id="2222", record_card=record_card, type=Conversation.APPLICANT,
            creation_group=record_card.responsible_profile).pk

        data = {
            "conversation_id": conversation_pk,
            "record_state_id": record_state_id,
            "text": "Text message"
        }

        ser = MessageCreateSerializer(data=data, context={"request": request})
        assert ser.is_valid() is True
        assert isinstance(ser.errors, dict)
        ser.save()
        record_card = RecordCard.objects.get(pk=record_card.pk)
        assert record_card.applicant_response is False
        assert record_card.pend_applicant_response is True
        assert record_card.alarm is True

    @pytest.mark.parametrize("conversation_type,conversation_creator", (
            (Conversation.INTERNAL, True),
            (Conversation.INTERNAL, False),
            (Conversation.EXTERNAL, True),
    ))
    def test_internal_external_alarm(self, conversation_type, conversation_creator):
        dair, parent, soon, _, _, _ = create_groups()
        load_missing_data()
        record_state_id = RecordState.PENDING_VALIDATE
        if record_state_id is not None:
            if not RecordState.objects.filter(id=record_state_id):
                record_state = RecordState(id=record_state_id)
                record_state.save()
        record_card = self.create_record_card(responsible_profile=parent)
        conversation_pk = mommy.make(
            Conversation, is_opened=True, user_id="2222", record_card=record_card, type=conversation_type,
            creation_group=parent).pk
        ConversationGroup.objects.create(conversation_id=conversation_pk, group=dair)
        ConversationGroup.objects.create(conversation_id=conversation_pk, group=soon)

        data = {
            "conversation_id": conversation_pk,
            "record_state_id": record_state_id,
            "text": "Text message"
        }

        if conversation_creator:
            message_creator, request = self.set_group_request(parent)
        else:
            message_creator, request = self.set_group_request(dair)
            ConversationUnreadMessagesGroup.objects.create(group=record_card.responsible_profile,
                                                           conversation_id=conversation_pk, unread_messages=3)

        internal_conversation_groups = Mock(return_value=[soon.id])
        with patch("communications.managers.ConversationManager.internal_conversation_groups",
                   internal_conversation_groups):

            ser = MessageCreateSerializer(data=data, context={"request": request})
            assert ser.is_valid() is True
            assert isinstance(ser.errors, dict)
            ser.save()
            record_card = RecordCard.objects.get(pk=record_card.pk)

            if conversation_creator:
                assert record_card.response_to_responsible is False
                assert record_card.pend_response_responsible is True
            else:
                assert record_card.response_to_responsible is True
                assert record_card.pend_response_responsible is False
            assert record_card.alarm is True


@pytest.mark.django_db
class TestConversationUnreadMessagesGroupSerializer(CreateRecordCardMixin, FieldsTestSerializerMixin):
    serializer_class = ConversationUnreadMessagesGroupSerializer
    data_keys = ["created_at", "record_card", "unread_messages", "mark_as_read"]

    def get_instance(self):
        load_missing_data()
        record_card = self.create_record_card()
        conversation = mommy.make(Conversation, user_id="2222", record_card=record_card,
                                  creation_group=mommy.make(Group, user_id="2222", profile_ctrl_user_id="ssssssss"))
        return ConversationUnreadMessagesGroup.objects.create(conversation=conversation, unread_messages=5,
                                                              group=record_card.responsible_profile)
