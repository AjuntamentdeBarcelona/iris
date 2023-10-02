from bs4 import BeautifulSoup
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import empty

from iris_masters.models import (RecordType, InputChannel, ApplicantType, Support, District, Parameter, RecordState,
                                 ResponseChannel)
from main.api.serializers import UpperKeysMixin
from profiles.permissions import IrisPermissionChecker
from record_cards.models import RecordCard, Citizen, SocialEntity
from record_cards.permissions import RESP_WORKED
from reports.caches import QuequicomCache
from themes.models import ThemeGroup, Area, ElementDetailFeature


class ReportsRequestSerializer(serializers.Serializer):
    create_date_gte = serializers.DateField(required=False, label=_('Created at from'))  # desde
    create_date_lte = serializers.DateField(required=False, label=_('Created at to'))  # hasta
    close_date_gte = serializers.DateField(required=False, label=_('Closed at from'))  # desde
    close_date_lte = serializers.DateField(required=False, label=_('Closed at to'))  # hasta

    area_id = serializers.PrimaryKeyRelatedField(
        queryset=Area.objects.filter(**Area.ENABLED_AREA_FILTERS), required=False,
        error_messages={"does_not_exist": _("The selected record_type does not exist")}

    )
    record_type_id = serializers.PrimaryKeyRelatedField(
        queryset=RecordType.objects.all(), required=False,
        error_messages={"does_not_exist": _("The selected record_type does not exist")})
    input_channel_id = serializers.PrimaryKeyRelatedField(
        queryset=InputChannel.objects.all(), required=False,
        error_messages={"does_not_exist": _("The selected input_channel does not exist or is not enabled")})
    applicant_type_id = serializers.PrimaryKeyRelatedField(
        queryset=ApplicantType.objects.all(), required=False,
        error_messages={"does_not_exist": _("The selected applicant type does not exist or is not enabled")})
    support_id = serializers.PrimaryKeyRelatedField(
        queryset=Support.objects.all(), required=False,
        error_messages={"does_not_exist": _("The selected support does not exist or is not enabled")})
    district_id = serializers.PrimaryKeyRelatedField(
        queryset=District.objects.filter(allow_derivation=True), required=False,
        error_messages={"does_not_exist": _("The selected district does not exist or is not enabled")})
    neighborhood = serializers.CharField(required=False, max_length=80)

    def run_validation(self, data=empty):
        validated_data = super().run_validation(data)
        errors = {}

        if not validated_data.get("create_date_lte") and not validated_data.get("create_date_gte") and \
                not validated_data.get("close_date_lte") and not validated_data.get("close_date_gte"):
            error_message = _("A pair of dates is needed to filter records")
            errors["create_date_lte"] = error_message
            errors["create_date_gte"] = error_message
            errors["close_date_lte"] = error_message
            errors["close_date_gte"] = error_message

        self.check_dates_pair("create_date_lte", "create_date_gte", validated_data, errors)
        self.check_dates_pair("close_date_lte", "close_date_gte", validated_data, errors)

        if errors:
            raise ValidationError(errors, code="invalid")
        self.update_dates_to_datetime(validated_data)
        return validated_data

    @staticmethod
    def update_dates_to_datetime(validated_data):

        if "create_date_gte" in validated_data:
            create_date_gte = validated_data["create_date_gte"]
            validated_data["create_date_gte"] = timezone.datetime(create_date_gte.year, create_date_gte.month,
                                                                  create_date_gte.day)

        if "create_date_lte" in validated_data:
            create_date_lte = validated_data["create_date_lte"]
            validated_data["create_date_lte"] = timezone.datetime(create_date_lte.year, create_date_lte.month,
                                                                  create_date_lte.day, 23, 59, 59)

        if "close_date_gte" in validated_data:
            close_date_gte = validated_data["close_date_gte"]
            validated_data["close_date_gte"] = timezone.datetime(close_date_gte.year, close_date_gte.month,
                                                                 close_date_gte.day)

        if "close_date_lte" in validated_data:
            close_date_lte = validated_data["close_date_lte"]
            validated_data["close_date_lte"] = timezone.datetime(close_date_lte.year, close_date_lte.month,
                                                                 close_date_lte.day, 23, 59, 59)

    @staticmethod
    def check_dates_pair(last_date_key, initial_date_key, validated_data, errors):
        error_message = _("If {} is set, {} must be set too")
        if validated_data.get(last_date_key) and not validated_data.get(initial_date_key):
            errors[last_date_key] = error_message.format(last_date_key, initial_date_key)
            errors[initial_date_key] = error_message.format(last_date_key, initial_date_key)

        if validated_data.get(initial_date_key) and not validated_data.get(last_date_key):
            errors[initial_date_key] = error_message.format(initial_date_key, last_date_key)
            errors[last_date_key] = error_message.format(initial_date_key, last_date_key)


