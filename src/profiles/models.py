from typing import List

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.db.models import Q

from custom_safedelete.managers import CustomSafeDeleteManager
from iris_masters.models import LetterTemplate, Parameter
from django.utils.translation import gettext_lazy as _

from mptt.models import MPTTModel, TreeForeignKey

from custom_safedelete.models import CustomSafeDeleteModel
from iris_masters.models import UserTrack, UserIdField, Application, InputChannel
from iris_masters.mixins import CleanEnabledBase, CleanSafeDeleteBase
from main.api.validators import EmailCommasSeparatedValidator
from main.cachalot_decorator import iris_cachalot
from profiles.managers import GroupIRISManager, GroupInputChannelManager
import logging

logger = logging.getLogger(__name__)

class PermissionCategory(UserTrack):
    """
    Groups the permissions.
    """
    objects = iris_cachalot(models.Manager(), extra_fields=["codename"])

    description = models.CharField(max_length=60)
    codename = models.CharField(max_length=20)

    def __str__(self):
        return self.description


class Permission(UserTrack):
    """
    A permission represents a functionality or service provided by the application.
    """
    objects = iris_cachalot(models.Manager(), extra_fields=["codename", "category"])

    description = models.CharField(max_length=120)
    codename = models.CharField(max_length=50, db_index=True)
    category = models.ForeignKey(PermissionCategory, null=True, blank=True, related_name="permissions",
                                 on_delete=models.SET_NULL)

    def __str__(self):
        return self.description


class Profile(CleanSafeDeleteBase, UserTrack, CustomSafeDeleteModel):
    """
    The profile represent a pattern of permissions shared by many groups.
    """
    objects = iris_cachalot(CustomSafeDeleteManager())

    field_error_name = "description"

    description = models.CharField(max_length=80)
    permissions = models.ManyToManyField(Permission, through="ProfilePermissions", related_name="profiles")

    def get_extra_filter_fields(self):
        """
        :return: Dict with filter fields
        """
        return {"description": self.description}

    class Meta:
        unique_together = ("description", "deleted")
        ordering = ("description",)

    def disable_profile_usages(self):
        GroupProfiles.objects.filter(profile_id=self.pk).update(enabled=False)
        ProfileUserGroup.objects.filter(profile_id=self.pk).update(enabled=False)
        ProfilePermissions.objects.filter(profile_id=self.pk).update(enabled=False)

    def __str__(self) -> str:
        return self.description


class ProfilePermissions(CleanEnabledBase, UserTrack):
    """
    Profile permissions assignation
    """
    field_error_name = "permission"

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    enabled = models.BooleanField(verbose_name=_("Enabled"), default=True, db_index=True)

    def get_extra_filter_fields(self):
        """
        :return: Dict with filter fields
        """
        return {"permission": self.permission}


def group_icons_path(instance, filename):
    now = timezone.now()
    return "group_icons/{}/{}/{}/{}".format(now.year, now.month, now.day, filename)


