from django.utils.functional import cached_property
from rest_framework.permissions import BasePermission


class IrisPermissionChecker:

    def __init__(self, user):
        self.user = user

    def has_permission(self, permission):
        """
        Checks if the user has permission for performing a given task.
        :param permission: Permission UID
        :return: True if the user has permission
        """
        return permission in self.permissions

    @cached_property
    def permissions(self):
        return {perm.codename: perm for perm in self.get_permissions()}

    def get_permissions(self):
        if hasattr(self.user, "usergroup") and self.user.usergroup:
            return self.user.usergroup.get_user_permissions()
        return []

    @staticmethod
    def get_for_user(user):
        if hasattr(user, "permission_checker"):
            return user.permission_checker
        checker = IrisPermissionChecker(user)
        setattr(user, "permission_checker", checker)
        return checker


class IrisPermission(BasePermission):
    """
    RestFramework view permission class for the IRIS permission model.
    """
    def __init__(self, permission):
        self.permission = permission

    def has_permission(self, request, view):
        return self.get_permission_checker(request.user).has_permission(self.permission)

    def get_permission_checker(self, user):
        return IrisPermissionChecker.get_for_user(user)
