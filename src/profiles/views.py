from collections import defaultdict

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.management import call_command
from django.db.models import Prefetch
from django.http import HttpResponseBadRequest, Http404
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from drf_yasg.utils import swagger_auto_schema
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.generics import RetrieveAPIView, CreateAPIView, ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import (HTTP_200_OK, HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN,
                                   HTTP_404_NOT_FOUND)
from rest_framework.views import APIView

from excel_export.mixins import ExcelDescriptionExportMixin
from iris_masters.models import InputChannelSupport, InputChannel, InputChannelApplicantType

from iris_masters.serializers import InputChannelRegularSerializer
from iris_masters.views import (BasicMasterViewSet, BasicMasterListApiView, BasicMasterAdminPermissionsMixin,
                                BasicOrderingFieldsSearchMixin)
from main.views import ModelCRUViewSet

from profiles.models import (Group, UserGroup, GroupInputChannel, Profile, Permission, GroupProfiles, GroupsUserGroup,
                             AccessLog, ProfileUserGroup)

from profiles.permission_registry import ADMIN_GROUP
from profiles.permissions import IrisPermissionChecker, IrisPermission
from profiles.serializers import (UserGroupSerializer, GroupSetSerializer, GroupSerializer, GroupShortSerializer,
                                  ProfileSerializer, PermissionSerializer, GroupDeleteRegisterSerializer,
                                  UserGroupsSerializer, UserGroupListSerializer, UserPreferencesSerializer, PreferencesOptionsSerializer)
from profiles.utils import get_user_groups_header_list
from profiles.tasks import (group_delete_action_execute, group_update_group_descendants_plates, profile_post_delete,
                            profiles_data_checks)

from main.api.schemas import (destroy_swagger_auto_schema_factory, create_swagger_auto_schema_factory,
                              update_swagger_auto_schema_factory, get_swagger_auto_schema_factory,
                              list_swagger_auto_schema_factory, retrieve_swagger_auto_schema_factory)
from themes.tasks import set_themes_ambits


class PermissionListView(BasicMasterListApiView):
    """
    List of Permission of the system. The endpoint:
     - is not paginated. The
     - supports search by description
    """
    filter_backends = (SearchFilter,)
    queryset = Permission.objects.all()
    search_fields = ("description",)
    serializer_class = PermissionSerializer
    pagination_class = None


class UserPermissionListView(PermissionListView):
    """
    Returns the list of permissions for functions and services for the logged user.
    """
    permission_classes = []

    def get_queryset(self):
        return IrisPermissionChecker.get_for_user(self.request.user).get_permissions()


@method_decorator(name="create", decorator=create_swagger_auto_schema_factory(ProfileSerializer))
@method_decorator(name="update", decorator=update_swagger_auto_schema_factory(ProfileSerializer))
@method_decorator(name="partial_update", decorator=update_swagger_auto_schema_factory(ProfileSerializer))
@method_decorator(name="destroy", decorator=destroy_swagger_auto_schema_factory())
@method_decorator(name="list", decorator=list_swagger_auto_schema_factory(ProfileSerializer))
class ProfileViewSet(ExcelDescriptionExportMixin, BasicMasterAdminPermissionsMixin, BasicOrderingFieldsSearchMixin,
                     BasicMasterViewSet):
    """
    Viewset to manage Profiles (CRUD).
    Administration permission needed to create, update and destroy.
    If a Profiles is deleted, all its usages will be disabled.
    The list endpoint:
     - is not paginated
     - can be exported to excel
     - can be ordered by description
     - supports unaccent search by description
    """

    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    search_fields = ("#description",)
    pagination_class = None
    filename = "profiles.xlsx"
    ordering_fields = ["description"]

    def perform_destroy(self, instance):
        instance.delete()
        profile_post_delete.delay(instance.pk)


