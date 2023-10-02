from django.db.models import Prefetch, Q, Count, F, Value, Avg
from django.db.models.functions import Coalesce, Concat
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from drf_renderer_xlsx.mixins import XLSXFileMixin
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.renderers import JSONRenderer, BrowsableAPIRenderer
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN
from rest_framework.views import APIView

from excel_export.mixins import ColumnNamesMixin
from excel_export.renderers import CustomXLSXRenderer
from excel_export.styles import ExcelBaseStyles
from iris_masters.models import Parameter, RecordState, RecordType, Reason
from profiles.models import Group, AccessLog
from record_cards.mixins import PermissionActionMixin
from record_cards.models import (RecordCard, RecordCardFeatures, RecordCardSpecialFeatures, RecordCardTextResponse,
                                 Citizen, SocialEntity, RecordCardStateHistory, RecordCardReasignation)
from record_cards.schemas import post_record_card_schema_factory
from reports import permissions as reports_permissions
from reports.reports_styles import (QuequicomStyles, EntriesStyles, ClosedRecordsStyles, ThemesRankingStyles,
                                    ApplicantsRecordCountStyles, RecordStateGroupsStyles, OperatorsStyles)
from reports.serializers import (QuequicomReportRequestSerializer, QuequicomReportSerializer, ReportsRequestSerializer,
                                 EntriesReportSerializer, ClosedRecordsReportSerializer,
                                 ReportRequestDatesLimitSerializer, ThemesRankingSerializer,
                                 AccessLogRequestSerializer, AccessLogSerializer, ThemeRankingRequestSerializer,
                                 ApplicantsRecordCountSerializer, ApplicantsRecordCountRequestSerializer,
                                 RecordStateGroupsReportSerializer, OperatorsReportSerializer)
from themes.models import ElementDetailThemeGroup, ElementDetail


class ReportsBaseView(ColumnNamesMixin, XLSXFileMixin, ExcelBaseStyles, PermissionActionMixin, APIView):
    renderer_classes = [CustomXLSXRenderer, JSONRenderer, BrowsableAPIRenderer]
    filename = "report.xlsx"

    request_serializer_class = ReportsRequestSerializer
    report_serializer_class = None

    def post(self, request, *args, **kwargs):
        report_request_serializer = self.request_serializer_class(data=self.request.data,
                                                                  context={"request": self.request})

        if not report_request_serializer.is_valid():
            request.accepted_renderer = JSONRenderer()
            raise ValidationError(report_request_serializer.errors)
        else:
            validated_data = report_request_serializer.validated_data
            filter_params = self.get_filter_params(validated_data)
            exclude_params = self.get_exclude_params(validated_data)
            queryset = self.get_queryset(filter_params, exclude_params, validated_data)
        queryset_serialized = self.serialize_queryset(validated_data, queryset)
        return Response(queryset_serialized, status=HTTP_200_OK)

    def get_filter_params(self, validated_data):
        """
        Prepare query filter parameters

        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        params = {"responsible_profile__isnull": False}

        create_date_gte = validated_data.get("create_date_gte")
        if create_date_gte:
            params["created_at__gte"] = create_date_gte
        create_date_lte = validated_data.get("create_date_lte")
        if create_date_lte:
            params["created_at__lte"] = create_date_lte

        user_group = self.request.user.usergroup.group
        if user_group != Group.get_dair_group():
            params["responsible_profile__group_plate__startswith"] = user_group.group_plate

        record_type_id = validated_data.get("record_type_id")
        if record_type_id:
            params["record_type_id"] = record_type_id

        input_channel_id = validated_data.get("input_channel_id")
        if input_channel_id:
            params["input_channel_id"] = input_channel_id

        applicant_type_id = validated_data.get("applicant_type_id")
        if applicant_type_id:
            params["applicant_type_id"] = applicant_type_id

        support_id = validated_data.get("support_id")
        if support_id:
            params["support_id"] = support_id

        district_id = validated_data.get("district_id")
        if district_id:
            params["ubication__district_id"] = district_id

        neighborhood = validated_data.get("neighborhood")
        if neighborhood:
            params["ubication__neighborhood__unaccent__ilike_contains"] = neighborhood

        return params

    def get_exclude_params(self, validated_data):
        """
        Prepare query exclude parameters

        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        return {}

    def get_queryset(self, filter_params, exclude_params, validated_data):
        """
        Filter record cards queryset

        :param filter_params: dict of query parameters to filter
        :param exclude_params: dict of query parameters to exclude
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        queryset = RecordCard.objects.filter(**filter_params)
        if exclude_params:
            queryset = queryset.exclude(**exclude_params)
        return queryset.order_by("created_at")[:self.get_reg_limit()]

    def serialize_queryset(self, validated_data, queryset):
        """
        Serialize record cards

        :param validated_data: Dict with validated data of the serializer
        :param queryset: queryset to serialize
        :return: Data serialized
        """
        queryset_list = []
        serializer_class = self.get_report_serializer_class()
        for db_object in queryset:
            self.serializer = serializer_class(**self.get_serializer_params(validated_data, db_object))
            queryset_list.append(self.serializer.data)

        return queryset_list

    def get_serializer(self):
        return

    def get_report_serializer_class(self):
        if not self.report_serializer_class:
            raise Exception("Add report serializer class")
        return self.report_serializer_class

    @staticmethod
    def get_reg_limit():
        return int(Parameter.get_parameter_by_key("NUM_REGISTRES_REPORTS", 5000))

    def get_serializer_params(self, validated_data, instance):
        return {"instance": instance}


class RecordCardAreaFilterMixin:

    def get_filter_params(self, validated_data):
        """
        Prepare query filter parameters

        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        params = super().get_filter_params(validated_data)
        area_id = validated_data.get("area_id")
        if area_id:
            params["element_detail__element__area_id"] = area_id
        return params