class DatesLimitMixin:
    @staticmethod
    def check_dates_limit(last_date_key, initial_date_key, validated_data, errors):
        days_limit = int(Parameter.get_parameter_by_key("REPORTS_DAYS_LIMITS", 366))
        last_date = validated_data.get(last_date_key)
        initial_date = validated_data.get(initial_date_key)

        if last_date and initial_date and (last_date - initial_date).days > days_limit:
            error_message = _("The difference between {} and {} can not be separated for more than {} days")
            errors[last_date_key] = error_message.format(last_date_key, initial_date_key, days_limit)
            errors[initial_date_key] = error_message.format(last_date_key, initial_date_key, days_limit)


class ReportRequestDatesLimitSerializer(DatesLimitMixin, ReportsRequestSerializer):

    def run_validation(self, data=empty):
        validated_data = super().run_validation(data)
        errors = {}

        self.check_dates_limit("create_date_lte", "create_date_gte", validated_data, errors)
        self.check_dates_limit("close_date_lte", "close_date_gte", validated_data, errors)

        if errors:
            raise ValidationError(errors, code="invalid")
        return validated_data


class DatesLimitYearMixin(DatesLimitMixin):
    def run_validation(self, data=empty):
        validated_data = super().run_validation(data)
        errors = {}

        close_date_lte = validated_data.get("close_date_lte")
        create_date_gte = validated_data.get("create_date_gte")
        if close_date_lte and create_date_gte:
            self.check_dates_limit("close_date_lte", "create_date_gte", validated_data, errors)
        if errors:
            raise ValidationError(errors, code="invalid")
        return validated_data


class ThemeRankingRequestSerializer(DatesLimitYearMixin, ReportRequestDatesLimitSerializer):
    pass


class ApplicantsRecordCountRequestSerializer(DatesLimitYearMixin, ReportRequestDatesLimitSerializer):
    applicant = serializers.ChoiceField(choices=[Citizen.CITIZEN_CHOICE, SocialEntity.SOCIAL_ENTITY_CHOICE],
                                        allow_null=True, required=False)
    min_requests = serializers.IntegerField(required=False, allow_null=True)


class QuequicomReportRequestSerializer(ReportsRequestSerializer):
    theme_group_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=ThemeGroup.objects.all(), required=False,
        error_messages={"does_not_exist": _("The selected theme group does not exists")})
    who = serializers.BooleanField(default=False)
    how = serializers.BooleanField(default=False)


class UbicationAttributeMixin:

    def get_ubication_attribute(self, record, attribute):
        return getattr(record.ubication, attribute, "") if record.ubication else ""


