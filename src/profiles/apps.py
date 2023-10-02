from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate
from django.utils.module_loading import import_string


class ProfilesConfig(AppConfig):
    name = "profiles"

    def ready(self):
        from profiles.permission_registry import PERMISSIONS

        def migrate_permissions(*args, **kwargs):
            PERMISSIONS.create_db_permissions()
        post_migrate.connect(migrate_permissions, sender=self, weak=False)
        self.register_tasks()
        try:
            set_default_admin = import_string(settings.SET_DEFAULT_ADMIN_BACKEND)
            post_migrate.connect(set_default_admin, sender=self)
        except ImportError as e:
            raise e

        if settings.EXECUTE_DATA_CHEKS:
            try:
                set_group_plates = import_string(settings.SET_GROUP_PLATES_BACKEND)
                set_ambit_coordinators = import_string(settings.SET_AMBIT_COORDINATORS_BACKEND)
            except ImportError as e:
                raise e

            post_migrate.connect(set_group_plates, sender=self)
            post_migrate.connect(set_ambit_coordinators, sender=self)

    @staticmethod
    def register_tasks():
        from . import tasks
        return tasks
