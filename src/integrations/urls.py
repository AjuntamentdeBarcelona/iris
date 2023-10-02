from django.urls import include, path
from integrations import views

urlpatterns = [
    path("gcod/", include(("integrations.services.gcod.urls", "gcod_urls"), namespace="integrations")),
    path("tasks/", include(("integrations.manual_task_schedule.urls", "manual_schedule"),
                           namespace="manual_scheduled")),
    path("task-types/", views.TaskTypeView.as_view(), name="task_types"),
    path("tasks/", views.LogResultView.as_view(), name="log_result"),
    path("batch-files/", views.BatchFileListAPIView.as_view(), name="batch_result_list"),
    path("batch-files/<int:pk>/validate/", views.BatchFileValidateView.as_view(), name="batch_validate"),
    path("opendatareport/<int:year>/<int:month>/", views.OpenDataDateReportView.as_view(), name="open_data_report"),
    path("batches-complete/", views.BatchReportsCompleteView.as_view(), name="batch_view"),
    path("eliminate_opendata/", views.EliminateOpendataView.as_view(), name="eliminate_opendata"),
    path("batch_change/", views.BatchFileChangeView.as_view(), name="batch_change"),
]
