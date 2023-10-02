from django.urls import path
from rest_framework.routers import DefaultRouter

from support_info.views import SupportInfoViewSet, UploadChunkedSupportInfoFileView

support_info_router = DefaultRouter()

urlpatterns = [
    path("support_files/upload/", UploadChunkedSupportInfoFileView.as_view(), name="support_info_file_upload"),
    path("support_files/upload/chunk/<str:pk>/", UploadChunkedSupportInfoFileView.as_view(),
         name="support_info_file_upload_chunk"),
]
support_info_router.register(r"", SupportInfoViewSet, "infos")

urlpatterns += support_info_router.urls
