from django.urls import path
from rest_framework.routers import DefaultRouter

from iris_masters import views

iris_masters_router = DefaultRouter()

iris_masters_router.register(r"media_types", views.MediaTypeViewSet)
iris_masters_router.register(r"communication_medias", views.CommunicationMediaViewSet)
iris_masters_router.register(r"cancel-reasons", views.CancelReasonViewSet)
iris_masters_router.register(r"reasign-reasons", views.ReassignationReasonViewSet)
iris_masters_router.register(r"announcements", views.AnnouncementViewSet)
iris_masters_router.register(r"supports", views.SupportViewSet)
iris_masters_router.register(r"input_channels", views.InputChannelViewSet)
iris_masters_router.register(r"resolution-types", views.ResolutionTypeViewSet)
iris_masters_router.register(r"applicant_types", views.ApplicantTypeViewSet)
iris_masters_router.register(r"record_types", views.RecordTypeListRetrieveUpdateViewSet)
iris_masters_router.register(r"districts", views.DistrictViewSet)

urlpatterns = [
    path("reasons/", views.ReasonListView.as_view(), name="all_reasons"),
    path("response_channels/", views.ResponseChannelView.as_view(), name="response_channels_list"),
    path("record_states/", views.RecordStateView.as_view(), name="record_states_list"),
    path("parameters/",  views.ParameterListView.as_view(), name="parameters_list"),
    path("parameters/visible/",  views.ParameterVisibleListView.as_view(), name="parameters_visible_list"),
    path("parameters/update/", views.ParameterUpdateListView.as_view(), name="parameters_udpate_list"),
    path("applications/", views.ApplicationView.as_view(), name="applications_list"),
    path("process/", views.ProcessListView.as_view(), name="process_list"),
    path("external-service/", views.ExternalServiceListView.as_view(), name="externa_service_list"),
    path("letter-templates/", views.LetterTemplateListView.as_view(), name="letter_template_list"),
    path("announcements/<int:id>/mark-as-seen/", views.AnnouncementSeenView.as_view(), name="announcements_mark_seen"),
    path("masters-data-checks/", views.MastersDataChecksView.as_view(), name="masters_data_checks"),
]
urlpatterns += iris_masters_router.urls
