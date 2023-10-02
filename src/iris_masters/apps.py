from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate


class IrisMastersConfig(AppConfig):
    name = "iris_masters"

    def ready(self):
        from iris_masters.permissions import register_permissions
        register_permissions()
        self.register_tasks()
        if settings.EXECUTE_DATA_CHEKS:
            from iris_masters.data_checks.states import check_record_states
            from iris_masters.data_checks.process import check_processes
            from iris_masters.data_checks.response_channels import check_response_channels
            from iris_masters.data_checks.reasons import check_reasons
            from iris_masters.data_checks.districts import check_districts
            from iris_masters.data_checks.applicant_types import check_applicant_types
            from iris_masters.data_checks.applications import check_required_applications
            from iris_masters.data_checks.support import check_required_support
            from iris_masters.data_checks.admin_permission import check_admin_profile
            from iris_masters.data_checks.input_channels import check_input_channels
            from iris_masters.data_checks.parameters import check_parameters
            from iris_masters.data_checks.resolution_types import check_resolution_types
            from iris_masters.data_checks.reset_sequences import reset_sequences
            from iris_masters.data_checks.record_types import check_required_record_types
            post_migrate.connect(check_record_states, sender=self)
            post_migrate.connect(check_processes, sender=self)
            post_migrate.connect(check_response_channels, sender=self)
            post_migrate.connect(check_reasons, sender=self)
            post_migrate.connect(check_districts, sender=self)
            post_migrate.connect(check_required_applications, sender=self)
            post_migrate.connect(check_admin_profile, sender=self)
            post_migrate.connect(check_input_channels, sender=self)
            post_migrate.connect(check_applicant_types, sender=self)
            post_migrate.connect(check_required_support, sender=self)
            post_migrate.connect(check_parameters, sender=self)
            post_migrate.connect(check_resolution_types, sender=self)
            post_migrate.connect(reset_sequences, sender=self)
            post_migrate.connect(check_required_record_types, sender=self)

    @staticmethod
    def register_tasks():
        from . import tasks
        return tasks