class QuequicomReportSerializer(UpperKeysMixin, UbicationAttributeMixin, serializers.ModelSerializer):
    fitxa = serializers.CharField(source="normalized_record_id", label=_('Record'))
    estat = serializers.SerializerMethodField(label=_('State'))
    data_entrada = serializers.SerializerMethodField(label=_('Creation date'))
    hora_entrada = serializers.SerializerMethodField(label=_('Creation hour'))
    data_tancament = serializers.SerializerMethodField(label=_('Closing date'))
    hora_tancament = serializers.SerializerMethodField(label=_('Entry hour'))
    tipologia = serializers.SerializerMethodField(label=_('Record type'))
    area = serializers.SerializerMethodField(label=_('Area'))
    element = serializers.CharField(source="element_detail.element.description", label=_('Element'))
    detall = serializers.CharField(source="element_detail.description", label=_('Elemet Detail'))
    especial = serializers.SerializerMethodField(label=_('Special'))
    canal_entrada = serializers.SerializerMethodField(label=_('Input channel'))
    tipus_solicitant = serializers.SerializerMethodField(label=_('Applicant type'))
    suport = serializers.SerializerMethodField(label=_('Support'))
    tipus_resposta = serializers.SerializerMethodField(label=_('Answer type'))
    proces = serializers.IntegerField(source="workflow_id", label=_('Workflow type'))
    usuari_validacio = serializers.SerializerMethodField(label=_('Validated by'))
    usuari_planificacio = serializers.SerializerMethodField(label=_('Planned by'))
    usuari_resolucio = serializers.SerializerMethodField(label=_('Solved by'))
    usuari_tancament = serializers.SerializerMethodField(label=_('Closed by'))
    perfil_responsable = serializers.SerializerMethodField(label=_('Responsible profile'))
    tipus_via = serializers.SerializerMethodField(label=_('Street type'))
    carrer = serializers.SerializerMethodField(label=_('Street'))
    numero = serializers.SerializerMethodField(label=_('Number'))
    lletra = serializers.SerializerMethodField(label=_('Block/Apartment'))
    barri = serializers.SerializerMethodField(label=_('Neighborhood'))
    districte = serializers.SerializerMethodField(label=_('District'))
    posicio_x = serializers.SerializerMethodField(label=_('Position X'))
    posicio_y = serializers.SerializerMethodField(label=_('Position Y'))
    sector_estadistic = serializers.SerializerMethodField(label=_('Stats sector'))
    zona_recerca = serializers.SerializerMethodField(label=_('Research Zone'))
    observacions = serializers.CharField(source="description", label=_('Observations'))
    resposta_treballada = serializers.SerializerMethodField(label=_('Answer worked?'))
    comment_resol = serializers.SerializerMethodField(label=_('Resolution Comment'))
    fitxa_pare = serializers.SerializerMethodField(label=_('Parent record'))
    resposta = serializers.SerializerMethodField(label=_('Answer'))
    dies_oberta = serializers.SerializerMethodField(label=_('Days opened'))
    antiguitat = serializers.SerializerMethodField(label=_('Days from creation'))
    solicitant_id = serializers.IntegerField(source="request.applicant_id", label=_('Applicant ID'))

    class Meta:
        model = RecordCard
        fields = ("fitxa", "estat", "data_entrada", "hora_entrada", "data_tancament", "hora_tancament", "tipologia",
                  "area", "element", "detall", "especial", "canal_entrada", "tipus_solicitant", "suport",
                  "tipus_resposta", "proces", "usuari_validacio", "usuari_planificacio", "usuari_resolucio",
                  "usuari_tancament", "perfil_responsable", "tipus_via", "carrer", "numero", "lletra", "barri",
                  "districte", "posicio_x", "posicio_y", "sector_estadistic", "zona_recerca", "observacions",
                  "resposta_treballada", "comment_resol", "fitxa_pare", "resposta", "dies_oberta", "antiguitat",
                  "solicitant_id")

    applicant_fields = ["solicitant_id"]
    response_channels = {
        ResponseChannel.EMAIL: "EMAIL",
        ResponseChannel.SMS: "SMS",
        ResponseChannel.NONE: "CAP",
        ResponseChannel.IMMEDIATE: "IMMEDIATA",
        ResponseChannel.TELEPHONE: "TELEFÒNIC",
        ResponseChannel.LETTER: "CARTA",
    }

    def __init__(self, who, how, instance=None, data=empty, **kwargs):
        self.who = who
        self.how = how
        self.record_features = 0
        super().__init__(instance, data, **kwargs)
        self.review_applicant_fields()
        self.review_worked_response_field()
        self.cache = QuequicomCache()

    def review_applicant_fields(self):
        """
        If who data are not required, pop applicant fields from serializer fields

        :return:
        """
        if not self.who:
            [self.fields.pop(applicant_field, None) for applicant_field in self.applicant_fields]

    def review_worked_response_field(self):
        """
        Check if user has permissions to see "resposta treaballada" column.
        If it has not permissions, the field is removed from the list of fields

        :return:
        """
        request = self.context.get("request")
        if request:
            if not IrisPermissionChecker.get_for_user(request.user).has_permission(RESP_WORKED):
                self.fields.pop("resposta_treballada", None)

    def get_estat(self, record):
        return self.cache.record_state_cache.get_item_description(record.record_state_id)

    def get_tipologia(self, record):
        return self.cache.record_type_cache.get_item_description(record.record_type_id)

    def get_data_entrada(self, record):
        return timezone.make_naive(record.created_at).date()

    def get_hora_entrada(self, record):
        return timezone.make_naive(record.created_at).strftime("%H:%M")

    def get_data_tancament(self, record):
        return timezone.make_naive(record.closing_date).date() if record.closing_date else ""

    def get_hora_tancament(self, record):
        return timezone.make_naive(record.closing_date).strftime("%H:%M") if record.closing_date else ""

    def get_area(self, record):
        return record.element_detail.element.area.description

    def get_especial(self, record):
        especial_features = record.recordcardspecialfeatures_set.filter(is_theme_feature=True)
        if especial_features:
            return self.get_related_feature_value(especial_features[0])
        else:
            return ""

    def get_canal_entrada(self, record):
        return self.cache.input_channel_cache.get_item_description(record.input_channel_id)

    def get_tipus_solicitant(self, record):
        return self.cache.applicant_type_cache.get_item_description(record.applicant_type_id)

    def get_suport(self, record):
        return self.cache.support_cache.get_item_description(record.support_id)

    def get_tipus_resposta(self, record):
        if not hasattr(record, "recordcardresponse"):
            return ""
        return self.response_channels.get(record.recordcardresponse.response_channel_id, "")

    def get_audit_field(self, record, audit_field):
        if hasattr(record, "recordcardaudit"):
            return getattr(record.recordcardaudit, audit_field)

    def get_usuari_validacio(self, record):
        return self.get_audit_field(record, "validation_user")

    def get_usuari_planificacio(self, record):
        return self.get_audit_field(record, "planif_user")

    def get_usuari_resolucio(self, record):
        return self.get_audit_field(record, "resol_user")

    def get_usuari_tancament(self, record):
        return self.get_audit_field(record, "close_user")

    def get_perfil_responsable(self, record):
        return record.responsible_profile.description

    def get_tipus_via(self, record):
        return self.get_ubication_attribute(record, "via_type")

    def get_carrer(self, record):
        return self.get_ubication_attribute(record, "official_street_name")

    def get_numero(self, record):
        return self.get_ubication_attribute(record, "street2")

    def get_lletra(self, record):
        return self.get_ubication_attribute(record, "letter")

    def get_barri(self, record):
        return self.get_ubication_attribute(record, "neighborhood")

    def get_districte(self, record):
        return record.ubication.district.name if record.ubication and record.ubication.district else ""

    def get_posicio_x(self, record):
        return self.get_ubication_attribute(record, "coordinate_x")

    def get_posicio_y(self, record):
        return self.get_ubication_attribute(record, "coordinate_y")

    def get_sector_estadistic(self, record):
        return self.get_ubication_attribute(record, "statistical_sector")

    def get_zona_recerca(self, record):
        return self.get_ubication_attribute(record, "research_zone")

    def get_comment_resol(self, record):
        return self.get_audit_field(record, "resol_comment")

    def get_fitxa_pare(self, record):
        return record.claimed_from.normalized_record_id if record.claimed_from else ""

    def get_resposta_treballada(self, record):
        text_responses = record.recordcardtextresponse_set.all()
        return text_responses[0].get_worked_display() if text_responses else ""

    def get_resposta(self, record):
        text_responses = record.recordcardtextresponse_set.all()
        if text_responses:
            return BeautifulSoup(text_responses[0].response, "html.parser").get_text()
        return ""

    def get_dies_oberta(self, record):
        if record.record_state_id in RecordState.CLOSED_STATES and record.closing_date:
            return (record.closing_date - record.created_at).days
        return ""

    def get_antiguitat(self, record):
        if record.record_state_id not in RecordState.CLOSED_STATES:
            return (timezone.now() - record.created_at).days
        return ""

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if self.how:
            self.record_features = 0
            queryset = ElementDetailFeature.objects.values("feature", "order").filter(
                element_detail=getattr(instance, "element_detail").id, enabled=True).order_by("order")
            record_features = instance.recordcardfeatures_set.filter(is_theme_feature=True)
            my_list = []
            feature_list = []
            for obj in record_features:
                feature_list.append(obj.feature_id)
            for item in queryset:
                if item['feature'] in feature_list:
                    my_list.append(item['feature'])
            objects = dict([(obj.feature_id, obj) for obj in record_features])
            sorted_objects = [objects[id] for id in my_list]

            self.add_feature_representation(representation, sorted_objects)
            # The first record_special_feature is shown in especial field
            record_special_features = instance.recordcardspecialfeatures_set.filter(is_theme_feature=True)[1:]
            my_list = []
            feature_list = []
            for obj in record_special_features:
                feature_list.append(obj.feature_id)
            for item in queryset:
                if item['feature'] in feature_list:
                    my_list.append(item['feature'])
            objects = dict([(obj.feature_id, obj) for obj in record_special_features])
            sorted_objects = [objects[id] for id in my_list]
            self.add_feature_representation(representation, sorted_objects)

        return representation

    def add_feature_representation(self, representation, record_features):
        for record_feature in record_features:
            attr_key = "ATRIBUT{}".format(self.record_features)
            representation[attr_key] = self.cache.features_cache.get_feature_description(record_feature.feature_id)
            representation["VALOR{}".format(self.record_features)] = self.get_related_feature_value(record_feature)
            self.record_features += 1

    def get_related_feature_value(self, related_feature):
        value = related_feature.value
        if self.cache.features_cache.get_values_type_id(related_feature.feature_id) == 0:
            return self.cache.values_cache.get_item_description(value)
        else:
            if not self.cache.features_cache.get_values_type_id(related_feature.feature_id):
                return value
            else:
                return self.cache.values_cache.get_item_description(value)


