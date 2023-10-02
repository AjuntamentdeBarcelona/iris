from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.status import HTTP_200_OK, HTTP_403_FORBIDDEN, HTTP_400_BAD_REQUEST

from iris_masters.views import BasicMasterAdminPermissionsMixin, BasicMasterViewSet
from main.api.schemas import (create_swagger_auto_schema_factory, update_swagger_auto_schema_factory,
                              destroy_swagger_auto_schema_factory)
from record_cards.base_views import CustomChunkedUploadView
from support_info.filters import SupportInfoFilter
from support_info.models import SupportInfo, SupportChunkedFile
from support_info.serializers import SupportInfoSerializer, SupportChunkedFileSerializer
from themes.views import BasicOrderingFieldsSearchMixin
from .permissions import SUPPORT_ADMIN


class SupportPermissionMixin(BasicMasterAdminPermissionsMixin):
    permission_codename = SUPPORT_ADMIN


@method_decorator(name="create", decorator=create_swagger_auto_schema_factory(SupportInfoSerializer))
@method_decorator(name="update", decorator=update_swagger_auto_schema_factory(SupportInfoSerializer))
@method_decorator(name="partial_update", decorator=update_swagger_auto_schema_factory(SupportInfoSerializer))
@method_decorator(name="destroy", decorator=destroy_swagger_auto_schema_factory())
class SupportInfoViewSet(SupportPermissionMixin, BasicOrderingFieldsSearchMixin, BasicMasterViewSet):
    """
    Viewset to manage Support Info (CRUD).
    Administration permission  needed to create, update and destroy.
    The list endpoint:
     - can be ordered by the type, title and created_at
     - can be filterd by type and title
     - support unaccent search by the title and description
    """
    queryset = SupportInfo.objects.all()
    serializer_class = SupportInfoSerializer
    filterset_class = SupportInfoFilter
    search_fields = ["#title", "#description"]
    ordering_fields = ["type", "title", "created_at", "category", "description"]

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        # Avoid to build full uris
        ctx.pop('request')
        return ctx


@method_decorator(name="post", decorator=swagger_auto_schema(responses={HTTP_200_OK: "File uploaded"}))
@method_decorator(name="put", decorator=swagger_auto_schema(request_body=SupportChunkedFileSerializer, responses={
    HTTP_200_OK: SupportChunkedFileSerializer,
    HTTP_400_BAD_REQUEST: "Bad Request",
    HTTP_403_FORBIDDEN: "Acces Not Allowed"
}))
class UploadChunkedSupportInfoFileView(SupportPermissionMixin, CustomChunkedUploadView):
    """
    API endpoint to upload chunked file related to a SupportInfo of documentation type. The chunks of the file
    must be codifiend un base64. Administration permission  needed to create, update and destroy.
    Upload a file consist on three steps:
    - PUT with the first chunk of the file to: /api/support_files/upload/
    - N PUTs with the next chunks of the file to: support_files/upload/chunk/<str:pk>/ where pk is the chunk file id
    - a POST to support_files/upload/chunk/<str:pk>/ with md5 checksum of file -> {"md5": "string"}

    Put's response will include the url to the next operation

    Validation issues:
    - file must be related to a SupportInfo of documentation type.
    """
    model = SupportChunkedFile
    serializer_class = SupportChunkedFileSerializer
    http_method_names = ("post", "put")
    parser_classes = (MultiPartParser,)
    permission_classes = (IsAuthenticated,)

    def on_completion(self, chunked_upload, request):
        file = default_storage.open(chunked_upload.file.name)
        content_file = ContentFile(file.read(), name=chunked_upload.filename)

        support_info = SupportInfo.objects.get(pk=chunked_upload.support_info_id)
        support_info.file = content_file
        support_info.save()
