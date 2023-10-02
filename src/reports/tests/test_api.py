from datetime import timedelta, datetime

import pytest
from django.utils import timezone
from mock import Mock, patch
from model_mommy import mommy
from rest_framework import status
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN

from iris_masters.models import RecordType
from main.open_api.tests.base import PostOperationMixin, BaseOpenAPITest
from profiles.models import Group, UserGroup, AccessLog
from record_cards.permissions import RESP_WORKED
from record_cards.tests.utils import CreateRecordCardMixin
from reports.permissions import REPS_OPERATIONS, REPS_MANAGEMENT, REPS_AUDIT, REPS_USERS
from themes.models import ThemeGroup, ElementDetailThemeGroup, Area


@pytest.mark.django_db
class TestQuequicomReportView(PostOperationMixin, CreateRecordCardMixin, BaseOpenAPITest):
    base_api_path = "/services/iris/api"
    path = "/reports/quequicom/"

    @pytest.mark.parametrize("add_dates,add_theme_group,who,how,wrong_pks,expected_response", (
            (True, True, True, False, False, HTTP_200_OK),
            (True, True, False, True, False, HTTP_200_OK),
            (False, True, True, False, False, HTTP_400_BAD_REQUEST),
            (True, False, True, False, False, HTTP_200_OK),
            (True, True, True, False, True, HTTP_400_BAD_REQUEST),
    ))
    def test_quequicom_report_view(self, add_dates, add_theme_group, who, how, wrong_pks, expected_response):
        element_detail = self.create_element_detail()
        theme_group = mommy.make(ThemeGroup, user_id="2222")
        ElementDetailThemeGroup.objects.create(element_detail=element_detail, theme_group=theme_group)
        record_card = self.create_record_card(element_detail=element_detail)
        self.set_group_permissions("222222", record_card.responsible_profile, [RESP_WORKED, REPS_OPERATIONS])

        data = {"who": who, "how": how}
        if add_dates:
            data.update({
                "create_date_gte": timezone.now().date(),
                "create_date_lte": (timezone.now() + timedelta(days=5)).date(),
                "close_date_gte": timezone.now().date(),
                "close_date_lte": (timezone.now() + timedelta(days=5)).date(),
            })
        if add_theme_group:
            data["theme_group_ids"] = [theme_group.pk]
        if wrong_pks:
            data["area_id"] = 10
            data["record_type_id"] = 10
        else:
            data["area_id"] = mommy.make(Area, user_id="222222").pk
            data["record_type_id"] = mommy.make(RecordType, user_id="222222").pk

        response = self.post(force_params=data)
        assert response.status_code == expected_response

    @pytest.mark.parametrize("has_permissions,expected_response", (
        (True, HTTP_200_OK),
        (False, HTTP_403_FORBIDDEN),
    ))
    def test_permissions(self, has_permissions, expected_response):
        element_detail = self.create_element_detail()
        theme_group = mommy.make(ThemeGroup, user_id="2222")
        ElementDetailThemeGroup.objects.create(element_detail=element_detail, theme_group=theme_group)
        record_card = self.create_record_card(element_detail=element_detail)

        if has_permissions:
            self.set_group_permissions("22222", record_card.responsible_profile, [REPS_OPERATIONS])
        data = {
            "who": True,
            "how": True,
            "create_date_gte": timezone.now().date(),
            "create_date_lte": (timezone.now() + timedelta(days=5)).date(),
            "close_date_gte": timezone.now().date(),
            "close_date_lte": (timezone.now() + timedelta(days=5)).date(),
            "theme_group_ids": [theme_group.pk]
        }
        response = self.post(force_params=data)
        assert response.status_code == expected_response


@pytest.mark.django_db
class TestEntriesReportView(PostOperationMixin, CreateRecordCardMixin, BaseOpenAPITest):
    base_api_path = "/services/iris/api"
    path = "/reports/entries/"
    permission = REPS_AUDIT

    @pytest.mark.parametrize("wrong_dates,wrong_pks,expected_response", (
            (False, False, HTTP_200_OK),
            (False, True, HTTP_400_BAD_REQUEST),
            (True, False, HTTP_400_BAD_REQUEST),
    ))
    def test_report_view(self, wrong_dates, wrong_pks, expected_response):
        record_card = self.create_record()
        if self.permission:
            self.set_group_permissions("22222", record_card.responsible_profile, [self.permission])

        data = {
            "create_date_gte": timezone.now().date(),
            "create_date_lte": (timezone.now() + timedelta(days=5)).date(),
            "close_date_gte": timezone.now().date(),
            "close_date_lte": (timezone.now() + timedelta(days=5)).date(),
        }
        if wrong_dates:
            self.set_wrong_dates(data)

        if wrong_pks:
            data["area_id"] = 10
            data["record_type_id"] = 10
        else:
            data["area_id"] = record_card.element_detail.element.area_id
            data["record_type_id"] = record_card.record_type_id

        response = self.post(force_params=data)
        assert response.status_code == expected_response

    def create_record(self):
        return self.create_record_card()

    @staticmethod
    def set_wrong_dates(data):
        data.pop("create_date_lte")
        data.pop("close_date_gte")

    @pytest.mark.parametrize("has_permissions,expected_response", (
        (True, HTTP_200_OK),
        (False, HTTP_403_FORBIDDEN),
    ))
    def test_permissions(self, has_permissions, expected_response):
        record_card = self.create_record()
        if has_permissions:
            self.set_group_permissions("22222", record_card.responsible_profile, [self.permission])

        data = {
            "create_date_gte": timezone.now().date(),
            "create_date_lte": (timezone.now() + timedelta(days=5)).date(),
            "close_date_gte": timezone.now().date(),
            "close_date_lte": (timezone.now() + timedelta(days=5)).date(),
        }
        response = self.post(force_params=data)
        assert response.status_code == expected_response


