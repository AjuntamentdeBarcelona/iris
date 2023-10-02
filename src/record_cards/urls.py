from django.urls import path
from rest_framework.routers import DefaultRouter
from django.conf import settings

from record_cards import views

record_cards_router = DefaultRouter()

record_cards_router.register(r"citizens", views.CitizenViewSet)
record_cards_router.register(r"social_entities", views.SocialEntityViewSet)
record_cards_router.register(r"applicants", views.ApplicantViewSet)
record_cards_router.register(r"internal-operators", views.InternalOperatorViewSet)
record_cards_router.register(r"requests", views.RequestViewSet)
record_cards_router.register(r"record_cards", views.RecordCardViewSet)

if settings.TWITTER_ENABLED:
    record_cards_router.register(r"record_cards/sources/twitter", views.TwitterRecordCardViewSet)

urlpatterns = [
    path("ubications/", views.UbicationListView.as_view(), name="ubications_list"),
    path("applicants/search/", views.ApplicantSearch.as_view(), name="applicants_search"),
    path("applicant_response/<int:applicant_id>/", views.ApplicantResponseRetrieveView.as_view(),
         name="applicant_response_retrieve"),
    path("remove-applicant-zero/", views.RemoveApplicantZero.as_view(), name="remove_applicant_zero"),

    path("state-machine/map/", views.RecordStateMapView.as_view(), name="state_machine_map"),
    path(r"record_cards/sources/survey/", views.SurveyViewSet.as_view(actions={'post': 'create'}),
         name="record_survey_create"),
    path("record_cards/retrieve/<int:pk>/", views.RecordCardPkRetrieveView.as_view(), name="record_card_pk_retrieve"),
    path("record_cards/summary/", views.RecordCardGroupManagementIndicatorsView.as_view(), name="record_card_summary"),
    path("record_cards/summary/ambit/<int:group_id>/", views.RecordCardAmbitManagementIndicatorsView.as_view(),
         name="record_card_ambit_summary"),
    path("record_cards/month-summary/<int:year>/<int:month>/", views.RecordCardGroupMonthIndicatorsView.as_view(),
         name="record_card_month_indicators"),
    path("record_cards/month-summary/ambit/<int:year>/<int:month>/", views.RecordCardAmbitMonthIndicatorsView.as_view(),
         name="record_card_month_indicators"),
    path("record_cards/calculate-month-indicators/<int:year>/<int:month>/",
         views.CalculateMonthIndicatorsView.as_view(), name="calculate_month_indicatos"),
    path("record_cards/my-tasks/", views.RecordCardMyTasksListView.as_view(), name="record_card_my_tasks"),
    path("record_cards/pending-validation/", views.RecordCardPendingValidationListView.as_view(),
         name="record_card_pending_validation"),
    path("record_cards/add-comment/", views.CommentCreateView.as_view(), name="record_card_add_comment"),
    path("record_cards/possible-similars-task/", views.RecordCardPossibleSimilarTaskView.as_view(),
         name="record_card_possible_similars_task"),
    path("record_cards/download-link/<int:pk>/", views.GetDownloadMinioUrlView.as_view(),
         name="record_cards_download_link"),

    # Photos endpoints
    path("record_files/upload/", views.UploadChunkedRecordFileView.as_view(), name="record_card_file_upload"),
    path("record_files/upload/chunk/<str:pk>/", views.UploadChunkedRecordFileView.as_view(),
         name="record_card_file_upload_chunk"),
    path("record_files/<int:pk>/delete/", views.DeleteRecordFileView.as_view(), name="record_card_file_delete"),

    path("record_cards/<str:normalized_record_id>/update/check/", views.RecordCardUpdateCheckView.as_view(),
         name="record_card_update_check"),
    path("record_cards/<int:pk>/toogle-urgency/", views.ToogleRecordCardUrgencyView.as_view(),
         name="record_card_toogle_urgency"),
    path("record_cards/<int:pk>/block/", views.RecordCardBlockView.as_view(), name="record_card_toogle_block"),
    path("record_cards/<int:pk>/validate/", views.RecordCardValidateView.as_view(), name="record_card_validate"),
    path("record_cards/<int:pk>/validate/check/", views.RecordCardValidateView.as_view(is_check=True),
         name="record_card_validate_check"),
    path("record_cards/<int:pk>/will-be-solved/", views.RecordCardWillBeSolvedView.as_view(),
         name="record_card_will_solve"),
    path("record_cards/<int:pk>/cancel/", views.RecordCardCancelView.as_view(), name="record_card_cancel"),
    path("record_cards/<int:pk>/close/", views.RecordCardCloseView.as_view(), name="record_card_close"),
    path("record_cards/<int:pk>/external-processing/", views.RecordCardExternalProcessingView.as_view(),
         name="record_card_external_processing"),
    path("record_cards/<int:pk>/external-processing-email/", views.RecordCardExternalProcessingEmailView.as_view(),
         name="record_card_external_processing_email"),
    path("record_cards/<int:pk>/draft-answer/", views.RecordCardDraftAnswerView.as_view(),
         name="record_card_draft_answer"),
    path("record_cards/<int:pk>/answer/", views.RecordCardAnswerView.as_view(), name="record_card_answer"),
    path("record_cards/<int:pk>/answer/response/", views.RecordCardAnswerResponseView.as_view(),
         name="record_card_answer_response"),
    path("record_cards/<int:pk>/traceability/", views.RecordCardTraceabilityView.as_view(),
         name="record_card_traceability"),
    path("record_cards/<int:pk>/reasignations/", views.RecordCardReasignationOptionsView.as_view(),
         name="record_card_reasignations"),
    path("record_cards/<int:pk>/toggle-reassignable/", views.ToogleRecordCardReasignableView.as_view(),
         name="record_card_toggle_reassignable"),
    path("record_cards/reasign/", views.RecordCardReasignationView.as_view(), name="record_card_reasign"),
    path("record_cards/<int:id>/multi_complaints/", views.RecordCardMultiRecordsView.as_view(),
         name="record_card_multicomplaints"),
    path("record_cards/<int:pk>/claim/", views.RecordCardClaimView.as_view(), name="record_card_claim"),
    path("record_cards/<int:pk>/claim/check/", views.RecordCardClaimView.as_view(is_check=True),
         name="record_card_claim_check"),
    path("record_cards/<int:pk>/theme-change/", views.RecordCardThemeChangeView.as_view(),
         name="record_card_theme_change"),
    path("record_cards/<int:pk>/theme-change/check/", views.RecordCardThemeChangeView.as_view(is_check=True),
         name="record_card_theme_change_check"),
    path("record_cards/<int:pk>/answer-preview/", views.RecordCardAnswerPreview.as_view(),
         name="record_card_answer_preview"),
    path("record_cards/<int:pk>/resend-answer/", views.RecordCardResendAnswerView.as_view(),
         name="record_card_resend_answer"),

    path("workflows/", views.WorkflowList.as_view(), name="workflows"),
    path("workflows/<int:pk>/", views.WorkflowFields.as_view(), name="workflow_fields"),
    path("workflows/<int:pk>/plan/", views.WorkflowPlanView.as_view(), name="workflow_plan"),
    path("workflows/<int:pk>/plan/check/", views.WorkflowPlanView.as_view(is_check=True), name="workflow_plan_check"),
    path("workflows/<int:pk>/resolute/", views.WorkflowResoluteView.as_view(), name="workflow_resolute"),
    path(
        "workflows/<int:pk>/resolute/draft/", views.WorkflowResoluteDraftView.as_view(), name="workflow_resolute_draft"
    ),
    path("workflows/<int:pk>/resolute/check/", views.WorkflowResoluteView.as_view(is_check=True),
         name="workflow_resolute_check"),
    path('workflow/<int:pk>/answer/', views.WorkflowAnswerView.as_view(), name='workflow_answer'),

    path("applicant-last-records/<int:id>/", views.ApplicantLastRecordsListView.as_view(),
         name="applicant_last_records"),
    path("default-applicant/", views.DefaultApplicantView.as_view(), name="applicant_default"),

    path("set-record-audits/", views.SetRecordCardAuditsView.as_view(), name="set_record_card_audits"),
]

urlpatterns += record_cards_router.urls