class AllowNoClosedRecordsMixin:

    @staticmethod
    def filter_close_date(record_cards, validated_data):
        if "close_date_lte" in validated_data and "close_date_gte" in validated_data:
            return record_cards.filter(Q(closing_date__lte=validated_data["close_date_lte"],
                                         closing_date__gte=validated_data["close_date_gte"]))
        return record_cards


@method_decorator(name="post", decorator=post_record_card_schema_factory(responses={
    HTTP_200_OK: "Quequicom Report",
    HTTP_400_BAD_REQUEST: "Bad request: Validation Error",
    HTTP_403_FORBIDDEN: "Acces not Allowed",
    HTTP_404_NOT_FOUND: "Not Found",
}, request_body_serializer=QuequicomReportRequestSerializer))
class QuequicomReportView(QuequicomStyles, AllowNoClosedRecordsMixin, ReportsBaseView):
    """
    Endpoint to generate Quequicom Report, which include information about RecordCards.
    The report will be only generated in XLSX format.
    Operations report permission is needed to generate the report.
    Records queryset can be filtered by create date, close date, area, record_type, input_channel, applicant_type,
    support, district and neighborhood and theme_group.

    Validation issues:
    - create_date_gte and create_date_lte must be sent together
    - close_date_gte and close_date_lte must  be sent together
    """

    renderer_classes = [CustomXLSXRenderer]
    filename = "quequicom.xlsx"
    request_serializer_class = QuequicomReportRequestSerializer
    permission = reports_permissions.REPS_OPERATIONS

    def __init__(self, *args, **kwargs):
        self.max_features = 0
        super().__init__(*args, **kwargs)

    def get_queryset(self, filter_params, exclude_params, validated_data):
        """
        Filter record cards queryset

        :param filter_params: dict of query parameters to filter
        :param exclude_params: dict of query parameters to exclude
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        record_cards = RecordCard.objects.filter(**filter_params)
        record_cards = self.filter_close_date(record_cards, validated_data)
        record_cards = record_cards.select_related(
            "element_detail", "element_detail__element", "element_detail__element__area", "responsible_profile",
            "ubication", "ubication__district", "workflow", "workflow__workflowplan",
            "workflow__workflowresolution", "recordcardresponse", "claimed_from", "recordcardaudit",
            "recordcardresponse__response_channel").prefetch_related(
            Prefetch("recordcardspecialfeatures_set",
                     queryset=RecordCardSpecialFeatures.objects.filter(enabled=True)),
            Prefetch("recordcardtextresponse_set",
                     queryset=RecordCardTextResponse.objects.filter(enabled=True).order_by("created_at"))
        )

        only_fields = self.set_initial_only_fields()

        if validated_data["who"]:
            record_cards = record_cards.select_related("request")
            only_fields += self.set_who_only_fields()
        if validated_data["how"]:
            record_cards = record_cards.prefetch_related(
                Prefetch("recordcardfeatures_set", queryset=RecordCardFeatures.objects.filter(enabled=True)))

        return record_cards.only(*only_fields).order_by("created_at")[:self.get_reg_limit()]

    def get_filter_params(self, validated_data):
        params = super().get_filter_params(validated_data)
        self.set_element_details_filters(validated_data, params)
        return params

    @staticmethod
    def get_reg_limit():
        return int(Parameter.get_parameter_by_key("NUM_REGISTRES_QQC", 5000))

    @staticmethod
    def set_element_details_filters(validated_data, params):
        themes_element_detail_ids = []
        areas_element_detail_ids = []

        theme_group_ids = validated_data.get("theme_group_ids")
        if theme_group_ids:
            theme_group_ids = [theme_group.pk for theme_group in validated_data["theme_group_ids"]]

            themes_element_detail_ids = ElementDetailThemeGroup.objects.filter(
                theme_group_id__in=theme_group_ids).values_list("element_detail_id", flat=True)
        area_id = validated_data.get("area_id")
        if area_id:
            areas_element_detail_ids = ElementDetail.objects.filter(
                element__area_id=area_id).values_list("pk", flat=True)

        if themes_element_detail_ids and areas_element_detail_ids:
            params["element_detail_id__in"] = themes_element_detail_ids.intersection(areas_element_detail_ids)
        elif themes_element_detail_ids:
            params["element_detail_id__in"] = themes_element_detail_ids
        elif areas_element_detail_ids:
            params["element_detail_id__in"] = areas_element_detail_ids

    @staticmethod
    def set_initial_only_fields():
        return ("created_at", "normalized_record_id", "record_state_id", "record_type_id", "element_detail",
                "element_detail__description", "element_detail__element", "element_detail__element__description",
                "description", "element_detail__element__area", "element_detail__element__description",
                "responsible_profile", "responsible_profile__description", "workflow", "workflow__workflowplan",
                "workflow__workflowresolution", "ubication", "ubication__via_type", "ubication__official_street_name",
                "ubication__street2", "ubication__letter", "ubication__neighborhood", "ubication__district",
                "ubication__district__name", "ubication__coordinate_x", "ubication__coordinate_y",
                "ubication__statistical_sector", "ubication__research_zone", "recordcardresponse",
                "recordcardresponse__response_channel", "recordcardresponse__response_channel__id",
                "input_channel_id", "applicant_type_id", "support_id", "closing_date", "claimed_from",
                "claimed_from__normalized_record_id", "recordcardaudit", "recordcardaudit__validation_user",
                "recordcardaudit__planif_user", "recordcardaudit__resol_user", "recordcardaudit__resol_comment",
                "recordcardaudit__close_user")

    @staticmethod
    def set_who_only_fields() -> tuple:
        return ("request", "request__applicant_id",)

    def serialize_queryset(self, validated_data, record_cards):
        """
        Serialize record cards

        :param validated_data: Dict with validated data of the serializer
        :param record_cards: list of records to serialize
        :return: Data serialized
        """
        records_list = []

        self.serializer = QuequicomReportSerializer(who=validated_data["who"], how=validated_data["how"])
        for record_card in record_cards:
            self.reset_report_serializer(self.serializer, record_card)
            records_list.append(self.serializer.data)
            if self.serializer.record_features > self.max_features:
                self.max_features = self.serializer.record_features

        if self.max_features:
            self.add_extra_empty_features(records_list)
        return records_list

    @staticmethod
    def reset_report_serializer(report_serializer, record_card):
        report_serializer.record_features = 0
        report_serializer.instance = record_card
        if hasattr(report_serializer, "_data"):
            delattr(report_serializer, "_data")

    def add_extra_empty_features(self, records_list):
        """
        Add empty features keys in order to print them on the excel

        :param records_list: List of serialized records
        :return:
        """
        for record in records_list:
            for index in range(self.max_features):
                if "ATRIBUT{}".format(index) not in record:
                    record["ATRIBUT{}".format(index)] = ""
                    record["VALOR{}".format(index)] = ""


@method_decorator(name="post", decorator=post_record_card_schema_factory(responses={
    HTTP_200_OK: EntriesReportSerializer(many=True),
    HTTP_400_BAD_REQUEST: "Bad request: Validation Error",
    HTTP_403_FORBIDDEN: "Acces not Allowed",
    HTTP_404_NOT_FOUND: "Not Found",
}, request_body_serializer=ReportRequestDatesLimitSerializer))
class EntriesReportView(AllowNoClosedRecordsMixin, EntriesStyles, RecordCardAreaFilterMixin, ReportsBaseView):
    """
    Endpoint to generate RecordCard Entries Report, which include information about RecordCard"s creations.
    The report can be generated in XLSX and JSON format.
    Audit report permission is needed to generate the report.
    Records queryset can be filtered by create date, close date, area, record_type, input_channel, applicant_type,
    support, district and neighborhood.

    Validation issues:
    - create_date_gte and create_date_lte must be sent together
    - close_date_gte and close_date_lte must be sent together
    - the dates of each pair can not be separated for more than the days indicated in Parameter REPORTS_DAYS_LIMITS
    """

    filename = "entries.xlsx"
    request_serializer_class = ReportRequestDatesLimitSerializer
    report_serializer_class = EntriesReportSerializer
    permission = reports_permissions.REPS_AUDIT

    def get_queryset(self, filter_params, exclude_params, validated_data):
        """
        Filter record cards queryset

        :param filter_params: dict of query parameters to filter
        :param exclude_params: dict of query parameters to exclude
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        record_cards = RecordCard.objects.filter(**filter_params)
        record_cards = self.filter_close_date(record_cards, validated_data)

        record_cards = record_cards.select_related(
            "record_state", "record_type", "element_detail", "element_detail__element",
            "responsible_profile", "responsible_profile__ambit_coordinator", "ubication", "ubication__district")

        only_fields = self.set_only_fields()

        return record_cards.only(*only_fields).order_by("created_at")[:self.get_reg_limit()]

    @staticmethod
    def set_only_fields():
        return ("created_at", "normalized_record_id", "record_state", "record_state__description",
                "record_type", "record_type__description", "element_detail", "element_detail__description",
                "element_detail__element", "element_detail__element__description", "workflow_id",
                "responsible_profile", "responsible_profile__description", "responsible_profile__ambit_coordinator",
                "responsible_profile__ambit_coordinator__description", "responsible_profile__profile_ctrl_user_id",
                "ubication", "ubication__street", "ubication__district", "ubication__district__name")


