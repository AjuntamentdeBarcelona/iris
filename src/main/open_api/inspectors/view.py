from django.conf import settings

from drf_yasg import openapi
from drf_yasg.inspectors import DjangoRestResponsePagination, CoreAPICompatInspector
from drf_yasg.inspectors import SwaggerAutoSchema
from drf_yasg.utils import is_list_view
from rest_framework import status
from rest_framework.pagination import PageNumberPagination


class ExtendedDjangoRestResponsePagination(DjangoRestResponsePagination):
    def get_paginated_response(self, paginator, response_schema):
        paged_schema = super().get_paginated_response(paginator, response_schema)
        paged_schema.properties['previous']['x-nullable'] = 'true'
        paged_schema.properties['next']['x-nullable'] = 'true'
        return paged_schema

    def get_paginator_parameters(self, paginator):
        if isinstance(paginator, PageNumberPagination):
            return [
                openapi.Parameter(
                    name=paginator.page_size_query_param or 'page_size',
                    in_=openapi.IN_QUERY,
                    type=openapi.TYPE_INTEGER,
                    required=False,
                    description='Indicates the number of items per page (default: {}, max: {})'.format(
                        paginator.page_size, paginator.max_page_size),
                ),
                openapi.Parameter(
                    name=paginator.page_query_param,
                    in_=openapi.IN_QUERY,
                    type=openapi.TYPE_INTEGER,
                    required=False,
                    description='Requested page (default: 1)'.format(
                        paginator.page_size, paginator.max_page_size),
                ),
            ]
        return []


class ExtendedSwaggerAutoSchema(SwaggerAutoSchema):
    """
    Custom SwaggerAutoSchema inspector for adding common functions for RestFramework.
    In addition, it adds the IMI roles in order to set security with custom OpenAPI extensions.
    """
    paginator_inspectors = [ExtendedDjangoRestResponsePagination, CoreAPICompatInspector]

    def get_operation(self, operation_keys):
        operation = super().get_operation(operation_keys)
        roles = self.get_imi_roles()
        if roles and 'public' not in roles:
            operation['x-imi-roles'] = roles
        return operation

    def add_manual_parameters(self, parameters):
        parameters = super().add_manual_parameters(parameters)
        parameters.append(openapi.Parameter(
            name='Accept-Language',
            in_=openapi.IN_HEADER,
            description='Request language',
            type=openapi.TYPE_STRING,
            enum=[lang_code for lang_code, name in settings.LANGUAGES]
        ))
        return parameters

    def get_imi_roles(self):
        fn = getattr(self.view, self.method.lower(), None)
        roles = None
        if fn:
            roles = getattr(fn, '_imi_roles', {})
        return roles if roles else self.get_default_role()

    def get_default_role(self):
        return getattr(settings, 'OPEN_API', {}).get('DEFAULT_IMI_ROLE')

    def get_default_responses(self):
        responses = super().get_default_responses()
        if not is_list_view(self.path, self.method, self.view):
            responses[status.HTTP_404_NOT_FOUND] = self.get_404_response()
        if self.method in ['POST', 'PUT', 'PATCH']:
            responses[status.HTTP_400_BAD_REQUEST] = self.get_400_bad_request_response()
        return responses

    def get_404_response(self):
        return openapi.Response(
            description='Not found: resource not exists',
        )

    def get_400_bad_request_response(self):
        return openapi.Response(
            description='Bad request: Validation Error',
        )