class Group(UserTrack, CustomSafeDeleteModel, MPTTModel):
    """
    IRS_TB_MA_PERFIL

    The group represents a unit of work of the organization. The Groups can have levels, following a tree structure.

    Each group have n profiles that define which permissions will have the Group.
    """

    objects = iris_cachalot(GroupIRISManager(), extra_fields=["parent", "parent_id", "is_anonymous"])

    group_plate = models.CharField(max_length=100, help_text=_("Group Plate"), blank=True, db_index=True)
    profiles = models.ManyToManyField(Profile, through="GroupProfiles", blank=True, related_name="groups")
    parent = TreeForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="children")
    description = models.CharField(verbose_name=_("Description"), max_length=40, db_index=True)
    profile_hierarchical = models.PositiveIntegerField(verbose_name=_("Profile Hierarchical"), default=0)
    profile_ctrl_user_id = UserIdField(verbose_name=_("Profile ctrl user id"), db_index=True)
    dist_sect_id = models.PositiveIntegerField(verbose_name=_("Dist sect id"), default=0)
    service_line = models.PositiveIntegerField(verbose_name=_("Service line"), null=True, blank=True)
    sector = models.PositiveIntegerField(verbose_name=_("Sector"), null=True, blank=True)
    no_reasigned = models.BooleanField(verbose_name=_("No Reasigned"), default=True)
    email = models.EmailField(verbose_name=_("Email"), blank=True)
    signature = models.CharField(verbose_name=_("Signature"), blank=True, max_length=200)
    icon = models.FileField(verbose_name=_("Icon"), blank=True, null=True, upload_to=group_icons_path)
    letter_template_id = models.ForeignKey(LetterTemplate, on_delete=models.SET_NULL,
                                           verbose_name=_('Letter template id'), null=True, blank=True)
    last_pending_delivery = models.DateField(verbose_name=_("Last pending delivery"), null=True, blank=True)
    citizen_nd = models.BooleanField(verbose_name=_("Citizen ND"), default=False)
    certificate = models.BooleanField(verbose_name=_("Certificate"), default=True)
    super_sector = models.PositiveIntegerField(verbose_name=_("Super Sector"), default=0)
    tree_levels = models.SmallIntegerField(verbose_name=_("Number of levels above for seeing the tree"), default=1)
    validate_thematic_tree = models.NullBooleanField(verbose_name=_("Validate Thematic Tree"))
    is_anonymous = models.BooleanField(verbose_name=_("Is AnonymousGroup"), default=False)
    is_ambit = models.BooleanField(verbose_name=_("Is Ambit"), default=False)
    reassignments = models.ManyToManyField("self", through="GroupReassignation", blank=True, symmetrical=False)
    notifications_emails = models.TextField(verbose_name=_("Notifications emails list"), blank=True,
                                            validators=[EmailCommasSeparatedValidator()],
                                            help_text=_("List of emails (separated by commas) to send notifications"))
    records_next_expire = models.BooleanField(verbose_name=_("Records Next to expire"), default=False,
                                              help_text=_("Send notifications for records next to expire"))
    records_next_expire_freq = models.PositiveSmallIntegerField(
        verbose_name=_("Records Next to expire frequency (days)"), default=1, validators=[MinValueValidator(1)])
    records_next_expire_notif_date = models.DateField(_("Records next to expire last notify date"),
                                                      null=True, blank=True,
                                                      help_text=_("Last day records next to expire has been notified"))
    records_allocation = models.BooleanField(verbose_name=_("Records Allocation"), default=False,
                                             help_text=_("Send notifications for records allocation"))
    pend_records = models.BooleanField(verbose_name=_("Pending records"), default=False,
                                       help_text=_("Send notifications for pending records"))
    pend_records_freq = models.PositiveSmallIntegerField(verbose_name=_("Pending records frequency (days)"), default=1,
                                                         validators=[MinValueValidator(1)])
    pend_records_notif_date = models.DateField(_("Pending records last notify date"), null=True, blank=True,
                                               help_text=_("Last day pending records  has been notified"))
    pend_communication = models.BooleanField(verbose_name=_("Records with pending communications"), default=False,
                                             help_text=_("Send notifications for records with pending communications"))
    pend_communication_freq = models.PositiveSmallIntegerField(
        verbose_name=_("Pending communications records frequency (days)"), default=1, validators=[MinValueValidator(1)])
    pend_communication_notif_date = models.DateField(
        _("Records with pending communications last notify date"), null=True, blank=True,
        help_text=_("Last day records with pending communications has been notified"))
    ambit_coordinator = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True,
                                          related_name="coordinator")
    is_mobile = models.BooleanField(verbose_name=_("Is Mobile"), default=False)

    class Meta:
        unique_together = ("description", "profile_ctrl_user_id", "deleted")

    def __str__(self):
        return self.description

    def save(self, keep_deleted=False, **kwargs):

        super().save(keep_deleted, **kwargs)

        ambit_parent = self.get_ambit_parent()
        if ambit_parent != self.ambit_coordinator:
            self.ambit_coordinator = ambit_parent
            self.save()

    def delete(self, force_policy=None, **kwargs):
        super().delete(force_policy, **kwargs)
        for children_group in self.get_children():
            children_group.delete()

    def calculate_group_plate(self):
        ancestors = self.get_ancestors(include_self=True)
        plate = ""
        for ancestor in ancestors:
            plate += "{}-".format(ancestor.pk)
        return plate

    def get_ancestors(self, ascending=False, include_self=False):
        return super().get_ancestors(ascending, include_self).filter(deleted__isnull=True)

    def get_descendants(self, include_self=False, include_deleted=False):
        descendants = super().get_descendants(include_self)
        if not include_deleted:
            return descendants.filter(deleted__isnull=True)
        return descendants

    def get_children(self):
        return super().get_children().filter(deleted__isnull=True)

    def get_isambit_groups(self, dair_group):
        """
        Get the isambit groups: all ascendants except the Dair Group and its descendants
        :param dair_group: DAIR Group
        :return: List of ancestors and descendants of isambit group
        """
        ancestors = self.get_ancestors().exclude(pk=dair_group.pk) if dair_group else self.get_ancestors()
        descendants = self.get_descendants()
        return list(ancestors) + list(descendants)

    def ambit_ancestor(self, dair_group):
        """
        Look for the first is_ambit ancestor except DAIR
        :param dair_group: DAIR Group
        :return: First is_ambit ancestor if its exists, otherwise None
        """
        ancestors = self.get_ancestors(ascending=True)
        if dair_group:
            ancestors = ancestors.exclude(pk=dair_group.pk)

        for ancestor in ancestors:
            if ancestor.is_ambit:
                return ancestor

    def get_ambit_parent(self):
        """
        :return: Return ambit parent group if its exists, otherwise None
        """
        if self.is_ambit:
            return self
        else:
            return self.ambit_ancestor(Group.get_dair_group())

    def get_ambit_ancestors_groups(self, ambit_ancestor):
        """
        Get the ambit of an ancestor excluding itself
        :param ambit_ancestor: Ancestor group
        :return: List of ambit ancestor descendants excluding itself
        """
        return list(ambit_ancestor.get_descendants(include_self=True).exclude(pk=self.pk, is_anonymous=False))

    def get_noambit_groups(self, dair_group):
        """
        Get the no isambit groups: all ascendants except the Dair Group
        :param dair_group: DAIR Group
        :return: List of ancestors of a no isambit group
        """
        ancestors = self.get_ancestors().exclude(pk=dair_group.pk) if dair_group else self.get_ancestors()
        return list(ancestors)

    def ambit(self):
        dair_group = Group.get_dair_group()
        if self.is_ambit:
            return self.get_isambit_groups(dair_group)
        else:
            ambit_ancestor = self.ambit_ancestor(dair_group)
            if ambit_ancestor:
                return self.get_ambit_ancestors_groups(ambit_ancestor)

            return self.get_noambit_groups(dair_group)

    @property
    def ambit_ids(self):
        ambit = self.ambit()
        return [ambit_group.pk for ambit_group in ambit] if ambit else []

    @property
    def ambits_ancestors(self):
        """

        :return: List of ambits of the current group
        """
        return [ancestor for ancestor in self.get_ancestors(include_self=True) if ancestor.is_ambit]

    @property
    def group_permissions_codes(self):
        group_profiles_ids = self.groupprofiles_set.filter(enabled=True).values_list("profile_id", flat=True)
        return ProfilePermissions.objects.filter(
            enabled=True, profile_id__in=group_profiles_ids).select_related(
            "permission").values_list("permission__codename", flat=True)

    @staticmethod
    def get_dair_group():
        return Group.objects.filter(parent__isnull=True, is_anonymous=False, deleted__isnull=True).first()

    @staticmethod
    def get_default_error_derivation_group():
        try:
            perfi_dair_error = int(Parameter.get_parameter_by_key("PERFIL_DAIR_ERROR", 356417))
            return Group.objects.get(pk=perfi_dair_error)
        except Group.DoesNotExist:
            return Group.get_dair_group()

    @staticmethod
    def get_initial_group_for_record():
        try:
            perfi_dair_initial = int(Parameter.get_parameter_by_key("PERFIL_DAIR_INICIAL", 406644))
            return Group.objects.get(pk=perfi_dair_initial)
        except Group.DoesNotExist:
            return Group.get_dair_group()

    def get_ambit_coordinator(self):
        is_coordinator = self.get_descendants().filter(level=self.level+2).exists()
        if is_coordinator or not self.parent:
            return self
        return self.parent.get_ambit_coordinator()