@method_decorator(name="post", decorator=post_record_card_schema_factory(responses={
    HTTP_200_OK: AccessLogSerializer(many=True),
    HTTP_400_BAD_REQUEST: "Bad request: Validation Error",
    HTTP_404_NOT_FOUND: "Not Found",
}, request_body_serializer=AccessLogRequestSerializer))
class AccessReportView(XLSXFileMixin, APIView):
    """
    Endpoint to generate Acces Log Report, which include information about the acces to the system from users.
    each state assigned to groups. The report can be generated in XLSX and JSON format.
    """

    filter_serializer_cls = AccessLogRequestSerializer
    filename = "access_log.xlsx"
    renderer_classes = [CustomXLSXRenderer, JSONRenderer, BrowsableAPIRenderer]
    response_serializer_cls = AccessLogSerializer
    queryset = AccessLog.objects.select_related("user_group__user__username", "group", "group__ambit_coordinator")

    def post(self, request, *args, **kwargs):
        if not self.filter_serializer.is_valid():
            request.accepted_renderer = JSONRenderer()
            raise ValidationError(self.filter_serializer.errors)
        data = self.get_data()
        return Response(data=self.response_serializer_cls(instance=data, many=True).data, status=status.HTTP_200_OK)

    def get_data(self):
        """
        :return: Report data extracted from the queryset operations and aggregates.
        """
        qs = self.get_queryset()
        qs = qs.values(
            "user_group__user__username", "group", "group__description", "group__profile_ctrl_user_id",
            "group__ambit_coordinator__description"
        ).annotate(
            count=Count("group_id"),
            username=F("user_group__user__username"),
            linia_servei=F("group__profile_ctrl_user_id"),
            operador=F("group__description"),
            sector=F("group__ambit_coordinator__description"),
        )
        return qs

    def get_queryset(self, **kwargs):
        lookups = self.get_filter_kwargs()
        lookups.update(kwargs)
        return self.queryset.filter(**lookups)

    def get_filter_kwargs(self):
        return {
            "created_at__gte": self.filter_serializer.validated_data["from_date"],
            "created_at__lte": self.filter_serializer.validated_data["to_date"],
        }

    @cached_property
    def filter_serializer(self):
        return self.filter_serializer_cls(data=self.request.data)


