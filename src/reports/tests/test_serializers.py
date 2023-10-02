from datetime import timedelta

import pytest
from django.utils import timezone
from model_mommy import mommy

from iris_masters.models import District, RecordType, InputChannel, ApplicantType, Support
from main.test.mixins import FieldsTestSerializerMixin, UpperFieldsTestSerializerMixin
from record_cards.models import Citizen, SocialEntity
from record_cards.permissions import RESP_WORKED
from record_cards.tests.utils import CreateRecordCardMixin, FeaturesMixin
from reports.serializers import (QuequicomReportRequestSerializer, QuequicomReportSerializer, ReportsRequestSerializer,
                                 EntriesReportSerializer, ClosedRecordsReportSerializer,
                                 ReportRequestDatesLimitSerializer, ThemeRankingRequestSerializer,
                                 ThemesRankingSerializer, ApplicantsRecordCountRequestSerializer,
                                 ApplicantsRecordCountSerializer, RecordStateGroupsReportSerializer,
                                 OperatorsReportSerializer)
from themes.models import ThemeGroup, Area
from iris_masters.tests.utils import (load_missing_data_applicant, load_missing_data_support, load_missing_data_input,
                                      load_missing_data_districts)


@pytest.mark.django_db
class TestReportsRequestSerializer:

    @pytest.mark.parametrize("create_date_gte,create_date_lte,close_date_gte,close_date_lte,valid", (
            (True, True, True, True, True),
            (True, False, True, True, False),
            (False, False, True, True, True),
            (True, True, True, False, False),
            (True, True, False, True, False),
            (True, True, False, False, True),
    ))
    def test_reports_request_serializer_dates(self, create_date_gte, create_date_lte, close_date_gte, close_date_lte,
                                              valid):
        data = {}
        if create_date_gte:
            data["create_date_gte"] = (timezone.now() - timedelta(days=3)).date()
        if create_date_lte:
            data["create_date_lte"] = (timezone.now() + timedelta(days=3)).date()
        if close_date_gte:
            data["close_date_gte"] = (timezone.now() - timedelta(days=2)).date()
        if close_date_lte:
            data["close_date_lte"] = (timezone.now() + timedelta(days=2)).date()
        ser = ReportsRequestSerializer(data=data)
        assert ser.is_valid() is valid
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize("wrong_pks,valid", ((True, False), (False, True)))
    def test_reports_request_serializer_pks(self, wrong_pks, valid):
        load_missing_data_input()
        load_missing_data_applicant()
        load_missing_data_support()
        load_missing_data_districts()
        data = {
            "create_date_gte": timezone.now().date(),
            "create_date_lte": (timezone.now() + timedelta(days=5)).date(),
            "close_date_gte": timezone.now().date(),
            "close_date_lte": (timezone.now() + timedelta(days=5)).date(),
        }

        if wrong_pks:
            data["area_id"] = mommy.make(Area, user_id="222222")
            data["record_type_id"] = mommy.make(RecordType, user_id="222222")
        else:
            data["area_id"] = mommy.make(Area, user_id="222222").pk
            data["record_type_id"] = mommy.make(RecordType, user_id="222222").pk
        data["input_channel_id"] = InputChannel.QUIOSC
        data["applicant_type_id"] = ApplicantType.CIUTADA
        data["support_id"] = Support.ALTRES_MITJANS
        data["district_id"] = District.CIUTAT_VELLA
        data["neighborhood"] = "Gracia"

        ser = ReportsRequestSerializer(data=data)
        assert ser.is_valid() is valid
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestReportRequestDatesLimitSerializer:

    @pytest.mark.parametrize("create_limit_lte,close_date_limit,add_close_dates,valid", (
            (5, 5, True, True),
            (5, 5, False, True),
            (375, 5, True, False),
            (5, 375, True, False),
    ))
    def test_reports_request_dates_limit_serializer(self, create_limit_lte, close_date_limit, add_close_dates, valid):
        data = {
            "create_date_gte": timezone.now().date(),
            "create_date_lte": (timezone.now() + timedelta(days=create_limit_lte)).date(),
        }
        if add_close_dates:
            data["close_date_gte"] = timezone.now().date()
            data["close_date_lte"] = (timezone.now() + timedelta(days=close_date_limit)).date()
        ser = ReportRequestDatesLimitSerializer(data=data)
        assert ser.is_valid() is valid
        assert isinstance(ser.errors, dict)


