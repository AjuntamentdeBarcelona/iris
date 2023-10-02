from django.urls import path
from reports.views import (QuequicomReportView, EntriesReportView, ClosedRecordsReportView, ThemesRankingReportView,
                           ApplicantsRecordCountReportView, RecordStateGroupsReportView, OperatorsReportView)
from reports.views import AccessReportView

urlpatterns = [
    path("quequicom/", QuequicomReportView.as_view(), name="quequicom_report"),
    path("entries/", EntriesReportView.as_view(), name="entries_records_report"),
    path("closed/", ClosedRecordsReportView.as_view(), name="closed_records_report"),
    path("themes_ranking/", ThemesRankingReportView.as_view(), name="themes_ranking_report"),
    path("applicants_records/", ApplicantsRecordCountReportView.as_view(), name="applicants_records_report"),
    path("recordstate-groups/", RecordStateGroupsReportView.as_view(), name="recordstate_groups_report"),
    path("access-log/", AccessReportView.as_view(), name="access_report"),
    path("operators/", OperatorsReportView.as_view(), name="operators_report"),
]
