from rest_framework import authentication
from rest_framework import permissions

from drf_yasg.views import get_schema_view
from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg import openapi


class FixedPathPrefixGenerator(OpenAPISchemaGenerator):

    def get_schema(self, request=None, public=False):
        schema = super().get_schema(request, public)
        schema.base_path = '/services/iris/api'
        return schema


schema_view = get_schema_view(
    openapi.Info(
        title="IRIS2 API",
        default_version='1.110.6',
        description="IRIS2 is a complete tool for managing communications between citizens and institutions. "
                    "It's the main citizen support software for the Ajuntament de Barcelona.",
        terms_of_service="-",
        contact=openapi.Contact(email="contact@snippets.local"),
        license=openapi.License(name="BSD License"),
    ),
    validators=['ssv'],
    urlconf='main.urls_iris_api',
    public=True,

    generator_class=FixedPathPrefixGenerator,
    permission_classes=(permissions.AllowAny,),
    authentication_classes=(authentication.TokenAuthentication,)
)