@method_decorator(name="create", decorator=create_swagger_auto_schema_factory(GroupSerializer))
@method_decorator(name="update", decorator=update_swagger_auto_schema_factory(GroupSerializer))
@method_decorator(name="retrieve", decorator=retrieve_swagger_auto_schema_factory(GroupSerializer))
@method_decorator(name="partial_update", decorator=update_swagger_auto_schema_factory(GroupSerializer))
class GroupResponsibleViewSet(BasicMasterAdminPermissionsMixin, ModelCRUViewSet):
    """
    Viewset to manage Responsible Groups at Task Manager
    """
    permission_classes = (IsAuthenticated,)
    filter_backends = (SearchFilter,)
    serializer_class = GroupSerializer
    search_fields = ("description",)
    short_serializer_class = GroupShortSerializer

    def get_queryset(self):
        user_group = self.request.user.usergroup.group
        return Group.objects.filter(
            deleted__isnull=True, is_anonymous=False, group_plate__startswith=user_group.group_plate
        ).order_by('description')

    def perform_create(self, serializer):
        group = serializer.save()
        self.queue_plates_task(group)

    def perform_update(self, serializer):
        previous_parent = serializer.instance.parent
        group = serializer.save()
        if previous_parent != group.parent:
            set_themes_ambits.delay()
        self.queue_plates_task(group)

    @staticmethod
    def queue_plates_task(group):
        """
        Queue the tasks to calculate and set group and its descendants plates

        :param group: group object
        :return:
        """
        group_update_group_descendants_plates.delay(group.pk)


@method_decorator(name="create", decorator=create_swagger_auto_schema_factory(GroupSerializer))
@method_decorator(name="update", decorator=update_swagger_auto_schema_factory(GroupSerializer))
@method_decorator(name="retrieve", decorator=retrieve_swagger_auto_schema_factory(GroupSerializer))
@method_decorator(name="partial_update", decorator=update_swagger_auto_schema_factory(GroupSerializer))
class GroupViewSet(BasicMasterAdminPermissionsMixin, ModelCRUViewSet):
    """
    Viewset to manage Groups (CRU).
    Administration permission needed to create and update.
    If a Profiles is deleted, all its usages will be disabled.
    The list endpoint supports search by description.
    When a Group is created or updated, its group_plate and its descendants are (re)calculated.
    """
    filter_backends = (SearchFilter,)
    serializer_class = GroupSerializer
    search_fields = ("description",)
    short_serializer_class = GroupShortSerializer

    def get_queryset(self):
        return Group.objects.filter(deleted__isnull=True, is_anonymous=False).order_by('description')

    def perform_create(self, serializer):
        group = serializer.save()
        self.queue_plates_task(group)

    def perform_update(self, serializer):
        previous_parent = serializer.instance.parent
        group = serializer.save()
        if previous_parent != group.parent:
            set_themes_ambits.delay()
        self.queue_plates_task(group)

    @staticmethod
    def queue_plates_task(group):
        """
        Queue the tasks to calculate and set group and its descendants plates

        :param group: group object
        :return:
        """
        group_update_group_descendants_plates.delay(group.pk)


@method_decorator(name="post", decorator=create_swagger_auto_schema_factory(GroupDeleteRegisterSerializer))
class CreateGroupDeleteRegisterView(BasicMasterAdminPermissionsMixin, CreateAPIView):
    """
    Create a group deletion Register and execute the group post delete action.
    The post delete action consist on reasign the derivations and records to the indicated group.
    """

    permission_classes = (IsAuthenticated,)
    serializer_class = GroupDeleteRegisterSerializer

    def perform_create(self, serializer):
        instance = serializer.save()
        # Once group delete register is created, we can delete the group and perform the group's post delete action
        instance.deleted_group.delete()
        group_delete_action_execute.delay(instance.pk)


