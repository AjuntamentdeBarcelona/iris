from django.urls import reverse_lazy
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import empty
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.serializers import (ModelSerializer, StringRelatedField, SerializerMethodField, EmailField,
                                        ChoiceField)

from django.utils.translation import ugettext_lazy as _

from communications.models import Conversation, ConversationGroup, Message, ConversationUnreadMessagesGroup
from iris_masters.models import ResponseChannel, RecordState, Parameter
from main.api.serializers import ManyToManyExtendedSerializer, GetGroupFromRequestMixin, SerializerCreateExtraMixin

from profiles.models import Group
from profiles.serializers import GroupShortSerializer
from record_cards.models import RecordCard, RecordFile
from record_cards.record_actions.alarms import RecordCardAlarms
from record_cards.record_actions.conversations_alarms import RecordCardConversationAlarms
from record_cards.serializers import RecordCardShortNotificationsSerializer


class ConversationGroupSerializer(ModelSerializer):
    description = StringRelatedField(source="group", read_only=True)

    class Meta:
        model = ConversationGroup
        fields = ("group", "description")


class ConversationSerializer(GetGroupFromRequestMixin, ModelSerializer):
    groups_involved = ManyToManyExtendedSerializer(source="conversationgroup_set", required=False,
                                                   **{"many_to_many_serializer": ConversationGroupSerializer,
                                                      "model": ConversationGroup, "related_field": "conversation",
                                                      "to": "group"})
    unread_messages = SerializerMethodField()
    creation_group = GroupShortSerializer()

    class Meta:
        model = Conversation
        fields = ("id", "user_id", "created_at", "type", "is_opened", "groups_involved", "external_email",
                  "unread_messages", "creation_group", "require_answer")
        read_only_fields = fields

    def get_unread_messages(self, obj):
        group = self.get_group_from_request(self.context.get("request"))
        return obj.unread_messages_by_group(group)


class ConversationCreateSerializer(GetGroupFromRequestMixin, SerializerCreateExtraMixin, ModelSerializer):
    extra_actions = True
    post_create_extra_actions = True

    record_card_id = PrimaryKeyRelatedField(
        source="record_card", queryset=RecordCard.objects.filter(enabled=True),
        error_messages={"does_not_exist": _("The selected RecordCard does not exist")})

    groups_involved = ManyToManyExtendedSerializer(source="conversationgroup_set", required=False,
                                                   **{"many_to_many_serializer": ConversationGroupSerializer,
                                                      "model": ConversationGroup, "related_field": "conversation",
                                                      "to": "group"})

    external_email = EmailField(allow_null=True, allow_blank=True, required=False)

    class Meta:
        model = Conversation
        fields = ("user_id", "record_card_id", "type", "groups_involved", "external_email", "require_answer")
        read_only_fields = ("user_id",)

    def __init__(self, instance=None, data=empty, **kwargs):
        super().__init__(instance, data, **kwargs)
        self.group = self.get_group_from_request(self.context.get("request"))

    def run_validation(self, data=empty):
        validated_data = super().run_validation(data)
        self.check_conversation_type_information(validated_data)
        # Only the RecordCard responsible can create conversations
        if not validated_data["record_card"].group_can_open_conversation(self.group, self.context.get("request").user):
            raise ValidationError(
                {"record_card_id": _("Only a group that can tramit the RecordCard can open new conversations")})

        return validated_data

    def check_conversation_type_information(self, validated_data):
        """
        Check information taking in account conversation type. Raise error if information is missing
        :param validated_data: Validated data from serializer
        :return:
        """
        conversation_type = validated_data.get("type")
        if validated_data.get("type") == Conversation.INTERNAL:
            if not validated_data.get("conversationgroup_set"):
                error_message = _("If conversation type is INTERNAL, the groups involved must be set")
                raise ValidationError({"type": error_message, "groups_involved": error_message})

            involved_groups_ids = [group["group"].pk for group in validated_data["conversationgroup_set"]]
            if self.group.pk in involved_groups_ids:
                raise ValidationError({"groups_involved": _("The group that create the conversation can not be "
                                                            "included in involved groups")})

        elif conversation_type == Conversation.EXTERNAL:
            if not validated_data.get("external_email"):
                error_message = _("If conversation type is EXTERNAL, the external email must be set")
                raise ValidationError({"type": error_message, "external_email": error_message})
        else:
            # else condition is self.type == Conversation.APPLICANT
            record_card_response = getattr(validated_data.get("record_card"), "recordcardresponse", None)
            if not record_card_response or record_card_response.response_channel_id != ResponseChannel.EMAIL:
                error_message = _("Conversation type can not be Applicant because applicant email is unknown")
                raise ValidationError({"type": error_message})

    def do_extra_actions_on_create(self, validated_data):
        """
        Perform extra actions on create
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        validated_data["creation_group"] = self.group

    def do_post_create_extra_actions(self, instance, validated_data):
        """
        Perform extra actions on create after the instance creation
        :param instance: Instance of the created object
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        if "groups_involved" in self.initial_data:
            serializer_kwargs = {
                "many_to_many_serializer": ConversationGroupSerializer, "model": ConversationGroup,
                "related_field": "conversation", "to": "group", "related_instance": instance}
            ser = ManyToManyExtendedSerializer(**serializer_kwargs, source="conversationgroup_set",
                                               data=self.remove_duplicated_groups(self.initial_data["groups_involved"]),
                                               context=self.context)
            ser.bind(field_name="", parent=self)
            if ser.is_valid():
                ser.save()
            validated_data.pop(ser.source, None)

    @staticmethod
    def remove_duplicated_groups(groups_involved):
        conversationgroup_set = []
        for group in groups_involved:
            # Only add groups that has not been add previously
            # in order to not allow group repetition
            if group not in conversationgroup_set:
                conversationgroup_set.append(group)
        return conversationgroup_set