@pytest.mark.django_db
class TestClosedRecordsReportView(TestEntriesReportView):
    base_api_path = "/services/iris/api"
    path = "/reports/closed/"
    permission = REPS_AUDIT

    def create_record(self):
        return self.create_record_card(closing_date=timezone.now())


@pytest.mark.django_db
class TestThemesRankingReportView(TestEntriesReportView):
    base_api_path = "/services/iris/api"
    path = "/reports/themes_ranking/"
    permission = REPS_MANAGEMENT

    def create_record(self):
        return self.create_record_card(closing_date=timezone.now())

    @staticmethod
    def set_wrong_dates(data):
        data["close_date_lte"] = (timezone.now() + timedelta(days=800)).date()


@pytest.mark.django_db
class TestApplicantsRecordCountReportView(TestEntriesReportView):
    base_api_path = "/services/iris/api"
    path = "/reports/applicants_records/"
    permission = REPS_MANAGEMENT


@pytest.mark.django_db
class TestRecordStateGroupsReportView(TestEntriesReportView):
    base_api_path = "/services/iris/api"
    path = "/reports/recordstate-groups/"
    permission = REPS_MANAGEMENT


@pytest.mark.django_db
class TestOperatorsReportView(TestEntriesReportView):
    base_api_path = "/services/iris/api"
    path = "/reports/operators/"
    permission = REPS_USERS

    @pytest.mark.parametrize("wrong_dates,wrong_pks,expected_response", (
            (False, False, HTTP_200_OK),
            (False, True, HTTP_400_BAD_REQUEST),
            (True, False, HTTP_400_BAD_REQUEST),
    ))
    def test_report_view(self, wrong_dates, wrong_pks, expected_response):
        record_card = self.create_record()
        self.set_group_permissions("user_id", record_card.responsible_profile, [self.permission])

        data = {
            "create_date_gte": timezone.now().date(),
            "create_date_lte": (timezone.now() + timedelta(days=5)).date(),
            "close_date_gte": timezone.now().date(),
            "close_date_lte": (timezone.now() + timedelta(days=5)).date(),
        }
        if wrong_dates:
            self.set_wrong_dates(data)

        if wrong_pks:
            data["area_id"] = 10
            data["record_type_id"] = 10
        else:
            data["area_id"] = record_card.element_detail.element.area_id
            data["record_type_id"] = record_card.record_type_id

        group_registers_by_user = Mock(return_value={})
        with patch("reports.views.OperatorsReportView.group_registers_by_user", group_registers_by_user):
            response = self.post(force_params=data)
            assert response.status_code == expected_response

    @pytest.mark.parametrize("has_permissions,expected_response", (
        (True, HTTP_200_OK),
        (False, HTTP_403_FORBIDDEN),
    ))
    def test_permissions(self, has_permissions, expected_response):
        record_card = self.create_record()
        if has_permissions:
            self.set_group_permissions("22222", record_card.responsible_profile, [self.permission])

        data = {
            "create_date_gte": timezone.now().date(),
            "create_date_lte": (timezone.now() + timedelta(days=5)).date(),
            "close_date_gte": timezone.now().date(),
            "close_date_lte": (timezone.now() + timedelta(days=5)).date(),
        }
        group_registers_by_user = Mock(return_value={})
        with patch("reports.views.OperatorsReportView.group_registers_by_user", group_registers_by_user):
            response = self.post(force_params=data)
            assert response.status_code == expected_response


@pytest.mark.django_db
class TestAccessLogReport(PostOperationMixin, BaseOpenAPITest):
    base_api_path = "/services/iris/api"

    def test_access_log(self):
        group_a = mommy.make(Group, user_id="a", profile_ctrl_user_id="a")
        group_b = mommy.make(Group, user_id="a", profile_ctrl_user_id="b")
        user_a = mommy.make(UserGroup, group=group_a, user__username="a")
        user_b = mommy.make(UserGroup, group=group_a, user__username="b")
        AccessLog.objects.create(user_group=user_a, group=group_a)
        AccessLog.objects.create(user_group=user_a, group=group_b)
        AccessLog.objects.create(user_group=user_b, group=group_a)
        response = self.post(force_params={
            "from_date": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
            "to_date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
        })
        assert len(response.data) == 3

    path = "/reports/access-log/"

    @pytest.mark.parametrize("params,", (
        {},
        {"from_date": ""},
        {"from_date": "2019-10-22"},
        {"from_date": "2019-22-10"},
        {"to_date": ""},
        {"to_date": "2019-22-10"},
        {"to_date": "2019-22-10"},
    ))
    def test_bad_params(self, params):
        print(params)
        response = self.post(force_params=params)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
