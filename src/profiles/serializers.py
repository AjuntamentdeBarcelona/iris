from django.conf import settings
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from drf_extra_fields.fields import Base64ImageField

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import empty

from iris_masters.models import LetterTemplate
from iris_masters.serializers import LetterTemplateSerializer
from main.api.serializers import (SerializerCreateExtraMixin, SerializerUpdateExtraMixin, ManyToManyExtendedSerializer,
                                  IrisSerializer, GetGroupFromRequestMixin)
from main.api.validators import BulkUniqueRelatedValidator
from profiles.models import (UserGroup, Group, GroupReassignation, Profile, Permission, ProfilePermissions,
                             GroupProfiles, GroupInputChannel, GroupDeleteRegister, GroupsUserGroup, ProfileUserGroup,
                             get_anonymous_group)
from profiles.permissions import IrisPermissionChecker
from profiles.utils import get_user_groups_header_list


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ("id", "codename", "description", "category")
        read_only_fields = ("id", "codename", "description", "category")


class ProfilePermissionsSerializer(serializers.ModelSerializer):
    description = serializers.StringRelatedField(source="permission", read_only=True)

    class Meta:
        model = ProfilePermissions
        fields = ("permission", "description")


class ProfileSerializer(SerializerCreateExtraMixin, SerializerUpdateExtraMixin, IrisSerializer):
    post_create_extra_actions = True

    permissions = ManyToManyExtendedSerializer(source="profilepermissions_set", required=False,
                                               **{"many_to_many_serializer": ProfilePermissionsSerializer,
                                                  "model": ProfilePermissions, "related_field": "profile",
                                                  "to": "permission"})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validators = [
            BulkUniqueRelatedValidator(
                main_fields=["description"], filter_fields=(), queryset=Profile.objects.all(),
                message=_("The description must be unique and there is another Profile with the same.")
            )
        ]

    class Meta:
        model = Profile
        fields = ("id", "description", "permissions", "can_delete")

    def do_post_create_extra_actions(self, instance, validated_data):
        """
        Perform extra actions on create after the instance creation
        :param instance: Instance of the created object
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        self.set_permissions(instance, validated_data)

    def do_extra_actions_on_update(self, validated_data):
        """
        Perform extra actions on update
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        self.set_permissions(self.instance, validated_data)

    def set_permissions(self, instance, validated_data):
        """
        Insert profile permissions if they exist
        :param instance: Instance of the created/updated object
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        if "permissions" in self.initial_data:
            serializer_kwargs = {
                "many_to_many_serializer": ProfilePermissionsSerializer, "model": ProfilePermissions,
                "related_field": "profile", "to": "permission", "related_instance": instance
            }

            ser = ManyToManyExtendedSerializer(**serializer_kwargs, source="profilepermissions_set",
                                               data=self.initial_data["permissions"], context=self.context)
            ser.bind(field_name="", parent=self)
            if ser.is_valid():
                ser.save()
            validated_data.pop(ser.source, None)


class GroupReassignationSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupReassignation
        fields = ("reasign_group",)


class GroupCanReassignationSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupReassignation
        fields = ("origin_group",)


class GroupProfilesSerializer(serializers.ModelSerializer):
    description = serializers.StringRelatedField(source="profile", read_only=True)

    class Meta:
        model = GroupProfiles
        fields = ("profile", "description")


class GroupInputChannelSerializer(serializers.ModelSerializer):
    description = serializers.StringRelatedField(source="input_channel", read_only=True)

    class Meta:
        model = GroupInputChannel
        fields = ("input_channel", "order", "description")


class GroupSerializer(SerializerCreateExtraMixin, SerializerUpdateExtraMixin, serializers.ModelSerializer):
    post_create_extra_actions = True

    reassignments = ManyToManyExtendedSerializer(source="groupreassignation_set", required=False,
                                                 **{"many_to_many_serializer": GroupReassignationSerializer,
                                                    "model": GroupReassignation, "related_field": "origin_group",
                                                    "to": "reasign_group"})

    can_reasign_groups = ManyToManyExtendedSerializer(source="reasignations", required=False,
                                                      **{"many_to_many_serializer": GroupCanReassignationSerializer,
                                                         "model": GroupReassignation, "related_field": "reasign_group",
                                                         "to": "origin_group"})

    profiles = ManyToManyExtendedSerializer(source="groupprofiles_set", required=False,
                                            **{"many_to_many_serializer": GroupProfilesSerializer,
                                               "model": GroupProfiles, "related_field": "group", "to": "profile"})

    input_channels = ManyToManyExtendedSerializer(source="groupinputchannel_set", required=False,
                                                  **{"many_to_many_serializer": GroupInputChannelSerializer,
                                                     "model": GroupInputChannel, "related_field": "group",
                                                     "to": "input_channel", "extra_values_params": ["order"]})

    parent = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.filter(deleted__isnull=True),
        error_messages={"does_not_exist": _("The selected group does not exist or it was delete")})

    letter_template_id_id = serializers.PrimaryKeyRelatedField(
        source="letter_template_id", queryset=LetterTemplate.objects.filter(enabled=True),
        required=False, allow_null=True,
        error_messages={"does_not_exist": _("The selected letter template does not exist or is not enabled")})
    letter_template_id = LetterTemplateSerializer(read_only=True)
    icon = Base64ImageField(required=False, use_url=True, allow_null=True)

    class Meta:
        model = Group
        fields = ("id", "user_id", "created_at", "updated_at", "description", "profile_hierarchical",
                  "profile_ctrl_user_id", "dist_sect_id", "service_line", "sector", "no_reasigned", "email",
                  "signature", "icon", "letter_template_id", "letter_template_id_id", "parent",
                  "last_pending_delivery", "certificate", "super_sector", "validate_thematic_tree", "is_ambit",
                  "reassignments", "citizen_nd",
                  "profiles", "input_channels", "can_reasign_groups", "tree_levels", "notifications_emails",
                  "records_next_expire", "records_next_expire_freq", "records_allocation", "pend_records",
                  "pend_records_freq", "pend_communication", "pend_communication_freq")
        read_only_fields = ("id", "user_id", "created_at", "update_at", "profile_hierarchical", "dist_sect_id",
                            "service_line", "sector", "super_sector", "letter_template_id")

    def __init__(self, instance=None, data=empty, **kwargs):
        super().__init__(instance, data, **kwargs)
        if instance and instance == Group.get_dair_group():
            self.fields["parent"].required = False
            self.fields["parent"].allow_null = True

    def run_validation(self, data=empty):
        validated_data = super().run_validation(data)
        errors = {}
        if self.instance:
            if validated_data.get("parent") == self.instance:
                errors["parent"] = _("Group can not be assigned as its own parent")

            if self.instance == Group.get_dair_group() and validated_data.get("parent"):
                errors["parent"] = _("Group can not has a parent")

        self.check_icon_size(validated_data, errors)

        if errors:
            raise ValidationError(errors, code="invalid")

        return validated_data

    @staticmethod
    def check_icon_size(validated_data, errors):
        icon_file = validated_data.get("icon")
        if icon_file and icon_file.size > settings.MAX_FILE_SIZE_GROUP_ICON:
            errors["icon"] = _("File size must be lower than 1MB")

    def do_post_create_extra_actions(self, instance, validated_data):
        """
        Perform extra actions on create after the instance creation
        :param instance: Instance of the created object
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        self.set_reassignments(validated_data, instance)
        self.set_can_reasign_groups(validated_data, instance)
        self.set_group_profiles(instance, validated_data)
        self.set_input_channels(instance, validated_data)

    def do_extra_actions_on_update(self, validated_data):
        """
        Perform extra actions on update
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        self.set_reassignments(validated_data)
        self.set_can_reasign_groups(validated_data)
        self.set_group_profiles(self.instance, validated_data)
        self.set_input_channels(self.instance, validated_data)

    def set_reassignments(self, validated_data, related_instance=None):
        """
        Set reassignments from group
        :param validated_data: Dict with validated data of the serializer
        :param related_instance: group instance for GroupReassignation creation/update
        :return:
        """

        if "reassignments" in self.initial_data:
            serializer_kwargs = {
                "many_to_many_serializer": GroupReassignationSerializer,
                "model": GroupReassignation,
                "related_field": "origin_group",
                "to": "reasign_group",

            }
            if related_instance:
                serializer_kwargs["related_instance"] = related_instance

            ser = ManyToManyExtendedSerializer(**serializer_kwargs, source="groupreassignation_set",
                                               data=self.initial_data["reassignments"])
            ser.bind(field_name="", parent=self)
            if ser.is_valid():
                ser.save()
            validated_data.pop(ser.source, None)

    def set_can_reasign_groups(self, validated_data, related_instance=None):
        """
        Set groups that can reasign to the one that is being created/updated
        :param validated_data: Dict with validated data of the serializer
        :param related_instance: group instance for GroupCanReassign creation/update
        :return:
        """

        if "can_reasign_groups" in self.initial_data:
            serializer_kwargs = {
                "many_to_many_serializer": GroupCanReassignationSerializer,
                "model": GroupReassignation,
                "related_field": "reasign_group",
                "to": "origin_group",

            }
            if related_instance:
                serializer_kwargs["related_instance"] = related_instance

            ser = ManyToManyExtendedSerializer(**serializer_kwargs, source="reasignations",
                                               data=self.initial_data["can_reasign_groups"])
            ser.bind(field_name="", parent=self)
            if ser.is_valid():
                ser.save()
            validated_data.pop(ser.source, None)

    def set_group_profiles(self, instance, validated_data):
        """
        Insert profile permissions if they exist
        :param instance: Instance of the created/updated object
        :param validated_data: Dict with validated data of the serializer
        :return:
        """

        if "profiles" in self.initial_data:

            serializer_kwargs = {
                "many_to_many_serializer": GroupProfilesSerializer, "model": GroupProfiles,
                "related_field": "group", "to": "profile", "related_instance": instance
            }

            ser = ManyToManyExtendedSerializer(**serializer_kwargs, source="groupprofiles_set",
                                               data=self.initial_data["profiles"], context=self.context)
            ser.bind(field_name="", parent=self)
            if ser.is_valid():
                ser.save()
            validated_data.pop(ser.source, None)

    def set_input_channels(self, instance, validated_data):
        """
        Insert input channels that the group can manage

        :param instance: Instance of the created/updated object
        :param validated_data: Dict with validated data of the serializer
        :return:
        """

        if "input_channels" in self.initial_data:
            serializer_kwargs = {
                "many_to_many_serializer": GroupInputChannelSerializer,
                "model": GroupInputChannel, "related_field": "group",
                "to": "input_channel", "extra_values_params": ["order"], "related_instance": instance
            }

            ser = ManyToManyExtendedSerializer(**serializer_kwargs, source="groupinputchannel_set",
                                               data=self.initial_data["input_channels"], context=self.context)
            ser.bind(field_name="", parent=self)
            if ser.is_valid():
                ser.save()
            validated_data.pop(ser.source, None)


class GroupShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ("id", "description", "profile_ctrl_user_id", "dist_sect_id", "email", "signature", "citizen_nd",
                  "is_ambit", "is_mobile")
        read_only_fields = fields


class GroupSetSerializer(serializers.ModelSerializer):
    group_id = serializers.CharField(help_text="Group id")

    class Meta:
        model = Group
        fields = ("group_id",)

    def run_validation(self, data=empty):
        validated_data = super().run_validation(data)
        if not settings.INTERNAL_GROUPS_SYSTEM:
            user_groups = get_user_groups_header_list(self.context["ctrl_user_groups"])
            if not user_groups:
                raise ValidationError({"profile_ctrl_user_id": _("User has no available groups")},
                                      code="invalid")
            if validated_data.get("group_id") not in user_groups:
                raise ValidationError({"group_id": _("Ctrl user id is not selectable for this user")},
                                      code="invalid")

        return validated_data


class UserGroupSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    current_group = GroupShortSerializer(source="group")
    groups = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()

    class Meta:
        model = UserGroup
        fields = ("username", "current_group", "groups", "permissions", "department")

    def get_username(self, obj):
        return obj.user.username

    def get_groups(self, obj):
        request = self.context.get('request')
        query_params = request.query_params if request else []
        if 'is_mobile' in query_params:
            is_mobile = self.bool_to_string(self.context.get('request').query_params.get('is_mobile'))

            if not settings.INTERNAL_GROUPS_SYSTEM:
                groups = Group.objects.get_user_groups(
                    get_user_groups_header_list(self.context["ctrl_user_groups"]))
                return [GroupShortSerializer(group).data for group in groups.filter(is_mobile=is_mobile, group__deleted__isnull=True)]
            return [GroupShortSerializer(group.group).data
                    for group in
                    obj.groupsusergroup_set.filter(enabled=True, group__is_mobile=is_mobile, group__deleted__isnull=True).select_related("group")]
        else:
            if not settings.INTERNAL_GROUPS_SYSTEM:
                return [GroupShortSerializer(group).data for group in Group.objects.get_user_groups(
                    get_user_groups_header_list(self.context["ctrl_user_groups"]))]
            return [GroupShortSerializer(group.group).data
                    for group in obj.groupsusergroup_set.filter(enabled=True, group__deleted__isnull=True).select_related("group")]

    def get_permissions(self, obj):
        if not settings.INTERNAL_GROUPS_SYSTEM and "permissions" in self.context:
            permissions = self.context["permissions"]
        else:
            permissions = IrisPermissionChecker.get_for_user(obj.user).get_permissions()

        return PermissionSerializer(instance=permissions, many=True).data

    def get_department(self, obj):
        return self.context.get("headers")

    def bool_to_string(self, is_mobile):
        if is_mobile.lower() == 'true':
            return True
        return False


class GroupsUserGroupSerializer(serializers.ModelSerializer):
    description = serializers.StringRelatedField(source="group", read_only=True)

    class Meta:
        model = GroupsUserGroup
        fields = ("group", "description")


class ProfileUserGroupSerializer(serializers.ModelSerializer):
    description = serializers.StringRelatedField(source="profile", read_only=True)

    class Meta:
        model = ProfileUserGroup
        fields = ("profile", "description")


class UserGroupsSerializer(SerializerCreateExtraMixin, SerializerUpdateExtraMixin, serializers.ModelSerializer):
    post_create_extra_actions = True
    save_user_id = False

    username = serializers.CharField(source="user.username")
    group_id = serializers.PrimaryKeyRelatedField(
        source="group", queryset=Group.objects.filter(is_anonymous=False, deleted__isnull=True), required=False,
        error_messages={"does_not_exist": _("The selected group does not exist or it was delete")})
    groups = ManyToManyExtendedSerializer(source="groupsusergroup_set",
                                          **{"many_to_many_serializer": GroupsUserGroupSerializer,
                                             "model": GroupsUserGroup, "related_field": "user_group", "to": "group"})
    profiles = ManyToManyExtendedSerializer(source="profileusergroup_set",
                                            **{"many_to_many_serializer": ProfileUserGroupSerializer,
                                               "model": ProfileUserGroup, "related_field": "user_group",
                                               "to": "profile"})

    class Meta:
        model = UserGroup
        fields = ("id", "username", "group_id", "groups", "profiles")
        read_only_fields = ("id", "group_id")

    def run_validation(self, data=empty):
        validated_data = super().run_validation(data)
        validation_errors = {}
        self.check_user(validated_data)
        if validation_errors:
            raise ValidationError(validation_errors)
        return validated_data

    def check_user(self, validated_data):
        """
        Check that the user exists and update validated data

        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        username = validated_data["user"].get("username")
        username = username.upper()
        try:
            validated_data["user"] = User.objects.get(username=username)
        except User.DoesNotExist:
            validated_data["user"] = User.objects.create(username=username)

        dups = UserGroup.objects.filter(user=validated_data["user"])
        if self.instance:
            dups = dups.exclude(pk=self.instance.pk)
        if dups.exists():
            raise ValidationError({"username": _('This user exists and cannot be recreated.')})

    def check_group(self, validated_data, validation_errors):
        """
        Check that the current group is one of the possible groups

        :param validated_data: Dict with validated data of the serializer
        :param validation_errors: dict for validation errors
        :return:
        """
        groups_ids = [group["group"] for group in self.initial_data["groups"]]
        if validated_data["group"].pk not in groups_ids:
            error_message = _("The current group has to be included in the groups list")
            validation_errors.update({"group_id": error_message, "groups": error_message})

    def do_post_create_extra_actions(self, instance, validated_data):
        """
        Perform extra actions on create after the instance creation
        :param instance: Instance of the created object
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        self.set_available_groups(validated_data, related_instance=instance, creation=True)
        self.set_available_profiles(validated_data, related_instance=instance)

    def do_extra_actions_on_update(self, validated_data):
        """
        Perform extra actions on update

        :param validated_data: Dict with validated data of the serializer
        :return:
        """

        self.set_available_groups(validated_data, related_instance=self.instance)
        self.set_available_profiles(validated_data, related_instance=self.instance)

    def set_available_groups(self, validated_data, related_instance=None, creation=False):
        """
        Set available groups for user
        :param validated_data: Dict with validated data of the serializer
        :param related_instance: group instance for GroupReassignation creation/update
        :return:
        """

        if "groups" in self.initial_data:
            serializer_kwargs = {
                "many_to_many_serializer": GroupsUserGroupSerializer,
                "model": GroupsUserGroup,
                "related_field": "user_group",
                "to": "group",

            }
            if related_instance:
                serializer_kwargs["related_instance"] = related_instance

            ser = ManyToManyExtendedSerializer(**serializer_kwargs, source="groupsusergroup_set",
                                               data=self.initial_data["groups"])
            ser.bind(field_name="", parent=self)
            if ser.is_valid():
                ser.save()
            validated_data.pop(ser.source, None)

            if not self.initial_data["groups"] or \
                    not related_instance.groupsusergroup_set.filter(enabled=True, pk=related_instance.group_id):
                anonymous_group = get_anonymous_group()
                if creation:
                    related_instance.group = anonymous_group
                    related_instance.save()
                else:
                    validated_data["group"] = anonymous_group

    def set_available_profiles(self, validated_data, related_instance=None):
        """
        Set available profiles for user
        :param validated_data: Dict with validated data of the serializer
        :param related_instance: group instance for GroupReassignation creation/update
        :return:
        """

        if "profiles" in self.initial_data:
            serializer_kwargs = {
                "many_to_many_serializer": ProfileUserGroupSerializer,
                "model": ProfileUserGroup,
                "related_field": "user_group",
                "to": "profile",

            }
            if related_instance:
                serializer_kwargs["related_instance"] = related_instance

            ser = ManyToManyExtendedSerializer(**serializer_kwargs, source="profileusergroup_set",
                                               data=self.initial_data["profiles"])
            ser.bind(field_name="", parent=self)
            if ser.is_valid():
                ser.save()
            validated_data.pop(ser.source, None)


class UserGroupListSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username")
    email = serializers.CharField(source="user.email")

    class Meta:
        model = UserGroup
        fields = ("id", "username", "email")
        read_only_fields = ("id", "username", "email")


class GroupDeleteRegisterSerializer(SerializerCreateExtraMixin, GetGroupFromRequestMixin, serializers.ModelSerializer):
    extra_actions = True

    deleted_group_id = serializers.PrimaryKeyRelatedField(
        source="deleted_group", queryset=Group.objects.filter(deleted__isnull=True),
        error_messages={"does_not_exist": _("The selected Group does not exist or it's deleted")})
    reasignation_group_id = serializers.PrimaryKeyRelatedField(
        source="reasignation_group", queryset=Group.objects.filter(deleted__isnull=True),
        error_messages={"does_not_exist": _("The selected Group does not exist or it's deleted")})

    class Meta:
        model = GroupDeleteRegister
        fields = ("id", "user_id", "created_at", "updated_at", "deleted_group_id", "reasignation_group_id", "only_open")
        read_only_fields = ("id", "user_id", "created_at", "updated_at")

    def run_validation(self, data=empty):
        validated_data = super().run_validation(data)

        if validated_data["deleted_group"] == validated_data["reasignation_group"]:
            error_message = _("Deleted group and Reasignation group can not be the same")
            raise ValidationError({"deleted_group": error_message, "reasignation_group": error_message}, code="invalid")

        if validated_data["deleted_group"].get_children():
            raise ValidationError({"deleted_group": _("Group can not be deleted because it has descendants")},
                                  code="invalid")
        return validated_data

    def do_extra_actions_on_create(self, validated_data):
        validated_data["group"] = self.get_group_from_request(self.context.get("request"))


class ResponsibleProfileRegularSerializer(serializers.Serializer):
    description = serializers.CharField()


class UserPreferencesSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProfileUserGroup
        fields = ("prefered_language",)


class PreferencesLanguagesSerializer(serializers.Serializer):

    name = serializers.CharField()
    code = serializers.CharField()

class PreferencesOptionsSerializer(serializers.Serializer):

    languages = PreferencesLanguagesSerializer()
