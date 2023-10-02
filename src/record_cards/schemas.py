from drf_yasg.utils import swagger_auto_schema
from rest_framework.status import (HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND,
                                   HTTP_409_CONFLICT)


def post_record_card_schema_factory(action="", request_body_serializer=None, responses=None, add_forbidden=True):
    if not responses:
        responses = {
            HTTP_204_NO_CONTENT: "RecordCard {}".format(action),
            HTTP_404_NOT_FOUND: "RecordCard is not available to {}".format(action),
            HTTP_409_CONFLICT: "RecordCard is blocked",
        }
        if request_body_serializer:
            responses[HTTP_400_BAD_REQUEST] = "Bad request: Validation Error"
        if add_forbidden:
            responses[HTTP_403_FORBIDDEN] = "Acces not allowed"
    return swagger_auto_schema(request_body=request_body_serializer, responses=responses)
