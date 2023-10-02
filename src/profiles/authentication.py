import json
import logging

from django.conf import settings
from django.contrib.auth.models import User
from rest_framework import authentication

from profiles.models import Group, UserGroup, get_anonymous_group
from profiles.permissions import IrisPermissionChecker

logger = logging.getLogger(__name__)


class OAMAuthentication(authentication.BaseAuthentication):
    """
    OAM is the auth system for Barcelona Town hall.
    This was the default option for iris in its first version.
    """
    def authenticate(self, request):
        data = self.get_data(request)
        username = data.get('user')
        if not username:
            return None
        username = username.upper()
        user = self.get_user(username, data)
        setattr(user, 'imi_data', data)
        self.set_user_group(request, user)
        user.permission_checker = IrisPermissionChecker.get_for_user(user)

        return user, None

    def get_data(self, request):
        logger.info(request.META.get('HTTP_X_IMI_AUTHORIZATION', '{}'))
        return json.loads(request.META.get('HTTP_X_IMI_AUTHORIZATION', '{}'))

    @staticmethod
    def get_user(username, data):
        try:
            return User.objects.select_related("usergroup").get(username=username)
        except User.DoesNotExist:
            logger.info("FIRST LOGIN FOR USER {}".format(username))
            return User.objects.create(username=username, email=data.get('email'))

    def set_user_group(self, request, user):
        if settings.INTERNAL_GROUPS_SYSTEM:
            self.set_internal_groups(user)
        else:
            self.set_control_user_groups(request, user)

    @staticmethod
    def set_internal_groups(user):
        """
        Set usergroup to user if

        :param user: user of the request
        :return:
        """
        if not hasattr(user, "usergroup"):
            anonym_group = get_anonymous_group()
            UserGroup.objects.create(user=user, group=anonym_group)

    @classmethod
    def set_control_user_groups(cls, user):
        """
        Set usergroup to user taking in account control user groups

        :param request: http request
        :param user: user of the request
        :return:
        """

        ctrl_user_groups = user.imi_data.get('grp', [])
        if ctrl_user_groups:
            cls.recheck_ctrl_user_groups(user, ctrl_user_groups)
        else:
            cls.set_anon(user)

    @staticmethod
    def set_anon(user):
        # If the user has no groups set on the control user, we set one without permissions
        anonym_group = get_anonymous_group()
        if hasattr(user, "usergroup"):
            user.usergroup.group = anonym_group
            user.usergroup.save()
        else:
            UserGroup.objects.create(user=user, group=anonym_group)

    @staticmethod
    def recheck_ctrl_user_groups(user, ctrl_user_groups):
        # If the user has groups set on the control user
        if hasattr(user, "usergroup"):
            # if the user has a group set on IRIS
            if user.usergroup.group.profile_ctrl_user_id not in ctrl_user_groups:
                groups = Group.objects.get_user_groups(ctrl_user_groups)
                if groups:
                    user.usergroup.group = groups[0]
                    user.usergroup.save()
        else:
            # If the user has not a group set on IRIS
            groups = Group.objects.get_user_groups(ctrl_user_groups)
            if groups:
                UserGroup.objects.create(user=user, group=groups[0])