def get_anonymous_group():
    try:
        anonym_group, _ = Group.objects.get_or_create(user_id="AnonymousGroup", description="AnonymousGroup",
                                                      profile_ctrl_user_id="AnonymousGroup", is_anonymous=True)
    except Group.MultipleObjectsReturned:
        anonym_group = Group.objects.filter(profile_ctrl_user_id="AnonymousGroup").first()
    return anonym_group


class ApplicationGroup(CleanEnabledBase, UserTrack):
    """
    IRS_TB_MA_SISTEMA_PERFIL
    """
    objects = iris_cachalot(models.Manager(), extra_fields=["group_id", "application_id"])

    field_error_name = "application"

    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    enabled = models.BooleanField(verbose_name=_("Enabled"), default=True, db_index=True)

    def __str__(self):
        return "{} - {}".format(self.application.description, self.group.description)

    def get_extra_filter_fields(self):
        """
        :return: Dict with filter fields
        """
        return {"group": self.group, "application": self.application}


class UserGroup(models.Model):
    objects = iris_cachalot(models.Manager(), extra_fields=["user_id", "group_id"])

    user = models.OneToOneField(User, verbose_name=_("User"), on_delete=models.CASCADE)
    group = models.ForeignKey(Group, verbose_name=_("Group"), null=True, on_delete=models.CASCADE)
    groups = models.ManyToManyField(Group, through="GroupsUserGroup", blank=True, related_name="groups")
    profiles = models.ManyToManyField(Profile, through="ProfileUserGroup", blank=True, related_name="profiles")

    class Meta:
        ordering = ("user__username",)

    def __str__(self):
        return "{} - {}".format(self.user.username, self.group.description if self.group else "")

    def get_user_permissions(self) -> List[Permission]:
        if not settings.INTERNAL_GROUPS_SYSTEM:
            q = Q(profile__group_profiles__group=self.group)
        else:
            user_groups_ids = self.groupsusergroup_set.filter(
                enabled=True).values_list("group_id", flat=True)
            q = Q(profile__group_profiles__group_id__in=user_groups_ids, profile__group_profiles__enabled=True)
            q |= Q(profile__profileusergroup__user_group_id=self.id, profile__profileusergroup__enabled=True)
        perms_qs = ProfilePermissions.objects.filter(enabled=True).filter(q).select_related("permission").only(
            "permission__id", "permission__codename").distinct()
        return [p.permission for p in perms_qs]

    @property
    def has_no_group(self):
        return not self.group or self.group == get_anonymous_group()