@method_decorator(name="post", decorator=post_record_card_schema_factory(responses={
    HTTP_200_OK: ClosedRecordsReportSerializer(many=True),
    HTTP_400_BAD_REQUEST: "Bad request: Validation Error",
    HTTP_403_FORBIDDEN: "Acces not Allowed",
    HTTP_404_NOT_FOUND: "Not Found",
}, request_body_serializer=ReportRequestDatesLimitSerializer))
class ClosedRecordsReportView(ClosedRecordsStyles, RecordCardAreaFilterMixin, ReportsBaseView):
    """
    Endpoint to generate RecordCard Closed Report, which include information about RecordCard's closing
    or external processing. The report can be generated in XLSX and JSON format.
    Audit report permission is needed to generate the report.
    Records queryset can be filtered by create date, close date, area, record_type, input_channel, applicant_type,
    support, district and neighborhood.

    Validation issues:
    - create_date_gte and create_date_lte must be sent together
    - close_date_gte and close_date_lte must be sent together
    - the dates of each pair can not be separated for more than the days indicated in Parameter REPORTS_DAYS_LIMITS
    """

    filename = "closed.xlsx"
    request_serializer_class = ReportRequestDatesLimitSerializer
    report_serializer_class = ClosedRecordsReportSerializer
    permission = reports_permissions.REPS_AUDIT

    def get_queryset(self, filter_params, exclude_params, validated_data):
        """
        Filter record cards queryset

        :param filter_params: dict of query parameters to filter
        :param exclude_params: dict of query parameters to exclude
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        record_cards = RecordCard.objects.filter(**filter_params)

        record_cards = record_cards.select_related(
            "record_type", "element_detail", "responsible_profile", "ubication", "ubication__district")
        only_fields = self.set_only_fields()

        return record_cards.only(*only_fields).order_by("created_at")[:self.get_reg_limit()]

    def get_filter_params(self, validated_data):
        params = super().get_filter_params(validated_data)

        params["record_state_id__in"] = RecordState.CLOSED_STATES

        close_date_gte = validated_data.get("close_date_gte")
        if close_date_gte:
            params["closing_date__gte"] = close_date_gte
        close_date_lte = validated_data.get("close_date_lte")
        if close_date_lte:
            params["closing_date__lte"] = close_date_lte
        return params

    @staticmethod
    def set_only_fields():
        return ("created_at", "normalized_record_id", "workflow_id", "closing_date", "record_type",
                "record_type__description", "element_detail", "element_detail__description",
                "responsible_profile", "responsible_profile__description", "responsible_profile__profile_ctrl_user_id",
                "ubication", "ubication__street", "ubication__district", "ubication__district__name")


@method_decorator(name="post",
                  decorator=post_record_card_schema_factory(responses={
                      HTTP_200_OK: ThemesRankingSerializer(many=True),
                      HTTP_400_BAD_REQUEST: "Bad request: Validation Error",
                      HTTP_403_FORBIDDEN: "Acces not Allowed",
                      HTTP_404_NOT_FOUND: "Not Found",
                  }, request_body_serializer=ThemeRankingRequestSerializer))
class ThemesRankingReportView(ThemesRankingStyles, AllowNoClosedRecordsMixin, RecordCardAreaFilterMixin,
                              ReportsBaseView):
    """
    Endpoint to generate Theme Ranking Report, which include information about themes usage during the period requested.
    The report can be generated in XLSX and JSON format.
    Management report permission is needed to generate the report.
    Records queryset can be filtered by create date, close date, area, record_type, input_channel, applicant_type,
    support, district and neighborhood.

    Validation issues:
    - create_date_gte and create_date_lte must be sent together
    - close_date_gte and close_date_lte must be sent together
    - the dates of each pair can not be separated for more than the days indicated in Parameter REPORTS_DAYS_LIMITS
    - the days between close_date_lte and create_date_gte can not be separated for more than the days
    indicated in Parameter REPORTS_DAYS_LIMITS
    """
    filename = "themes_ranking.xlsx"
    request_serializer_class = ThemeRankingRequestSerializer
    report_serializer_class = ThemesRankingSerializer
    permission = reports_permissions.REPS_MANAGEMENT
    resp_profile_not_tramit_iris1 = 0

    def __init__(self, *args, **kwargs):
        self.month_keys_list = []
        super().__init__(*args, **kwargs)

    def get_queryset(self, filter_params, exclude_params, validated_data):
        """
        Filter record cards queryset

        :param filter_params: dict of query parameters to filter
        :param exclude_params: dict of query parameters to exclude
        :param validated_data: Dict with validated data of the serializer
        :return:
        """

        record_cards = RecordCard.objects.filter(**filter_params).exclude(record_state_id=RecordState.NO_PROCESSED)
        record_cards = self.filter_close_date(record_cards, validated_data)
        if not record_cards:
            return []

        num_records = record_cards.values(
            "element_detail_id", "element_detail__description", "element_detail__element__description",
            "created_at__month", "created_at__year").annotate(records=Count("element_detail_id"))
        self.set_month_keys(num_records)

        totals = self.set_totals_initial()
        themes_dict = self.register_months_counters(num_records, totals)
        return self.set_registers(themes_dict, record_cards.count(), totals)

    def set_month_keys(self, num_records) -> None:
        """
        Set the list of month keys.
        Update the list with the month between the first month key and the last month key

        :param num_records: Queryset with month numbers
        :return:
        """
        record_ordered_by_month = num_records.order_by("created_at__year", "created_at__month")
        first_month = record_ordered_by_month.first()
        last_month = record_ordered_by_month.last()
        first_month_key = "{}/{}".format(first_month["created_at__month"], first_month["created_at__year"])
        last_month_key = "{}/{}".format(last_month["created_at__month"], last_month["created_at__year"])

        self.month_keys_list.append(first_month_key)
        if first_month_key != last_month_key:
            current_moth_key = self.get_next_month_key(first_month_key)
            while current_moth_key != last_month_key:
                self.month_keys_list.append(current_moth_key)
                current_moth_key = self.get_next_month_key(current_moth_key)
            self.month_keys_list.append(last_month_key)

    @staticmethod
    def get_next_month_key(current_month_key) -> str:
        current_month, current_year = int(current_month_key.split("/")[0]), int(current_month_key.split("/")[1])
        if current_month == 12:
            return "1/{}".format(current_year + 1)
        else:
            return "{}/{}".format(current_month + 1, current_year)

    def set_totals_initial(self) -> dict:
        """
        Declare total initial information
        :return:
        """
        totals = {"detail_description": "TOTAL", "element_description": "TOTAL", "total": 0, "percentage": 100}
        totals.update({month: 0 for month in self.month_keys_list})
        return totals

    def register_months_counters(self, num_records, totals) -> dict:
        """
        Transform the month numbers queryset into a dict structure, adding the counters

        :param num_records: Queryset with month numbers
        :param totals: dict of totals
        :return:
        """
        themes_dict = {}
        for num_record in num_records:
            element_detail_id = num_record["element_detail_id"]
            if element_detail_id not in themes_dict:
                themes_dict[element_detail_id] = {
                    "detail_description": num_record["element_detail__description"],
                    "element_description": num_record["element_detail__element__description"],
                    "total": 0
                }
                themes_dict[element_detail_id].update({month: 0 for month in self.month_keys_list})

            month_key = "{}/{}".format(num_record["created_at__month"], num_record["created_at__year"])

            totals[month_key] += num_record["records"]
            totals["total"] += num_record["records"]
            themes_dict[element_detail_id][month_key] = num_record["records"]
            themes_dict[element_detail_id]["total"] += num_record["records"]
        return themes_dict

    def get_serializer_params(self, validated_data, instance) -> dict:
        return {"instance": instance, "month_keys_list": self.month_keys_list}

    def set_registers(self, themes_dict, record_cards_number, totals) -> list:
        """

        :param themes_dict: dict of themes with month counters
        :param record_cards_number: total number of record cards
        :param totals: dict of totals
        :return: list of dicts with month counters
        """
        themes_count = self.order_themes_by_total(themes_dict)
        registers = self.add_others_register(themes_count)
        self.add_percentages(registers, record_cards_number)
        registers.append(totals)
        return registers

    @staticmethod
    def order_themes_by_total(themes_dict) -> list:
        """
        Convert themes dict in a list and order by total number of records
        :param themes_dict: dict of themes with month counters
        :return:
        """
        themes_count = [theme_dict for _, theme_dict in themes_dict.items()]
        return sorted(themes_count, key=lambda x: x["total"], reverse=True)

    def add_others_register(self, themes_count) -> list:
        """
        Check if other register has to be add and dot it if it's necessary

        :param themes_count: list of ordered
        :return:
        """
        registers = themes_count[:25]
        other_registers = themes_count[25:]
        if other_registers:
            other = {"detail_description": "ALTRES", "element_description": "ALTRES", "total": 0}
            other.update({month: 0 for month in self.month_keys_list})
            for record in other_registers:
                other["total"] += record["total"]
                for month_key in self.month_keys_list:
                    other[month_key] += record.get(month_key, 0)
            registers.append(other)
        return registers

    @staticmethod
    def add_percentages(registers, total_records) -> None:
        for register in registers:
            register["percentage"] = round((register["total"] / total_records) * 100, 2)


@method_decorator(name="post",
                  decorator=post_record_card_schema_factory(responses={
                      HTTP_200_OK: ApplicantsRecordCountSerializer(many=True),
                      HTTP_400_BAD_REQUEST: "Bad request: Validation Error",
                      HTTP_403_FORBIDDEN: "Acces not Allowed",
                      HTTP_404_NOT_FOUND: "Not Found",
                  }, request_body_serializer=ApplicantsRecordCountRequestSerializer))
class ApplicantsRecordCountReportView(ApplicantsRecordCountStyles, RecordCardAreaFilterMixin, AllowNoClosedRecordsMixin,
                                      ReportsBaseView):
    """
    Endpoint to generate Applciants Record Count Report, which include information about the applicants
    and the number of records that they have applyied. The report can be generated in XLSX and JSON format.
    Citizen report permission is needed to generate the report.
    Records queryset can be filtered by create date, close date, area, record_type, input_channel, applicant_type,
    support, district, neighborhood, applicant (citizen or social_entity) and min_requests.

    Validation issues:
    - create_date_gte and create_date_lte must be sent together
    - close_date_gte and close_date_lte must be sent together
    - the dates of each pair can not be separated for more than the days indicated in Parameter REPORTS_DAYS_LIMITS
    - the days between close_date_lte and create_date_gte can not be separated for more than the days
    indicated in Parameter REPORTS_DAYS_LIMITS
    """
    request_serializer_class = ApplicantsRecordCountRequestSerializer
    report_serializer_class = ApplicantsRecordCountSerializer
    filename = "applicants-records-count.xlsx"
    permission = reports_permissions.REPS_MANAGEMENT
    applicant_not_tramit_iris1 = 0

    def get_queryset(self, filter_params, exclude_params, validated_data):
        """
        Filter record cards queryset

        :param filter_params: dict of query parameters to filter
        :param exclude_params: dict of query parameters to exclude
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        queryset = RecordCard.objects.filter(**filter_params).exclude(record_state_id=RecordState.NO_PROCESSED)
        queryset = self.filter_close_date(queryset, validated_data)
        if exclude_params:
            queryset = queryset.exclude(**exclude_params)
        queryset = queryset.values(
            "request__applicant", "request__applicant__citizen__dni", "request__applicant__social_entity__cif",
            "request__applicant__citizen__name", "request__applicant__citizen__first_surname",
            "request__applicant__citizen__second_surname", "request__applicant__social_entity__social_reason"
        ).annotate(
            records=Count("request__applicant"),
            document=Coalesce("request__applicant__citizen__dni", "request__applicant__social_entity__cif"),
            name=Coalesce(
                "request__applicant__social_entity__social_reason",
                Concat("request__applicant__citizen__name", Value(" "), "request__applicant__citizen__first_surname",
                       Value(" "), "request__applicant__citizen__second_surname"))
        ).values("request__applicant", "records", "document", "name").order_by("-records")

        min_requests = validated_data.get("min_requests")
        if min_requests is not None:
            min_applicant_records = min_requests
        else:
            min_applicant_records = int(Parameter.get_parameter_by_key("NUMERO_MINIM_INCIDENCIES_CIUTADA", 4))
        queryset = queryset.filter(records__gt=min_applicant_records)

        return queryset

    def get_filter_params(self, validated_data):
        params = super().get_filter_params(validated_data)
        params["request__applicant__isnull"] = False
        return params

    def get_exclude_params(self, validated_data):
        exclude_params = super().get_exclude_params(validated_data)
        applicant = validated_data.get("applicant")
        if applicant:
            if applicant == Citizen.CITIZEN_CHOICE:
                exclude_params["request__applicant__social_entity__isnull"] = False
            elif applicant == SocialEntity.SOCIAL_ENTITY_CHOICE:
                exclude_params["request__applicant__citizen__isnull"] = False
        return exclude_params