class EntriesReportSerializer(UpperKeysMixin, UbicationAttributeMixin, serializers.ModelSerializer):
    fitxa = serializers.CharField(source="normalized_record_id", label=_('Record'))
    codi_process = serializers.IntegerField(source="workflow_id", label=_('Workflow ID'))
    tipologia = serializers.CharField(source="record_type.description", label=_('Record type'))
    data_entrada = serializers.SerializerMethodField(label=_('Creation date'))
    element = serializers.CharField(source="element_detail.element.description", label=_('Element'))
    detall = serializers.CharField(source="element_detail.description", label=_('Elemet Detail'))
    sector = serializers.SerializerMethodField(label=_('Stats sector'))
    linia_servei = serializers.SerializerMethodField(label=_('Sevice line'))
    operador = serializers.SerializerMethodField(label=_('Operator'))
    estat = serializers.CharField(source="record_state.description", label=_('Record State'))
    districte = serializers.SerializerMethodField(label=_('District'))
    carrer = serializers.SerializerMethodField(label=_('Stret'))

    class Meta:
        model = RecordCard
        fields = ("fitxa", "codi_process", "tipologia", "data_entrada", "element", "detall", "sector", "linia_servei",
                  "operador", "estat", "districte", "carrer")

    def get_data_entrada(self, record):
        return record.created_at.date()

    def get_sector(self, record):
        if record.responsible_profile and record.responsible_profile.ambit_coordinator:
            return record.responsible_profile.ambit_coordinator.description
        return ""

    def get_linia_servei(self, record):
        return record.responsible_profile.profile_ctrl_user_id if record.responsible_profile else ""

    def get_operador(self, record):
        return record.responsible_profile.description if record.responsible_profile else ""

    def get_districte(self, record):
        return record.ubication.district.name if record.ubication and record.ubication.district else ""

    def get_carrer(self, record):
        return self.get_ubication_attribute(record, "street")


