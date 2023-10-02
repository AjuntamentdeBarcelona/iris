from django.conf import settings

from main.celery import app as celery_app

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


@celery_app.task(queue=settings.CELERY_HIGH_QUEUE_NAME, max_retries=5)
def masters_data_checks():
    check_record_states(None)
    check_processes(None)
    check_response_channels(None)
    check_reasons(None)
    check_districts(None)
    check_applicant_types(None)
    check_required_applications(None)
    check_required_support(None)
    check_admin_profile(None)
    check_input_channels(None)
    check_parameters(None)
    check_resolution_types(None)
    reset_sequences(None)