class DatesLimitYearTestMixin:
    serializer_class = None

    def test_theme_ranking_request_serializer(self):
        data = {
            "create_date_gte": timezone.now().date(),
            "create_date_lte": timezone.now().date(),
            "close_date_gte": (timezone.now() + timedelta(days=375)).date(),
            "close_date_lte": (timezone.now() + timedelta(days=375)).date(),
        }
        assert self.serializer_class
        ser = self.serializer_class(data=data)
        assert ser.is_valid() is False
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestThemeRankingRequestSerializer(DatesLimitYearTestMixin):
    serializer_class = ThemeRankingRequestSerializer


@pytest.mark.django_db
class TestApplicantsRecordCountRequestSerializer(DatesLimitYearTestMixin):
    serializer_class = ApplicantsRecordCountRequestSerializer

    @pytest.mark.parametrize("applicant,min_requests,valid", (
            (None, None, True),
            (Citizen.CITIZEN_CHOICE, 5, True),
            (SocialEntity.SOCIAL_ENTITY_CHOICE, 2, True),
            (10, 1, False),
            (Citizen.CITIZEN_CHOICE, "a", False)))
    def test_applicants_record_count_request_serializer(self, applicant, min_requests, valid):
        data = {
            "create_date_gte": timezone.now().date(),
            "create_date_lte": timezone.now().date(),
            "close_date_gte": (timezone.now() + timedelta(days=10)).date(),
            "close_date_lte": (timezone.now() + timedelta(days=10)).date(),
        }

        if applicant:
            data["applicant"] = applicant
        if min_requests is not None:
            data["min_requests"] = min_requests

        assert self.serializer_class
        ser = self.serializer_class(data=data)
        assert ser.is_valid() is valid
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestQuequicomReportRequestSerializer:

    @pytest.mark.parametrize("add_dates,theme_group_ids,who,how,wrong_pks,valid", (
            (True, 2, True, False, False, True),
            (True, 2, False, True, False, True),
            (True, 0, True, False, False, True),
            (True, 2, True, False, True, False),
            (False, 2, True, False, False, False),
    ))
    def test_quequicom_report_serializer(self, add_dates, theme_group_ids, who, how, wrong_pks, valid):
        load_missing_data_input()
        load_missing_data_applicant()
        load_missing_data_support()
        load_missing_data_districts()
        data = {
            "who": who,
            "how": how
        }

        if add_dates:
            data.update({
                "create_date_gte": timezone.now().date(),
                "create_date_lte": (timezone.now() + timedelta(days=5)).date(),
                "close_date_gte": timezone.now().date(),
                "close_date_lte": (timezone.now() + timedelta(days=5)).date(),
            })

        # no required fields
        if theme_group_ids:
            data["theme_group_ids"] = [mommy.make(ThemeGroup, user_id="2222").pk for _ in range(theme_group_ids)]

        if wrong_pks:
            data["area_id"] = mommy.make(Area, user_id="222222")
            data["record_type_id"] = mommy.make(RecordType, user_id="222222")
        else:
            data["area_id"] = mommy.make(Area, user_id="222222").pk
            data["record_type_id"] = mommy.make(RecordType, user_id="222222").pk
        data["input_channel_id"] = InputChannel.QUIOSC
        data["applicant_type_id"] = ApplicantType.CIUTADA
        data["support_id"] = Support.ALTRES_MITJANS
        data["district_id"] = District.CIUTAT_VELLA
        data["neighborhood"] = "Gracia"

        ser = QuequicomReportRequestSerializer(data=data)
        assert ser.is_valid() is valid
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestQuequicomReportSerializer(FeaturesMixin, CreateRecordCardMixin, FieldsTestSerializerMixin):
    serializer_class = QuequicomReportSerializer
    data_keys = ["fitxa", "estat", "data_entrada", "hora_entrada", "data_tancament", "hora_tancament", "tipologia",
                 "area", "element", "detall", "especial", "canal_entrada", "tipus_solicitant", "suport",
                 "tipus_resposta", "proces", "usuari_validacio", "usuari_planificacio", "usuari_resolucio",
                 "usuari_tancament", "perfil_responsable", "tipus_via", "carrer", "numero", "lletra", "barri",
                 "districte", "posicio_x", "posicio_y", "sector_estadistic", "zona_recerca", "observacions",
                 "resposta_treballada", "comment_resol", "fitxa_pare", "resposta", "dies_oberta", "antiguitat",
                 "solicitant_id"]
    applicant_fields = ["solicitant_id"]

    def get_instance(self, features):
        return self.create_record_card(features=features)

    @pytest.mark.parametrize("who,create_features", (
            (True, True),
            (True, False),
            (False, True),
            (False, False)
    ))
    def test_serializer(self, who, create_features):
        features = self.create_features() if create_features else []

        group, request = self.set_group_request()
        self.set_group_permissions("222222", group, [RESP_WORKED])
        ser = self.get_serializer_class()(who, create_features, instance=self.get_instance(features),
                                          context={"request": request})
        if who and create_features:
            assert len(ser.data.keys()) == self.get_keys_number() + len(features) * 2
        elif who and not create_features:
            assert len(ser.data.keys()) == self.get_keys_number()
        elif not who and create_features:
            assert len(ser.data.keys()) == self.get_keys_number() - len(self.applicant_fields) + len(features) * 2
        else:
            assert len(ser.data.keys()) == self.get_keys_number() - len(self.applicant_fields)

        for data_key in self.data_keys:
            if not who and data_key in self.applicant_fields:
                continue
            assert data_key.upper() in ser.data, f"Required {data_key.upper()} not present in serializer data"
        if create_features:
            features_keys = ["ATRIBUT0", "VALOR0", "ATRIBUT1", "VALOR1", "ATRIBUT2", "VALOR2"]
            for feature_key in features_keys:
                assert feature_key in ser.data, f"Required {feature_key} not present in serializer data"

    @pytest.mark.parametrize("who", (True, False))
    def test_review_applicant_fields(self, who):
        _, request = self.set_group_request()
        ser = self.get_serializer_class()(who, False, instance=self.get_instance([]), context={"request": request})
        if who:
            for applicant_key in self.applicant_fields:
                assert applicant_key in ser.fields
        else:
            for applicant_key in self.applicant_fields:
                assert applicant_key not in ser.fields

    @pytest.mark.parametrize("add_permission", (True, False))
    def test_serializer_response_workec(self, add_permission):
        group, request = self.set_group_request()
        if add_permission:
            self.set_group_permissions("222222", group, [RESP_WORKED])
        features = self.create_features()
        ser = self.get_serializer_class()(True, True, instance=self.get_instance(features),
                                          context={"request": request})
        if add_permission:
            assert "RESPOSTA_TREBALLADA" in ser.data
        else:
            assert "RESPOSTA_TREBALLADA" not in ser.data


