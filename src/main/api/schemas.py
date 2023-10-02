from drf_yasg.utils import swagger_auto_schema
from rest_framework.status import (HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST,
                                   HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND)


def create_swagger_auto_schema_factory(request_body_serializer, responses=None, add_forbidden=True):
    if not responses:
        responses = {
            HTTP_201_CREATED: request_body_serializer,
            HTTP_400_BAD_REQUEST: "Bad request: Validation Error",
        }
        if add_forbidden:
            responses[HTTP_403_FORBIDDEN] = "Acces not allowed"
    return swagger_auto_schema(request_body=request_body_serializer, responses=responses)


def update_swagger_auto_schema_factory(request_body_serializer, responses=None, add_forbidden=True):
    if not responses:
        responses = {
            HTTP_200_OK: request_body_serializer,
            HTTP_400_BAD_REQUEST: "Bad request: Validation Error",
            HTTP_404_NOT_FOUND: "Not found: resource not exists",
        }
        if add_forbidden:
            responses[HTTP_403_FORBIDDEN] = "Acces not allowed"
    return swagger_auto_schema(request_body=request_body_serializer, responses=responses)


def destroy_swagger_auto_schema_factory(responses=None, add_forbidden=True):
    if not responses:
        responses = {
            HTTP_204_NO_CONTENT: "No Content",
            HTTP_404_NOT_FOUND: "Not found: resource not exists"
        }
        if add_forbidden:
            responses[HTTP_403_FORBIDDEN] = "Acces not allowed"
    return swagger_auto_schema(responses=responses)


def retrieve_swagger_auto_schema_factory(body_serializer, responses=None):
    if not responses:
        responses = {
            HTTP_200_OK: body_serializer,
            HTTP_404_NOT_FOUND: "Not found: resource not exists",
        }
    return swagger_auto_schema(responses=responses)


def list_swagger_auto_schema_factory(serializer, responses=None, add_forbidden=True):
    if not responses:
        responses = {
            HTTP_200_OK: serializer,
        }
        if add_forbidden:
            responses[HTTP_403_FORBIDDEN] = "Acces not allowed"
    return swagger_auto_schema(responses=responses)


def get_swagger_auto_schema_factory(responses=None, ok_message=None):
    if not responses:
        responses = {
            HTTP_200_OK: ok_message if ok_message else "OK"
        }

    return swagger_auto_schema(responses=responses)
