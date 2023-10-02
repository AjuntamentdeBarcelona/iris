from profiles.models import Permission, PermissionCategory


class OverrideException(Exception):
    pass


class PermissionRegistry:
    """
    Class for registering the different application permission and available services.
    Each django app of the system will register its own services by registering it during the initialization, in the
    ready method of the AppConfig class.

    After each migrate, this application will create the permission on the D. This approach is similar to the Django's
    contrib permission system.
    """
    def __init__(self):
        self.registry = {}

    def register(self, permission_uid, config, force_override=False):
        """
        Registers the permission with a given uid.
        :param permission_uid:
        :param config:
        :param force_override: If False, will raise an exception when trying to override a record. This option is useful
         for avoiding involuntary errors during registration.
        """
        if permission_uid in self.registry and not force_override:
            raise OverrideException("Trying to override the registered uid {}.".format(permission_uid))
        self.registry[permission_uid] = config

    def unregister(self, permission_uid):
        """
        Unregisters the permission with the given uid.
        :param permission_uid:
        :return: Config for the uid
        :raises: KeyError if the permission uid does not exist.
        """
        self.registry.pop(permission_uid)

    def create_db_permissions(self):
        Permission.objects.exclude(codename__in=self.registry.keys()).delete()
        for permission, config in self.registry.items():
            try:
                permission = Permission.objects.get(codename=permission)
                permission.description = config.get("description", permission)
                permission.category = self._create_db_category(config)
                permission.save()
            except Permission.DoesNotExist:
                Permission.objects.create(
                    codename=permission,
                    description=config.get("description", permission),
                    category=self._create_db_category(config)
                )
            except Permission.MultipleObjectsReturned:
                Permission.objects.filter(codename=permission).delete()
                Permission.objects.create(
                    codename=permission,
                    description=config.get("description", permission),
                    category=self._create_db_category(config)
                )

    def _create_db_category(self, config):
        if config.get("category"):
            try:
                cat = PermissionCategory.objects.get(codename=config.get("category"))
                cat.description = config.get("category_label", config.get("category"))
                cat.save()
                return cat
            except PermissionCategory.DoesNotExist:
                return PermissionCategory.objects.create(
                    codename=config.get("category"),
                    description=config.get("category_label", config.get("category")),
                )
        return None


PERMISSIONS = PermissionRegistry()

CATEGORY = 'USERS'
ADMIN_GROUP = 'ADMIN_USERS'

PERMISSIONS.register(ADMIN_GROUP, {
    "description": "Menu - Administrar els operadors",
    "category": CATEGORY,
})