class ClosedRecordsReportSerializer(EntriesReportSerializer):
    data_tancament = serializers.SerializerMethodField(label=_('Closing date'))
    temps_resolucio = serializers.SerializerMethodField(label=_('Resolution time'))

    class Meta:
        model = RecordCard
        fields = ("fitxa", "codi_process", "tipologia", "data_entrada", "data_tancament", "temps_resolucio",
                  "detall", "linia_servei", "operador", "districte", "carrer")

    def get_data_tancament(self, record):
        return record.closing_date.date()

    def get_temps_resolucio(self, record):
        resol_time = record.closing_date - record.created_at
        day_seconds = 3600 * 24

        resol_time = resol_time.days + round(resol_time.seconds / day_seconds, 2)
        return resol_time if resol_time > 0 else 0


class ThemesRankingSerializer(serializers.Serializer):
    element = serializers.SerializerMethodField(label=_('Element'))
    detall = serializers.SerializerMethodField(label=_('Element Detail'))

    def __init__(self, instance=None, data=empty, **kwargs):
        self.month_keys = kwargs.pop("month_keys_list", [])
        super().__init__(instance, data, **kwargs)

    def get_element(self, record):
        return record["element_description"]

    def get_detall(self, record):
        return record["detail_description"]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        for month_key in self.month_keys:
            representation[month_key] = instance.get(month_key, 0)
        representation["total"] = instance.get("total", 0)
        representation["percentage"] = instance.get("percentage", 0)
        return representation