@method_decorator(name="post", decorator=post_record_card_schema_factory(responses={
    HTTP_200_OK: RecordStateGroupsReportSerializer(many=True),
    HTTP_400_BAD_REQUEST: "Bad request: Validation Error",
    HTTP_403_FORBIDDEN: "Acces not Allowed",
    HTTP_404_NOT_FOUND: "Not Found",
}, request_body_serializer=ReportRequestDatesLimitSerializer))
class RecordStateGroupsReportView(RecordStateGroupsStyles, AllowNoClosedRecordsMixin, RecordCardAreaFilterMixin,
                                  ReportsBaseView):
    """
    Endpoint to generate Record States Groups Report, which include information about the number of records in
    each state assigned to groups. The report can be generated in XLSX and JSON format.
    Management report permission is needed to generate the report.
    Records queryset can be filtered by create date, close date, area, record_type, input_channel, applicant_type,
    support, district, neighborhood.

    Validation issues:
    - create_date_gte and create_date_lte must be sent together
    - close_date_gte and close_date_lte must be sent together
    - the dates of each pair can not be separated for more than the days indicated in Parameter REPORTS_DAYS_LIMITS
    """

    request_serializer_class = ReportRequestDatesLimitSerializer
    report_serializer_class = RecordStateGroupsReportSerializer
    filename = "record-state-groups.xlsx"
    permission = reports_permissions.REPS_MANAGEMENT

    PLATE_KEY = "plate"
    OPERATOR_KEY = "perfil_operador"
    PEND_VAL_KEY = "pendent_validar"
    PROC_KEY = "en_proces"
    CLOSE_KEY = "tancada"
    CANCEL_KEY = "cancelada"
    EXTERNAL_KEY = "tramitacio_externa"
    TOTAL_KEY = "total"
    PERCENTAGE_KEY = "percentatge"

    def get_queryset(self, filter_params, exclude_params, validated_data):
        """
        Filter record cards queryset

        :param filter_params: dict of query parameters to filter
        :param exclude_params: dict of query parameters to exclude
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        record_cards = RecordCard.objects.filter(**filter_params).exclude(record_state_id=RecordState.NO_PROCESSED)
        record_cards = self.filter_close_date(record_cards, validated_data)

        records_counters = record_cards.values(
            "responsible_profile__group_plate", "responsible_profile__description", "record_state_id").annotate(
            counters=Count("responsible_profile__group_plate"))

        totals = self.set_totals_initial()
        groups_dict = self.register_records_counters(records_counters, totals)

        return self.set_registers(groups_dict, record_cards.count(), totals)

    def set_totals_initial(self) -> dict:
        """
        Declare total initial information
        :return:
        """
        return {self.OPERATOR_KEY: "TOTALS", self.PEND_VAL_KEY: 0, self.PROC_KEY: 0, self.CLOSE_KEY: 0,
                self.CANCEL_KEY: 0, self.EXTERNAL_KEY: 0, self.TOTAL_KEY: 0, self.PERCENTAGE_KEY: 100}

    def register_records_counters(self, records_counters, totals):
        groups_dict = {}
        for record_counter in records_counters:
            group_plate = record_counter["responsible_profile__group_plate"]
            if group_plate not in groups_dict:
                groups_dict[group_plate] = {
                    self.PLATE_KEY: group_plate, self.OPERATOR_KEY: record_counter["responsible_profile__description"],
                    self.PEND_VAL_KEY: 0, self.PROC_KEY: 0, self.CLOSE_KEY: 0, self.CANCEL_KEY: 0, self.EXTERNAL_KEY: 0,
                    self.TOTAL_KEY: 0
                }
            counters = record_counter["counters"]
            self.update_group_states(record_counter["record_state_id"], counters, groups_dict[group_plate], totals)

            groups_dict[group_plate][self.TOTAL_KEY] += counters
            totals[self.TOTAL_KEY] += counters
        return groups_dict

    def update_group_states(self, record_state_id, counters, group, totals):
        if record_state_id in RecordState.PEND_VALIDATE_STATES:
            group[self.PEND_VAL_KEY] += counters
            totals[self.PEND_VAL_KEY] += counters
        elif record_state_id in RecordState.STATES_IN_PROCESSING:
            group[self.PROC_KEY] += counters
            totals[self.PROC_KEY] += counters
        elif record_state_id == RecordState.CLOSED:
            group[self.CLOSE_KEY] += counters
            totals[self.CLOSE_KEY] += counters
        elif record_state_id == RecordState.CANCELLED:
            group[self.CANCEL_KEY] += counters
            totals[self.CANCEL_KEY] += counters
        elif record_state_id == RecordState.EXTERNAL_PROCESSING:
            group[self.EXTERNAL_KEY] += counters
            totals[self.EXTERNAL_KEY] += counters

    def set_registers(self, groups_dict, record_cards_number, totals) -> list:
        """

        :param groups_dict: dict of groups with reocrds counters
        :param record_cards_number: total number of record cards
        :param totals: dict of totals
        :return: list of dicts with records counters
        """
        registers = self.order_groups_by_plate(groups_dict)
        self.add_percentages(registers, record_cards_number)
        registers.append(totals)
        return registers

    def order_groups_by_plate(self, groups_dict) -> list:
        """
        Convert themes dict in a list and order by total number of records
        :param groups_dict: dict of themes with month counters
        :return:
        """
        records_count = [group_dict for _, group_dict in groups_dict.items()]
        return sorted(records_count, key=lambda x: x[self.PLATE_KEY])

    def add_percentages(self, registers, total_records) -> None:
        for register in registers:
            register[self.PERCENTAGE_KEY] = round((register[self.TOTAL_KEY] / total_records) * 100, 2)


@method_decorator(name="post", decorator=post_record_card_schema_factory(responses={
    HTTP_200_OK: OperatorsReportSerializer(many=True),
    HTTP_400_BAD_REQUEST: "Bad request: Validation Error",
    HTTP_403_FORBIDDEN: "Acces not Allowed",
    HTTP_404_NOT_FOUND: "Not Found",
}, request_body_serializer=ReportRequestDatesLimitSerializer))
class OperatorsReportView(OperatorsStyles, RecordCardAreaFilterMixin, ReportsBaseView):
    """
    Endpoint to generate Operators Report, which include information about the actions done by the operators during
    the request period. The report can be generated in XLSX and JSON format.
    Users report permission is needed to generate the report.
    Records queryset can be filtered by create date, close date, area, record_type, input_channel, applicant_type,
    support, district, neighborhood.

    In this report, only RecordCard with RecordType Query (5) has to be taken in account

    Validation issues:
    - create_date_gte and create_date_lte must be sent together
    - close_date_gte and close_date_lte must be sent together
    - the dates of each pair can not be separated for more than the days indicated in Parameter REPORTS_DAYS_LIMITS
    """

    request_serializer_class = ReportRequestDatesLimitSerializer
    report_serializer_class = OperatorsReportSerializer
    filename = "operators.xlsx"
    permission = reports_permissions.REPS_USERS
    no_records_filters = ["created_at__gte", "created_at__lte"]
    iris_user = "IRIS"

    def get_filter_params(self, validated_data):
        params = super().get_filter_params(validated_data)
        # update filters for record cards related
        filters = {}
        for key, value in params.items():
            if key in self.no_records_filters:
                filters.update({key: value})
            else:
                filters.update({"record_card__{}".format(key): value})
        if "close_date_gte" in validated_data:
            filters.update({"record_card__closing_date__gte": validated_data["close_date_gte"]})
        if "close_date_lte" in validated_data:
            filters.update({"record_card__closing_date__lte": validated_data["close_date_lte"]})
        # In this report, only RecordCard with RecordType Query (5) has to be taken in account
        filters["record_card__record_type_id"] = RecordType.QUERY
        return filters

    def get_queryset(self, filter_params, exclude_params, validated_data):
        """
        Filter record cards queryset

        :param filter_params: dict of query parameters to filter
        :param exclude_params: dict of query parameters to exclude
        :param validated_data: Dict with validated data of the serializer
        :return:
        """

        states_changes = RecordCardStateHistory.objects.filter(**filter_params).exclude(
            record_card__record_state_id=RecordState.NO_PROCESSED).values("user_id").annotate(
            validated=Count("user_id", filter=Q(previous_state_id__in=RecordState.PEND_VALIDATE_STATES,
                                                next_state_id__in=RecordState.VALIDATE_STATES)),
            closed=Count("user_id", filter=Q(next_state_id=RecordState.CLOSED)),
            cancelled=Count("user_id", filter=Q(next_state_id=RecordState.CANCELLED)),
            external=Count("user_id", filter=Q(next_state_id=RecordState.EXTERNAL_PROCESSING)),
            avg_response=Avg(F("record_card__closing_date") - F("record_card__created_at"),
                             filter=Q(next_state_id=RecordState.CLOSED, record_card__closing_date__isnull=False))
        )
        users_reasignations = RecordCardReasignation.objects.filter(**filter_params).exclude(
            Q(record_card__record_state_id=RecordState.NO_PROCESSED) |
            Q(reason_id__in=Reason.AUTOMATIC_REASIGNATIONS_REASONS)
        ).values("user_id").annotate(reasignations=Count("user_id"))

        user_dicts = self.group_registers_by_user(states_changes, users_reasignations)
        return self.filter_register_to_report(user_dicts)

    def filter_register_to_report(self, user_dicts):
        report_registers = []
        for _, user_dict in user_dicts.items():
            if user_dict["validated"] == 0 and user_dict["closed"] == 0:
                continue
            if user_dict["user_id"] == self.iris_user:
                continue
            report_registers.append(user_dict)
        return report_registers

    def group_registers_by_user(self, states_changes, users_reasignations):
        user_dicts = {}
        self.register_states_changes(states_changes, user_dicts)
        self.register_users_reasignations(users_reasignations, user_dicts)
        return user_dicts

    def register_states_changes(self, states_changes, user_dicts):
        for state_changes in states_changes:
            user_id = state_changes["user_id"]
            if user_id not in user_dicts:
                user_dicts[user_id] = self.empty_user_dict(user_id)
            user_dicts[user_id]["validated"] = state_changes["validated"]
            user_dicts[user_id]["closed"] = state_changes["closed"]
            user_dicts[user_id]["cancelled"] = state_changes["cancelled"]
            user_dicts[user_id]["external"] = state_changes["external"]
            if state_changes["avg_response"]:
                # Average time to response in hours
                user_dicts[user_id]["avg_response"] = round(state_changes["avg_response"].total_seconds() / 3600, 2)

    def register_users_reasignations(self, users_reasignations, user_dicts):
        for reasignations in users_reasignations:
            user_id = reasignations["user_id"]
            if user_id not in user_dicts:
                user_dicts[user_id] = self.empty_user_dict(user_id)
            user_dicts[user_id]["reasignations"] = reasignations["reasignations"]

    @staticmethod
    def empty_user_dict(user_id):
        return {"validated": 0, "closed": 0, "cancelled": 0, "external": 0, "reasignations": 0, "avg_response": 0,
                "user_id": user_id}
