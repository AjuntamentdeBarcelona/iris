from django.urls import path

from public_external_processing.views import (RecordCardExternalReturnedView, RecordCardExternalCancelView,
                                              RecordCardExternalCloseView)

urlpatterns = [
    path("return/<int:pk>/", RecordCardExternalReturnedView.as_view(), name="public_external_return"),
    path("cancel/<int:pk>/", RecordCardExternalCancelView.as_view(), name="public_external_cancel"),
    path("close/<int:pk>/", RecordCardExternalCloseView.as_view(), name="public_external_close"),
]