class ApplicantsRecordCountSerializer(serializers.Serializer):
    name = serializers.SerializerMethodField(label=_('Name'))
    document = serializers.SerializerMethodField(label=_('ID Card'))
    records = serializers.SerializerMethodField(label=_('Records'))

    def get_name(self, record):
        return record["name"]

    def get_document(self, record):
        return record["document"]

    def get_records(self, record):
        return record["records"]


class RecordStateGroupsReportSerializer(serializers.Serializer):
    perfil_operador = serializers.CharField(max_length=100, label=_('Operator profile'))
    pendent_validar = serializers.IntegerField(label=_('Pending to validate'))
    en_proces = serializers.IntegerField(label=_('In progress'))
    tancada = serializers.IntegerField(label=_('Closed'))
    cancelada = serializers.IntegerField(label=_('Cancelled'))
    tramitacio_externa = serializers.IntegerField(label=_('External'))
    total = serializers.IntegerField(label=_('Total'))
    percentatge = serializers.FloatField(label=_('Percentage'))

    class Meta:
        read_only_fields = ("perfil_operador", "pendent_validar", "en_proces", "tancada", "cancelada",
                            "tramitacio_externa", "total", "percentatge")


class AccessLogRequestSerializer(serializers.Serializer):
    from_date = serializers.DateField(label=_('From date'))  # desde
    to_date = serializers.DateField(label=_('To date'))  # hasta

    class Meta:
        fields = ("from_date", "to_date")


class AccessLogSerializer(serializers.Serializer):
    username = serializers.CharField(label=_('Username'))
    sector = serializers.CharField(label=_('Stat sector'))
    linia_servei = serializers.CharField(label=_('Service line'))
    operador = serializers.CharField(label=_('Operator'))
    count = serializers.IntegerField(label=_('Count'))

    class Meta:
        fields = ("from_date", "to_date")


class OperatorsReportSerializer(UpperKeysMixin, serializers.Serializer):
    usuari_id = serializers.SerializerMethodField(label=_('User id'))
    validades = serializers.SerializerMethodField(label=_('Validated'))
    tancades = serializers.SerializerMethodField(label=_('Closed'))
    anulades = serializers.SerializerMethodField(label=_('Cancelled'))
    reassignacions = serializers.SerializerMethodField(label=_('Reassigned'))
    tramitades_externament = serializers.SerializerMethodField(label=_('External'))
    temps_mig_resposta = serializers.SerializerMethodField(label=_('AVG Answer time'))

    def get_usuari_id(self, register):
        return register["user_id"]

    def get_validades(self, register):
        return register["validated"]

    def get_tancades(self, register):
        return register["closed"]

    def get_anulades(self, register):
        return register["cancelled"]

    def get_reassignacions(self, register):
        return register["reasignations"]

    def get_tramitades_externament(self, register):
        return register["external"]

    def get_temps_mig_resposta(self, register):
        return register["avg_response"]
