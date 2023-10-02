from iris_masters.permissions import ADMIN
from profiles.permissions import IrisPermissionChecker


class GroupManageFiles:

    def __init__(self, record_card, group, user) -> None:
        self.record_card = record_card
        self.group = group
        self.user_perms = IrisPermissionChecker.get_for_user(user)
        super().__init__()

    def group_can_add_file(self) -> bool:
        """
        Group can add file if it's the responsible profile or the creation group of the record or has admin permissions

        :return: True if group can add file, else not
        """
        return (self.record_card.creation_group == self.group and not self.record_card.is_validated) or \
                self.record_card.group_can_tramit_record(self.group) or \
                self.user_perms.has_permission(ADMIN)

    def group_can_delete_file(self) -> bool:
        """
        Group can delete file if it's the responsible profile of the record or has admin permissions

        :return: True if group can delete file, else not
        """
        return (self.record_card.creation_group == self.group and not self.record_card.is_validated) or \
                self.record_card.group_can_tramit_record(self.group) or \
                self.user_perms.has_permission(ADMIN)