@method_decorator(name="get", decorator=swagger_auto_schema(responses={
    HTTP_200_OK: UserGroupSerializer,
    HTTP_400_BAD_REQUEST: "Bad request: User has no available groups",
    HTTP_404_NOT_FOUND: "Not found: resource not exists",
}))
class UserGroupView(RetrieveAPIView):
    """
    Retrieve the user group information. If the user has not an assigend group and has groups available,
    the first one is set. The endpoint register the user acces to the platform.
    """
    queryset = UserGroup.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = UserGroupSerializer

    def retrieve(self, request, *args, **kwargs):
        if 'is_mobile' in self.request.query_params:
            is_mobile = self.request.query_params.get('is_mobile').lower()
            if is_mobile != 'true' and is_mobile != 'false':
                return HttpResponseBadRequest(content=_("is_mobile must be true or false"))
        instance = self.get_object()
        if not settings.INTERNAL_GROUPS_SYSTEM:
            user_groups = get_user_groups_header_list(self.request.META.get("HTTP_GRUPS"))
            if not user_groups:
                return HttpResponseBadRequest(content=_("User has no available groups"))

        if type(instance) != UserGroup:
            setattr(instance, 'imi_data', {})
            return instance

        user_groups = instance.groupsusergroup_set.filter(enabled=True)
        if instance.has_no_group and user_groups.exists():
            instance.group = user_groups.first().group
            instance.save()
        if instance.group is not None:
            AccessLog.register_for_user_group(instance)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def get_object(self):
        return get_object_or_404(self.queryset, user=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if hasattr(self.request.user, 'imi_data'):
            context["ctrl_user_groups"] = self.request.user.imi_data.get('grp', [])
            context["department"] = self.request.user.imi_data.get('dptcuser')
        if not isinstance(self.request.user, AnonymousUser):
            context["permissions"] = IrisPermissionChecker.get_for_user(self.request.user).get_permissions()
        return context


@method_decorator(name="post", decorator=swagger_auto_schema(
    request_body=GroupSetSerializer,
    responses={
        HTTP_200_OK: UserGroupSerializer,
        HTTP_404_NOT_FOUND: "Group with profile_ctrl_user_id does not exist",
        HTTP_400_BAD_REQUEST: "Bad Request"
    }
))
class UserGroupSetView(APIView):
    """
    Endpoint to set a group to a user. If user alredy exists on the system, it checks if the group is one of
    its available groups. Else, it creates the relation.
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        resp_ser = self.get_response_serializer(user_group=self.get_or_create_user_group())
        return Response(resp_ser.data, status=HTTP_200_OK)

    @cached_property
    def serializer_context(self):
        return {
            "ctrl_user_groups": self.request.META.get("HTTP_GRUPS"),
        }

    @cached_property
    def group(self):
        group_set_serializer = GroupSetSerializer(data=self.request.data, context=self.serializer_context)
        if group_set_serializer.is_valid(raise_exception=True):
            return get_object_or_404(Group, id=group_set_serializer.data["group_id"], deleted__isnull=True)

    def get_or_create_user_group(self):
        user_group, created = UserGroup.objects.get_or_create(user=self.request.user, defaults={"group": self.group})
        if not created:

            if settings.INTERNAL_GROUPS_SYSTEM:
                usergroup_groups = user_group.groupsusergroup_set.filter(
                    enabled=True).select_related("group").values_list("group", flat=True)
                if self.group.pk not in usergroup_groups:
                    return Response(_("Group is not one of the user options"), status=HTTP_400_BAD_REQUEST)

            user_group.group = self.group
            user_group.save()
            AccessLog.register_for_user_group(user_group)
            self.request.user.usergroup = user_group
            return user_group
        else:
            return GroupsUserGroup.objects.create(user_group=user_group, group=self.group)

    def get_response_serializer(self, user_group):
        return UserGroupSerializer(user_group, context={
            'permissions': IrisPermissionChecker.get_for_user(self.request.user).get_permissions(),
            **self.serializer_context
        })


@method_decorator(name="post", decorator=swagger_auto_schema(
    responses={
        HTTP_200_OK: "Group tree rebuilded",
        HTTP_403_FORBIDDEN: "User has no access permissions to this views"
    }
))
class GroupsRebuildTreeView(APIView):
    """
    Rebuilds the groups tree and delay tasks to recalculate group_plates and coordinators
    """

    def post(self, request, *args, **kwargs):
        call_command("invalidate_cachalot")
        Group.objects.rebuild()
        profiles_data_checks() if request.data.get('sync') else profiles_data_checks.delay()
        return Response(status=HTTP_200_OK)


class GroupInputChannelsView(BasicMasterListApiView):
    """
    List of InputChannels related to a group
    """
    serializer_class = InputChannelRegularSerializer

    def get_paginated_response(self, data):
        # Allow to create multirecords from internal claims
        if self.request.GET.get('multirecord', None):
            data.append(self.get_internal_claim())
        return super().get_paginated_response(data)

    def get_internal_claim(self):
        claim = InputChannel.objects.filter(pk=InputChannel.RECLAMACIO_INTERNA).first()
        return self.serializer_class(instance=claim).data

    def get_queryset(self):
        if not hasattr(self.request.user, "usergroup"):
            return InputChannel.objects.none()
        qs = self.get_record_channels() if self.request.GET.get('multirecord', None) else self.get_user_group_channels()
        qs = qs.prefetch_related(
            Prefetch(
                "inputchannelapplicanttype_set",
                queryset=InputChannelApplicantType.objects.filter(enabled=True, applicant_type__deleted__isnull=True
                                                                  ).select_related("applicant_type")
            ),
            Prefetch(
                "inputchannelsupport_set",
                queryset=InputChannelSupport.objects.filter(enabled=True,
                                                            support__deleted__isnull=True).select_related("support")
            )
        )
        if self.request.GET.get('id'):
            try:
                qs = qs.filter(id=int(self.request.GET.get('id')))
            except ValueError:
                raise Http404
        return qs

    def get_record_channels(self):
        return InputChannel.objects.filter(recordcard__normalized_record_id=self.request.GET.get('multirecord', None))

    def get_user_group_channels(self):
        input_channel_pks = GroupInputChannel.objects.get_input_channels_from_group(self.request.user.usergroup.group)
        return InputChannel.objects.filter(pk__in=input_channel_pks, deleted__isnull=True)


@method_decorator(name="get", decorator=get_swagger_auto_schema_factory(ok_message="Groups Tree"))
class GetGroupsTreeView(APIView):
    """
    Retrieve Groups Tree, providing the name and the childres of every available group.
    The anonymous group is not included.
    """

    def get(self, request, *args, **kwargs):
        self.childrens = defaultdict(list)
        root_nodes = []
        for group in Group.objects.filter(deleted__isnull=True, is_anonymous=False):
            if group.parent_id:
                self.childrens[group.parent_id].append(group)
            else:
                root_nodes.append(group)

        response = [self.get_childrens(root) for root in root_nodes]
        # Always will exists a root node (DAIR)
        return Response(response[0], status=HTTP_200_OK)

    def get_childrens(self, group):
        group_pk = group.pk
        return {
            "id": group_pk,
            "name": group.description,
            "childrens": [self.get_childrens(child_group) for child_group in self.childrens[group_pk]]
        }


class GroupAmbitView(APIView):
    """
    Retrieve the list of groups that are in the ambit of the indicated (ID) group
    """

    def get(self, request, *args, **kwargs):
        group = get_object_or_404(Group, pk=self.kwargs.get("pk"))
        return Response(data=[{"id": g.pk, "desc": g.description} for g in group.ambit()])


class SetProfileToAll(APIView):
    """
    Set the indicated profile (PK) to all the available groups
    """

    def post(self, request, *args, **kwargs):
        profile = get_object_or_404(Profile, pk=self.kwargs.get("pk"))
        for g in Group.objects.filter(deleted__isnull=True):
            perm, created = GroupProfiles.objects.get_or_create(profile=profile, group=g)
            if not perm.enabled:
                perm.enabled = True
                perm.save()
        return Response(status=200)


@method_decorator(name="create", decorator=create_swagger_auto_schema_factory(UserGroupsSerializer))
@method_decorator(name="update", decorator=update_swagger_auto_schema_factory(UserGroupsSerializer))
@method_decorator(name="partial_update", decorator=update_swagger_auto_schema_factory(UserGroupsSerializer))
@method_decorator(name="list", decorator=swagger_auto_schema(responses={
    HTTP_200_OK: "Users list",
    HTTP_403_FORBIDDEN: "Acces not allowed",
}))
class UserViewSet(ModelCRUViewSet):
    """
    Viewset to manage User Groups (CRUD).
    Administration Group permission needed to create, update and destroy.
    The list endpoint:
     - can be ordered by username
     - supports unaccent search by username
    """

    queryset = UserGroup.objects.all().select_related("user")
    serializer_class = UserGroupsSerializer
    short_serializer_class = UserGroupListSerializer
    search_fields = ("user__username",)
    filter_backends = (SearchFilter, DjangoFilterBackend, OrderingFilter)
    ordering_fields = ["user__username"]

    def get_permissions(self):
        return [IrisPermission(ADMIN_GROUP)]


@method_decorator(name="post", decorator=swagger_auto_schema(responses={
    HTTP_204_NO_CONTENT: "Profiles data checks task queued"
}))
class ProfilesDataChecksView(APIView):
    """
    Delay de post migrate profiles tasks:
     - recalculate group plates
     - set ambit coordinators
    """

    def post(self, request, *args, **kwargs):
        profiles_data_checks.delay()
        return Response(status=HTTP_204_NO_CONTENT)


@method_decorator(name="get", decorator=swagger_auto_schema(responses={
    HTTP_200_OK: UserPreferencesSerializer
}))
@method_decorator(name="patch", decorator=update_swagger_auto_schema_factory(UserPreferencesSerializer))
class ProfilePreferencesView(APIView):
    permission_classes = (IsAuthenticated,)

    """
    Modify and retrieve user's preferences
    """

    def get_queryset(self):
        return ProfileUserGroup.objects.get(user_group__user__id=self.request.user.id)

    def get(self, request, *args, **kwargs):
        return Response(status=HTTP_200_OK, data=UserPreferencesSerializer(instance=self.get_queryset()).data)

    def patch(self, request, *args, **kwargs):
        profile_user_group = self.get_queryset()
        serializer = UserPreferencesSerializer(instance=profile_user_group, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
        else:
            return Response(data=serializer.errors, status=HTTP_400_BAD_REQUEST)
        return Response(data=serializer.data, status=HTTP_200_OK)


@method_decorator(name="get", decorator=swagger_auto_schema(responses={
    HTTP_200_OK: PreferencesOptionsSerializer
}))
class PreferencesOptionsView(APIView):

    """
    Endpoint to list all the options aviable in preferences
    """
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        languages = []
        for language in ProfileUserGroup.LANGUAGES:
            languages.append({"code": language[0], "name": language[1]})
        data = {"languages": languages}
        serializer = PreferencesOptionsSerializer(data=data)
        serializer.is_valid()
        return Response(status=HTTP_200_OK, data=serializer.data)



@method_decorator(name="get", decorator=swagger_auto_schema(
    responses={
        HTTP_200_OK: UserGroupListSerializer
    }
))
class ProfileUsersView(ListAPIView):
    """
    Obtain all users from specific profile
    """

    permission_classes = (IsAuthenticated,)
    serializer_class = UserGroupListSerializer

    def get_queryset(self):
        user_group_ids = ProfileUserGroup.objects.select_related("profile", "user_group" ).filter(profile__id=self.kwargs["profile_id"]).values_list("user_group")
        return UserGroup.objects.filter(id__in=user_group_ids)
