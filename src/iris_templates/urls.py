from django.urls import path
from rest_framework.routers import DefaultRouter

from iris_templates.views import (IrisTemplateViewset, ResponseTypeViewSet, RecordTypeTemplatesListView,
                                  VariablesListView, RecordCardTemplatesListView, ApplicantCommunicationTemplate,
                                  SaveForRecordView, RecordVariableView)

iris_templates_router = DefaultRouter()


iris_templates_router.register(r'templates', IrisTemplateViewset)
iris_templates_router.register(r'response_types', ResponseTypeViewSet)

urlpatterns = [
    path('record_type/<int:id>/templates/', RecordTypeTemplatesListView.as_view(),
         name='record_types_templates'),
    path('record-card/<int:record_id>/communications/', ApplicantCommunicationTemplate.as_view(),
         name='record_card_cim'),
    path('record-card/<int:record_id>/', RecordCardTemplatesListView.as_view(),
         name='record_card_templates'),
    path('variables/', VariablesListView.as_view(), name='templates_variables'),
    path('variables/<slug:record_id>/', RecordVariableView.as_view(), name='templates_variables'),
    path('group/save-for-record/<int:record_id>/', SaveForRecordView.as_view(), name='templates_manage'),
    path('group/update-for-record/<int:record_id>/<int:pk>/', SaveForRecordView.as_view(), name='templates_update'),
]

urlpatterns += iris_templates_router.urls
