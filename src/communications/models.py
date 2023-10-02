from datetime import timedelta

from django.conf import settings
from django.core.signing import Signer
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from communications.managers import ConversationManager
from custom_safedelete.models import CustomSafeDeleteModel
from iris_masters.models import UserTrack, RecordState, Parameter
from profiles.models import Group
from record_cards.models import RecordCard


class Conversation(UserTrack):

    objects = ConversationManager.as_manager()

    INTERNAL = 0
    EXTERNAL = 1
    APPLICANT = 2

    TYPES = (
        (INTERNAL, _("Internal conversation")),
        (EXTERNAL, _("External conversation")),
        (APPLICANT, _("Applicant conversation"))
    )

    HASH_TYPES = [EXTERNAL, APPLICANT]

    type = models.IntegerField(_("Conversation Type"), choices=TYPES, default=INTERNAL)
    creation_group = models.ForeignKey(Group, verbose_name=_("Creation Group"), null=True, on_delete=models.PROTECT,
                                       related_name="creation_group")
    record_card = models.ForeignKey(RecordCard, verbose_name=_("RecordCard"), on_delete=models.PROTECT)
    is_opened = models.BooleanField(_("Is opened"), default=True, help_text=_("Conversation is opened"))
    require_answer = models.BooleanField(_("Require answer"), default=True,
                                         help_text=_("Indicates if an answer is expected"))
    groups_involved = models.ManyToManyField(
        Group, verbose_name=_("Groups involved"), blank=True, through="ConversationGroup",
        help_text=_("Groups involved on conversation, if it's Internal Type"))
    external_email = models.EmailField(_("External email"), blank=True,
                                       help_text=_("External email involved on conversation, if it's External Type"))

    def __str__(self):
        return "{} - {} - {} - {}".format(self.record_card.pk, self.pk, self.type, self.is_opened)

    def unread_messages_by_group(self, group):
        """
        Get the number of unread messages of conversation from a group
        :param group: Group to known the unread messages
        :return: If we have registers return unread_messages registered on the db, else return the number of messages
        """
        try:
            return ConversationUnreadMessagesGroup.objects.get(conversation=self, group=group).unread_messages
        except ConversationUnreadMessagesGroup.DoesNotExist:
            # If group hasn't any ConversationUnreadMessagesGroup from this conversations means that the group
            # has read the messages
            return 0

    def update_unread_messages(self, message_group):
        """
        Update the number of unread messages of a conversation for every group on it.
        Groups on it: all the groups that have writen a message on the conversation and, for INTERNAL type conversation,
         the groups involved
        :param message_group: group that has written the message
        :return:
        """
        groups_messages_ids = self.message_set.exclude(group=message_group).values_list("group_id", flat=True)

        if self.type == self.INTERNAL:
            groups_messages_ids = Conversation.objects.internal_conversation_groups(
                self, groups_messages_ids, message_group)

        for groups_messages_id in groups_messages_ids:
            unread, created = ConversationUnreadMessagesGroup.objects.get_or_create(
                conversation=self, group_id=groups_messages_id, defaults={"unread_messages": 1})
            if not created:
                unread.unread_messages += 1
                unread.save()

    def reset_unread_messages_bygroup(self, group):
        """
        Set the unread messages to 0 when a group has read it and delete it to not show notifications
        :param group: Group to reset its number of unread messages
        :return:
        """
        unread, created = ConversationUnreadMessagesGroup.objects.get_or_create(conversation=self, group=group)
        unread.delete()


class ConversationGroup(UserTrack):

    conversation = models.ForeignKey(Conversation, verbose_name=_("Conversation"), on_delete=models.PROTECT)
    group = models.ForeignKey(Group, verbose_name=_("Group"), on_delete=models.PROTECT)
    enabled = models.BooleanField(verbose_name=_("Enabled"), default=True, db_index=True)

    def __str__(self):
        return "{} - {}".format(self.conversation.__str__(), self.group.description)


class ConversationUnreadMessagesGroup(CustomSafeDeleteModel):

    created_at = models.DateTimeField(verbose_name=_("Creation date"), auto_now_add=True)
    conversation = models.ForeignKey(Conversation, verbose_name=_("Conversation"), on_delete=models.PROTECT)
    group = models.ForeignKey(Group, verbose_name=_("Group"), on_delete=models.PROTECT)
    unread_messages = models.IntegerField(default=0)

    def __str__(self):
        return "{} - {} - {}".format(self.conversation.__str__(), self.group.description, self.unread_messages)


class Message(UserTrack):
    conversation = models.ForeignKey(Conversation, verbose_name=_("Conversation"), on_delete=models.PROTECT)
    group = models.ForeignKey(Group, verbose_name=_("Group"), on_delete=models.PROTECT)
    record_state = models.ForeignKey(RecordState, on_delete=models.PROTECT,
                                     help_text=_("State of the RecordCard on the creation of the message"))
    text = models.TextField(_("Text Message"))
    # Hash field is nullable because of unique=True as explained in
    # https://docs.djangoproject.com/en/2.2/ref/models/fields/#null
    hash = models.CharField(verbose_name=_("Message hash"), max_length=100, blank=True, null=True, unique=True,
                            db_index=True)
    is_answered = models.BooleanField(_(u"Messages is answered"), default=False)

    class Meta:
        ordering = ("-created_at", )

    def __str__(self):
        return "{} - {}".format(self.conversation.__str__(), self.text[:15])

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if not self.pk and self.conversation.type in Conversation.HASH_TYPES:
            signer = Signer(salt=settings.MESSAGE_HASH_SALT)
            self.hash = signer.signature(timezone.now().strftime("%Y%m%d%H%M%S.%f"))
        super().save(force_insert, force_update, using, update_fields)

    @property
    def response_time_expired(self):
        if self.is_answered:
            return False
        limit_answer_days = int(Parameter.get_parameter_by_key("DIES_RESPOSTA_CI", 7))
        limit_response = self.created_at + timedelta(days=limit_answer_days)
        return limit_response < timezone.now()
