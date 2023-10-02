from django.db.models import Manager
from mptt.managers import TreeManager

from custom_safedelete.managers import CustomSafeDeleteManager


class GroupIRISManager(TreeManager, CustomSafeDeleteManager):

    def get_user_groups(self, groups_codes):
        """
        :param groups_codes: List of groups codes
        :return: Queryset of enabled groups at IRIS from control user
        """
        return self.filter(deleted__isnull=True, profile_ctrl_user_id__in=groups_codes)


class GroupInputChannelManager(Manager):

    def get_input_channels_from_group(self, group):
        """
        :param group:
        :return: List of input channels pks allowed to a group
        """
        return self.filter(
            group=group, enabled=True, input_channel__deleted__isnull=True).values_list("input_channel_id", flat=True)