class GroupsUserGroup(CleanEnabledBase, UserTrack):
    field_error_name = "group"

    user_group = models.ForeignKey(UserGroup, verbose_name=_("User Group"), on_delete=models.CASCADE)
    group = models.ForeignKey(Group, verbose_name=_("Group"), on_delete=models.CASCADE)
    enabled = models.BooleanField(verbose_name=_("Enabled"), default=True, db_index=True)

    def __str__(self):
        return "User group: {} to {}".format(self.user_group.user.username, self.group.description)

    def get_extra_filter_fields(self):
        """
        :return: Dict with filter fields
        """
        return {"user_group": self.user_group, "group": self.group}


class ProfileUserGroup(CleanEnabledBase, UserTrack):
    field_error_name = "group"

    SPANISH = "ES"
    GALICIAN = "GL"
    LANGUAGES = [
        (SPANISH, "Español"),
        (GALICIAN, "Galego")
    ]

    user_group = models.ForeignKey(UserGroup, verbose_name=_("User Group"), on_delete=models.CASCADE)
    profile = models.ForeignKey(Profile, verbose_name=_("Profile"), on_delete=models.CASCADE)
    enabled = models.BooleanField(verbose_name=_("Enabled"), default=True, db_index=True)
    prefered_language = models.CharField(verbose_name="prefered_language", choices=LANGUAGES, default=GALICIAN, max_length=2)

    def __str__(self):
        return "User group: {} to {}".format(self.user_group.user.username, self.profile.description)

    def get_extra_filter_fields(self):
        """
        :return: Dict with filter fields
        """
        return {"user_group": self.user_group, "profile": self.profile}