@pytest.mark.django_db
class TestEntriesReportSerializer(CreateRecordCardMixin, UpperFieldsTestSerializerMixin):
    serializer_class = EntriesReportSerializer
    data_keys = ["fitxa", "codi_process", "tipologia", "data_entrada", "element", "detall", "sector", "linia_servei",
                 "operador", "estat", "districte", "carrer"]

    def get_instance(self):
        return self.create_record_card()


@pytest.mark.django_db
class TestClosedRecordsReportSerializer(CreateRecordCardMixin, UpperFieldsTestSerializerMixin):
    serializer_class = ClosedRecordsReportSerializer
    data_keys = ["fitxa", "codi_process", "tipologia", "data_entrada", "data_tancament", "temps_resolucio",
                 "detall", "linia_servei", "operador", "districte", "carrer"]

    def get_instance(self):
        return self.create_record_card(closing_date=timezone.now())


@pytest.mark.django_db
class TestThemesRankingSerializer(FieldsTestSerializerMixin):
    serializer_class = ThemesRankingSerializer
    data_keys = ["element", "detall", "total", "percentage"]

    def get_instance(self):
        return {"element_description": "test", "detail_description": "test", "total": 0, "percentage": 0}


@pytest.mark.django_db
class TestApplicantsRecordCountSerializer(FieldsTestSerializerMixin):
    serializer_class = ApplicantsRecordCountSerializer
    data_keys = ["name", "document", "records"]

    def get_instance(self):
        return {"name": "test", "document": "47844521P", "records": 10}


@pytest.mark.django_db
class TestRecordStateGroupsReportSerializer(FieldsTestSerializerMixin):
    serializer_class = RecordStateGroupsReportSerializer
    data_keys = ["perfil_operador", "pendent_validar", "en_proces", "tancada", "cancelada", "tramitacio_externa",
                 "total", "percentatge"]

    def get_instance(self):
        return {"perfil_operador": "test", "pendent_validar": 2, "en_proces": 4, "tancada": 56, "cancelada": 9,
                "tramitacio_externa": 3, "total": 74, "percentatge": 65.9}


@pytest.mark.django_db
class TestOperatorsReportSerializer(UpperFieldsTestSerializerMixin):
    serializer_class = OperatorsReportSerializer
    data_keys = ["usuari_id", "validades", "tancades", "anulades", "reassignacions", "tramitades_externament",
                 "temps_mig_resposta"]

    def get_instance(self):
        return {"validated": 0, "closed": 0, "cancelled": 0, "external": 0, "reasignations": 0, "avg_response": 0,
                "user_id": "user_id"}
