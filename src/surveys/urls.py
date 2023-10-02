from django.urls import path

from surveys import views

urlpatterns = [
    path("surveys/<slug:survey>/<slug:record_id>", views.SurveyQuestionsView.as_view(), name="survey_questions"),
    path("surveys/<slug:survey>/<slug:record_id>/answer", views.AnswerSurveyView.as_view(), name="survey_questions"),
]