class MessageSerializer(ModelSerializer):
    group = GroupShortSerializer()

    class Meta:
        model = Message
        fields = ("id", "created_at", "user_id", "group", "record_state", "text", "conversation_id")
        read_only_fields = fields


class MessageCreateSerializer(GetGroupFromRequestMixin, SerializerCreateExtraMixin, ModelSerializer):
    extra_actions = True
    post_create_extra_actions = True
    post_data_keys = ["record_files", "record_card", "conversationgroup_set", "type", "external_email"]
    check_involved_users = True

    group_id = PrimaryKeyRelatedField(source="group", queryset=Group.objects.filter(deleted__isnull=True),
                                      error_messages={"does_not_exist": _("The selected group does not exist")},
                                      required=False, allow_null=True)

    conversation_id = PrimaryKeyRelatedField(
        source="conversation", queryset=Conversation.objects.filter(is_opened=True), required=False, allow_null=True,
        error_messages={"does_not_exist": _("The selected conversation does not exist or it's closed")})

    record_state_id = PrimaryKeyRelatedField(
        source="record_state", queryset=RecordState.objects.filter(enabled=True),
        error_messages={"does_not_exist": _("The selected record_state does not exist")})

    record_file_ids = PrimaryKeyRelatedField(
        source="record_files", queryset=RecordFile.objects.all(), many=True, required=False,
        error_messages={"does_not_exist": _("The selected record file does not exist")})

    # Conversation fields
    record_card_id = PrimaryKeyRelatedField(
        source="record_card", queryset=RecordCard.objects.filter(enabled=True), required=False,
        error_messages={"does_not_exist": _("The selected RecordCard does not exist")})

    groups_involved = ManyToManyExtendedSerializer(source="conversationgroup_set", required=False,
                                                   **{"many_to_many_serializer": ConversationGroupSerializer,
                                                      "model": ConversationGroup, "related_field": "conversation",
                                                      "to": "group"})

    type = ChoiceField(choices=[Conversation.INTERNAL, Conversation.EXTERNAL, Conversation.APPLICANT], required=False)

    external_email = EmailField(allow_null=True, allow_blank=True, required=False)
    require_answer = serializers.BooleanField(default=True, required=False)

    class Meta:
        model = Message
        fields = ("id", "created_at", "user_id", "conversation_id", "group_id", "record_state_id", "text",
                  "record_card_id", "groups_involved", "type", "external_email", "require_answer", "record_file_ids")
        read_only_fields = ("id", "created_at", "user_id")

    def __init__(self, instance=None, data=empty, **kwargs):
        super().__init__(instance, data, **kwargs)
        request = self.context.get("request")
        if self.check_involved_users and request:
            self.group = self.get_group_from_request(request)

    def run_validation(self, data=empty):
        validated_data = super().run_validation(data)
        validation_errors = {}
        if not validated_data.get("conversation") and not validated_data.get("conversation_id"):
            # If conversation has not been set, one conversation has to be created
            conversation_serializer = ConversationCreateSerializer(data=self.initial_data, context=self.context)
            conversation_serializer.is_valid(raise_exception=True)
            validated_data["conversation"] = conversation_serializer.save()
        elif validated_data.get("conversation") and not validated_data.get("conversation").is_opened:
            validation_errors["conversation_id"] = _("The conversation is closed and messages can not be added")
        if self.check_involved_users:
            self.check_user_involved_in_conversation(validated_data["conversation"], validation_errors)
        if validated_data.get("conversation").require_answer != validated_data.get("require_answer", True):
            validated_data.get("conversation").require_answer = validated_data.get("require_answer", True)
            validated_data.get("conversation").save()
        validated_data.pop("require_answer", True)

        self.check_record_files(validated_data["conversation"], validated_data.get("record_files", []),
                                validation_errors)
        if validation_errors:
            raise ValidationError(validation_errors, code="invalid")

        return validated_data

    def check_user_involved_in_conversation(self, conversation, validation_errors):
        """
        Check if the user can add a message. A user can create a message if he has created the conversation or
        is one of the groups involverd in INTERNAL conversation type
        :param conversation: Conversation where the message has to be included
        :param validation_errors: dict for validation errors
        :return:
        """
        if self.group.pk != conversation.creation_group.pk:
            error_message = _("The group can not add messages to this {} because it's not involved").format(
                conversation.get_type_display())
            if conversation.type == Conversation.INTERNAL:
                involved_groups_ids = list(conversation.conversationgroup_set.filter(
                    enabled=True).values_list("group_id", flat=True))

                if self.group.pk in involved_groups_ids:
                    # If user group is in the involved groups can add a message
                    return
                if conversation.record_card.responsible_profile.group_plate.startswith(self.group.group_plate):
                    # Allow superior groups to
                    return
            validation_errors["non_field_errors"] = error_message

    @staticmethod
    def check_record_files(conversation, record_files, validation_errors):
        """
        Check record files send to be attached to external email

        :param conversation: Conversation where the message has to be included
        :param record_files: list of files to be attachend to external email
        :param validation_errors: dict for validation errors
        :return:
        """
        allow_add_files = int(Parameter.get_parameter_by_key("FITXERS_PERMETRE_ANEXAR", 1))
        if not allow_add_files and record_files:
            validation_errors["record_file_ids"] = _("The attach of files is deactivated")
            return

        previous_files = []
        if record_files and conversation.type not in Conversation.HASH_TYPES:
            validation_errors["record_file_ids"] = _("Files can only be added in conversations with external people")
            return
        for record_file in record_files:
            if record_file in previous_files:
                validation_errors["record_file_ids"] = _("There are repeated record files to add to the email")
                break
            if record_file.record_card_id != conversation.record_card_id:
                validation_errors["record_file_ids"] = _("The record files selected must be one of record card files")
                break
            previous_files.append(record_file)

    def do_extra_actions_on_create(self, validated_data):
        """
        Perform extra actions on create
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        validated_data["group"] = self.get_serializer_group()

    def get_serializer_group(self):
        return self.group

    def do_post_create_extra_actions(self, instance, validated_data):
        """
        Perform extra actions on create after the instance creation
        :param instance: Instance of the created object
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        instance.conversation.update_unread_messages(instance.group)
        self.set_alarms(instance)

    def set_alarms(self, instance):
        """
        Set alarms depending on who has sent the message and the conversation type
        :param instance: Message created
        :return:
        """
        record_card = instance.conversation.record_card

        if instance.conversation.type == Conversation.APPLICANT:
            conversation_alarms = RecordCardConversationAlarms(record_card, [Conversation.APPLICANT])
            record_card.applicant_response = conversation_alarms.response_to_responsible
            record_card.pend_applicant_response = True
            record_card.alarm = True
        else:
            # instance.conversation.type en Conversation.INTERNAL o Conversation.EXTERNAL
            self.set_internal_external_alarms(record_card)
        record_card.save(update_fields=["alarm", "pend_applicant_response", "applicant_response",
                                        "response_to_responsible", "pend_response_responsible"])

    def set_internal_external_alarms(self, record_card):
        conversation_alarms = RecordCardConversationAlarms(record_card, [Conversation.INTERNAL, Conversation.EXTERNAL])
        record_card.response_to_responsible = conversation_alarms.response_to_responsible
        record_card.pend_response_responsible = conversation_alarms.pend_response_responsible

        if record_card.response_to_responsible or record_card.pend_response_responsible:
            record_card.alarm = True
        else:
            record_card.alarm = RecordCardAlarms(
                record_card, self.group).check_alarms(["responsible_pend_message", "pend_response_responsible"])


class ConversationUnreadMessagesGroupSerializer(ModelSerializer):
    record_card = RecordCardShortNotificationsSerializer(source="conversation.record_card")
    mark_as_read = SerializerMethodField()

    class Meta:
        model = ConversationUnreadMessagesGroup
        fields = ("created_at", "record_card", "unread_messages", "mark_as_read")
        read_only_fields = ("created_at", "record_card", "unread_messages", "mark_as_read")

    def get_mark_as_read(self, obj):
        return reverse_lazy("private_api:communications:conversations_mark_as_read", kwargs={"id": obj.conversation_id})