class AccessLog(models.Model):
    group = models.ForeignKey(Group, verbose_name=_("Group"), on_delete=models.CASCADE)
    user_group = models.ForeignKey(UserGroup, verbose_name=_("User Group"), on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def register_for_user_group(user_group):
        return AccessLog.objects.create(user_group=user_group, group=user_group.group)


class GroupReassignation(CleanEnabledBase, UserTrack):
    """
    IRS_TB_MA_PERMISOS_REASIG
    """
    objects = iris_cachalot(models.Manager(), extra_fields=["origin_group_id", "reasign_group_id"])

    field_error_name = "reasign_group"

    origin_group = models.ForeignKey(Group, verbose_name=_("Origin Group"), on_delete=models.PROTECT, db_index=True)
    reasign_group = models.ForeignKey(Group, verbose_name=_("Reasign Group"), on_delete=models.PROTECT,
                                      related_name="reasignations")
    enabled = models.BooleanField(verbose_name=_("Enabled"), default=True, db_index=True)

    def __str__(self):
        return "Reasign from {} to {}".format(self.origin_group.description, self.reasign_group.description)

    def clean(self):
        super().clean()
        if self.origin_group_id == self.reasign_group_id:
            error_message = _("Origin Group and Reasignation Group can not be the same")
            raise ValidationError({"origin_group": error_message, "reasign_group": error_message})

    def get_extra_filter_fields(self):
        """
        :return: Dict with filter fields
        """
        return {"origin_group": self.origin_group, "reasign_group": self.reasign_group}


class GroupInputChannel(CleanEnabledBase, UserTrack):
    """
    IRS_TB_MA_PERFIL_CANAL
    """
    objects = iris_cachalot(GroupInputChannelManager(), extra_fields=["group_id", "input_channel_id"])
    field_error_name = "input_channel"

    group = models.ForeignKey(Group, verbose_name=_("Group"), on_delete=models.PROTECT, db_index=True)
    input_channel = models.ForeignKey(InputChannel, verbose_name=_("Input Channel"), on_delete=models.PROTECT,
                                      db_index=True)
    enabled = models.BooleanField(verbose_name=_("Enabled"), default=True, db_index=True)
    order = models.PositiveIntegerField(default=0, db_index=True)
    update_user_id = UserIdField(verbose_name=_("Update User ID"), blank=True)

    def __str__(self):
        return "{} - {}".format(self.group.description, self.input_channel.description)

    def get_extra_filter_fields(self):
        """
        :return: Dict with filter fields
        """
        return {"group": self.group, "input_channel": self.input_channel}


class GroupProfiles(UserTrack):
    """
    Group profiles assignation
    """
    objects = iris_cachalot(models.Manager(), extra_fields=["group_id", "profile_id"])

    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="group_profiles")
    enabled = models.BooleanField(verbose_name=_("Enabled"), default=True, db_index=True)


class GroupDeleteRegister(UserTrack):
    """
    Model to register group's deletion and control the state of the deletion process
    """
    objects = iris_cachalot(models.Manager(), extra_fields=["process_finished"])

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="register_delete_groups")
    deleted_group = models.ForeignKey(Group, on_delete=models.CASCADE)
    reasignation_group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="deleted_groups")
    only_open = models.BooleanField(_("Only Open RecordCards"), default=True)
    process_finished = models.BooleanField(_("Process finished"), default=False,
                                           help_text=_("Shows if recordCard reassignations and derivations "
                                                       "reassignations has finished correctly"))
