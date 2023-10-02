from rest_framework import authentication
from rest_framework import permissions

from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg.views import get_schema_view

from public_api import authenticated_urls as authenticated_public_urls


class FixedPathPrefixGenerator(OpenAPISchemaGenerator):

    def get_schema(self, request=None, public=False):
        schema = super().get_schema(request, public)
        schema.base_path = '/services/iris/api-internet'
        return schema


public_auth_schema_view = get_schema_view(
    openapi.Info(
        title="IRIS2 Public Authenticated API",
        default_version='1.5.0',
        description="IRIS2 is a complete tool for managing communications between citizens and institutions. "
                    "It's the main citizen support software for the Ajuntament de Barcelona."
                    "This is the public (accesible outside the corporate network) part of its API.",
        terms_of_service="-",
        contact=openapi.Contact(email="fmunoz@apsl.net"),
        license=openapi.License(name="BSD License"),
    ),
    urlconf=authenticated_public_urls,
    validators=['ssv'],
    public=True,
    generator_class=FixedPathPrefixGenerator,
    permission_classes=(permissions.AllowAny,),
    authentication_classes=(authentication.TokenAuthentication,)
)
