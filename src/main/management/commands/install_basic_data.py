from django.core.management.base import BaseCommand

from integrations.data_checks.integrations_parameters import check_integrations_parameters
from iris_masters.data_checks.admin_permission import check_admin_profile
from iris_masters.data_checks.applicant_types import check_applicant_types
from iris_masters.data_checks.applications import check_required_applications
from iris_masters.data_checks.districts import check_districts
from iris_masters.data_checks.input_channels import check_input_channels
from iris_masters.data_checks.parameters import check_parameters
from iris_masters.data_checks.process import check_processes
from iris_masters.data_checks.reasons import check_reasons
from iris_masters.data_checks.record_types import check_required_record_types
from iris_masters.data_checks.reset_sequences import reset_sequences
from iris_masters.data_checks.resolution_types import check_resolution_types
from iris_masters.data_checks.response_channels import check_response_channels
from iris_masters.data_checks.states import check_record_states
from iris_masters.data_checks.support import check_required_support
from iris_templates.data_checks.visible_parameters import check_template_parameters
from profiles.data_checks.default_admin import create_basic_group_struct
from profiles.tasks import set_default_admin, set_group_plates, set_ambit_coordinators
from record_cards.data_checks.default_applicant import create_default_applicant
from themes.data_checks.survey import check_survey


class Command(BaseCommand):
    """
    Command to create an initial dataset for IRIS.
    """
    help = "Installs a minimal set of data for start using IRIS."

    def handle(self, *args, **options):
        check_required_record_types(sender=None)
        set_default_admin(sender=None)
        set_ambit_coordinators(sender=None)
        set_group_plates(sender=None)
        create_default_applicant(sender=None)

        check_record_states(sender=None)
        check_processes(sender=None)
        check_response_channels(sender=None)
        check_reasons(sender=None)
        check_districts(sender=None)
        check_required_applications(sender=None)
        check_admin_profile(sender=None)
        check_input_channels(sender=None)
        check_applicant_types(sender=None)
        check_required_support(sender=None)
        check_parameters(sender=None)
        create_basic_group_struct()
        check_resolution_types(sender=None)
        reset_sequences(sender=None)
        check_template_parameters(sender=None)
        check_integrations_parameters(sender=None)
        check_survey(sender=None)
