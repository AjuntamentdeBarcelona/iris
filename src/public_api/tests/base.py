import pytest

from main.open_api.tests.base import BaseOpenAPITest
from main.urls import PUBLIC_API_URL_NAME


@pytest.mark.django_db
class BasePublicAPITest(BaseOpenAPITest):
    """
    BaseClass for creating RestFramework view tests that take advantage of the OpenAPI specification. The main goals
    of this class are:
     - Check if an API call is conformant to the OpenAPI schema defined.
     - Give abstractions for creating integration and functional API tests.
     - Generate deterministic test cases easily.

    This class can be extended for more common and concrete use cases.
    """
    path = None
    open_api_format = '.json'
    open_api_url_name = PUBLIC_API_URL_NAME
    base_api_path = '/services/iris/api-public'
