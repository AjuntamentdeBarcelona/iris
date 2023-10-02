from django.utils.deprecation import MiddlewareMixin

from iris_masters.models import Application
from main.urls import PUBLIC_API_BASE_PATH
from public_api.urls import SSI_RECORDS_URL


class ApplicationMiddelware(MiddlewareMixin):
    """
    Detects the origin application according to its hash. By default, it sets the ATE hash.
    """

    def process_request(self, request):
        application_hash = request.META.get('HTTP_APPLICATION_HASH')
        try:
            request.application = Application.objects.get(description_hash=application_hash)
        except Application.DoesNotExist:
            if PUBLIC_API_BASE_PATH in request.path or SSI_RECORDS_URL in request.path:
                request.application = Application.objects.get(description_hash=Application.WEB_HASH)
