import logging
from datetime import date, timedelta
from functools import reduce

from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters

from ariadna.models import AriadnaRecord
from features.models import Feature
from iris_masters.models import (RecordState, ApplicantType, Support, InputChannel, ResponseChannel, District,
                                 RecordType)
from main.api.filters import UnaccentLookupChoiceFilter
from profiles.models import Group
from record_cards.models import (Applicant, RecordCard, Workflow, RecordCardFeatures, RecordCardSpecialFeatures,
                                 Ubication)
from themes.models import Area, Element, ElementDetail, ThemeGroup


logger = logging.getLogger(__name__)


class RecordCardFilter(filters.FilterSet):
    # ModelMultipleChoice filters
    area = filters.ModelMultipleChoiceFilter(field_name="element_detail__element__area_id", distinct=False,
                                             queryset=Area.objects.filter(**Area.ENABLED_AREA_FILTERS))
    element = filters.ModelMultipleChoiceFilter(field_name="element_detail__element_id", distinct=False,
                                                queryset=Element.objects.filter(**Element.ENABLED_ELEMENT_FILTERS))
    elementdetail = filters.ModelMultipleChoiceFilter(field_name="element_detail_id", distinct=False,
                                                      queryset=ElementDetail.objects.filter(
                                                          **ElementDetail.ENABLED_ELEMENTDETAIL_FILTERS))
    state = filters.ModelMultipleChoiceFilter(field_name="record_state_id", distinct=False,
                                              queryset=RecordState.objects.filter(enabled=True))

    # ModelChoice filters
    applicant_type = filters.ModelChoiceFilter(field_name="applicant_type_id",
                                               queryset=ApplicantType.objects.all())
    input_channel = filters.ModelChoiceFilter(field_name="input_channel_id",
                                              queryset=InputChannel.objects.all())
    response_channel = filters.ModelChoiceFilter(method="filter_response_channel",
                                                 queryset=ResponseChannel.objects.filter(enabled=True))
    feature = filters.ModelChoiceFilter(method="filter_feature", queryset=Feature.objects.all())
    theme_group = filters.ModelChoiceFilter(method="filter_theme_group", queryset=ThemeGroup.objects.all())
    support = filters.ModelChoiceFilter(field_name="support_id", queryset=Support.objects.all())
    record_type = filters.ModelChoiceFilter(field_name="record_type_id", queryset=RecordType.objects.all())

    # boolean filters
    urgent = filters.BooleanFilter(method="filter_urgent")
    alarm = filters.BooleanFilter(field_name="alarm")
    pend_citizen_response = filters.BooleanFilter(field_name="pend_applicant_response")
    response_time_expired = filters.BooleanFilter(field_name="response_time_expired")
    citizen_response = filters.BooleanFilter(field_name="applicant_response")
    related_records = filters.BooleanFilter(field_name="similar_process")
    reasigned_task = filters.BooleanFilter(field_name="reasigned")
    cancel_request = filters.BooleanFilter(field_name="cancel_request")
    possible_similar_records = filters.BooleanFilter(field_name="possible_similar_records")
    citizen_claim = filters.BooleanFilter(field_name="citizen_alarm")
    citizen_web_claim = filters.BooleanFilter(field_name="citizen_web_alarm")
    response_to_responsible = filters.BooleanFilter(method="filter_response_to_responsible")
    pend_response_responsible = filters.BooleanFilter(method="filter_pend_response_responsible")
    processing = filters.BooleanFilter(method="filter_processing")
    expired = filters.BooleanFilter(method="filter_expired")
    near_expire = filters.BooleanFilter(method="filter_near_expire")
    open_records = filters.BooleanFilter(method="filter_open_records")
    mayorship = filters.BooleanFilter(field_name="mayorship")
    active_claims = filters.BooleanFilter(method="filter_active_claims")
    has_communication_media = filters.BooleanFilter(method="filter_has_communication_media")

    # applicant filters
    applicant_name = UnaccentLookupChoiceFilter(label=_("Applicant Name"),
                                                field_name="request__applicant__citizen__name",
                                                lookup_choices=[("iexact", "Equals"), ("icontains", "Contains"),
                                                                ("istartswith", "Start With"),
                                                                ("ilike_contains", "Ilike contains")])
    applicant_surname = UnaccentLookupChoiceFilter(label=_("Applicant Surname"),
                                                   field_name="request__applicant__citizen__first_surname",
                                                   lookup_choices=[("iexact", "Equals"), ("icontains", "Contains"),
                                                                   ("istartswith", "Start With"),
                                                                   ("ilike_contains", "Ilike contains")])
    applicant_second_surname = UnaccentLookupChoiceFilter(label=_("Applicant Second Surname"),
                                                          lookup_expr="ilike_contains",
                                                          field_name="request__applicant__citizen__second_surname")
    applicant_social_reason = UnaccentLookupChoiceFilter(label=_("Applicant Social Reason"),
                                                         field_name="request__applicant__social_entity__social_reason",
                                                         lookup_choices=[("iexact", "Equals"),
                                                                         ("icontains", "Contains"),
                                                                         ("istartswith", "Start With"),
                                                                         ("ilike_contains", "Ilike contains")])
    applicant_dni = filters.LookupChoiceFilter(label=_("Applicant DNI"), method="filter_applicant_dni",
                                               lookup_choices=[
                                                   ("exact", "Equals"), ("contains", "Contains"),
                                                   ("startswith", "startswith")
                                               ])
    applicant_cif = filters.LookupChoiceFilter(label=_("Applicant CIF"), method="filter_applicant_cif",
                                               lookup_choices=[("exact", "Equals"), ("contains", "Contains")])

    applicant_address_response = filters.CharFilter(label=_("Applicant Address Response"),
                                                    method="filter_applicant_address_response")
    applicant_phone_response = filters.CharFilter(label=_("Applicant Phone Response"),
                                                  method="filter_applicant_phone_response")
    applicant_email_response = filters.CharFilter(label=_("Applicant Email Response"),
                                                  method="filter_applicant_email_response")
    # date filters
    created_at_ini = filters.DateFilter(label=_("Created at init"), field_name="created_at", lookup_expr="gte")
    created_at_end = filters.DateFilter(label=_("Created at end"), method="filter_created_at_end")
    closing_date_ini = filters.DateFilter(label=_("Closing date init"), field_name="closing_date", lookup_expr="gte")
    closing_date_end = filters.DateFilter(label=_("Closing date end"), method="filter_closing_date_end")
    ans_limit_date_ini = filters.NumberFilter(label=_("Ans limit date at init"), method="filter_ans_limit_date_ini")
    ans_limit_date_end = filters.NumberFilter(label=_("Ans limit date at end"), method="filter_ans_limit_date_end")

    # groups filters
    responsible_profile = filters.CharFilter(label=_("Responsible Profile Description"),
                                             lookup_expr="unaccent__ilike_contains",
                                             field_name="responsible_profile__description")
    responsible_profile_id = filters.ModelChoiceFilter(label=_("Responsible Profile Description"),
                                                       queryset=Group.objects.filter(deleted__isnull=True))
    creation_profile = filters.ModelChoiceFilter(label=_("Creation Profile"), method="filter_creation_profile",
                                                 queryset=Group.objects.filter(deleted__isnull=True))
    incharge_profile = filters.ModelChoiceFilter(label=_("Incharge Profile"), field_name="responsible_profile_id",
                                                 queryset=Group.objects.filter(deleted__isnull=True))
    advanced_profile = filters.ModelChoiceFilter(label=_("Advanced Responsible Profile"),
                                                 method="filter_advanced_profile",
                                                 queryset=Group.objects.filter(deleted__isnull=True))

    user_id = filters.Filter(label=_("User id"), field_name="user_id", lookup_expr="ilike_contains")
    normalized_record_id = filters.LookupChoiceFilter(label=_("Normalized record id contains"),
                                                      method="filter_normalized_record_id",
                                                      lookup_choices=[("iexact", "iEquals"),
                                                                      ("exact", "Equals"),
                                                                      ("icontains", "iContains"),
                                                                      ("contains", "Contains"),
                                                                      ("istartswith", "iStart With"),
                                                                      ("startswith", "Start With"),
                                                                      ("ilike_contains", "Ilike contains")])
    # ubication filters
    district = filters.ModelMultipleChoiceFilter(field_name="ubication__district_id", queryset=District.objects.all(),
                                                 distinct=False)
    null_ubication = filters.BooleanFilter(field_name="ubication__street", lookup_expr='isnull')
    neighborhood = filters.Filter(label=_("Neighborhood"), field_name="ubication__neighborhood",
                                  lookup_expr="unaccent__ilike_contains")

    # operator filters
    create_operator = filters.CharFilter(label=_("Create operator"), method="filter_create_operator")
    validate_operator = filters.CharFilter(label=_("Validate operator"), method="filter_validate_operator")
    plan_operator = filters.CharFilter(label=_("Plan operator"), method="filter_plan_operator")
    resolute_operator = filters.CharFilter(label=_("Resolute operator"), method="filter_resolute_operator")
    close_operator = filters.CharFilter(label=_("Close operator"), method="filter_close_operator")
    reasigned_records = filters.CharFilter(method="filter_reasigned_records")

    # ariadna_filter
    ariadna_record = filters.CharFilter(label=_("Ariadna Record"), method="filter_ariadna_record")

    class Meta:
        model = RecordCard
        fields = ("area", "element", "elementdetail", "state", "applicant_type", "input_channel", "response_channel",
                  "feature", "theme_group", "support", "record_type", "urgent", "alarm", "active_claims",
                  "processing", "expired", "near_expire", "open_records", "mayorship", "applicant_name",
                  "applicant_surname", "applicant_second_surname", "applicant_social_reason", "applicant_dni",
                  "applicant_cif", "applicant_address_response", "applicant_phone_response", "applicant_email_response",
                  "created_at_ini", "created_at_end", "closing_date_ini", "closing_date_end", "ans_limit_date_ini",
                  "ans_limit_date_end", "responsible_profile", "creation_profile", "user_id", "normalized_record_id",
                  "district", "neighborhood", "create_operator", "validate_operator", "plan_operator",
                  "resolute_operator", "close_operator", "reasigned_records", "ariadna_record",
                  "has_communication_media", "communication_media_id",)

    def __init__(self, data=None, queryset=None, *, request=None, prefix=None):
        self.user_group = request.user.usergroup.group if request and hasattr(request.user, "usergroup") else None
        super().__init__(data, queryset, request=request, prefix=prefix)

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        queryset = self.filter_features_values(queryset)
        queryset = self.filter_streets(queryset)
        return queryset

    def filter_created_at_end(self, queryset, name, value):
        # As the value is a Date and its is compared with a datetime, the lookup __lte is not usefull.
        # For that reason, we use lt and add a day to the comparision value
        date_limit = value + timedelta(days=1)
        return queryset.filter(created_at__lt=date_limit)

    def filter_closing_date_end(self, queryset, name, value):
        # As the value is a Date and its is compared with a datetime, the lookup __lte is not usefull.
        # For that reason, we use lt and add a day to the comparision value
        date_limit = value + timedelta(days=1)
        return queryset.filter(closing_date__lt=date_limit)

    def filter_ans_limit_date_ini(self, queryset, name, value):
        date_limit = timezone.localdate() + timezone.timedelta(days=int(value))
        return queryset.filter(ans_limit_date__gte=date_limit)

    def filter_ans_limit_date_end(self, queryset, name, value):
        # As the value is a Date and its is compared with a datetime, the lookup __lte is not usefull.
        # For that reason, we use lt and add a day to the comparision value
        date_limit = timezone.localdate() + timezone.timedelta(days=int(value) + 1)
        return queryset.filter(ans_limit_date__lt=date_limit)

    def filter_creation_profile(self, queryset, name, value):
        return queryset.filter(creation_group_id=value)

    def filter_advanced_profile(self, queryset, name, value):
        group_ids = value.get_descendants(include_self=True, include_deleted=True).values_list("pk", flat=True)
        return queryset.filter(responsible_profile__in=group_ids)

    def filter_urgent(self, queryset, name, value):
        return queryset.filter(urgent=value).exclude(
            Q(record_state_id=RecordState.CLOSED) | Q(record_state_id=RecordState.CANCELLED))

    def filter_response_to_responsible(self, queryset, name, value):
        kwargs_params = {"responsible_profile": self.user_group, "response_to_responsible": True}
        return queryset.filter(**kwargs_params) if value else queryset.exclude(**kwargs_params)

    def filter_pend_response_responsible(self, queryset, name, value):
        kwargs_params = {"responsible_profile": self.user_group, "pend_response_responsible": True}
        return queryset.filter(**kwargs_params) if value else queryset.exclude(**kwargs_params)

    def filter_processing(self, queryset, name, value):
        if value:
            return queryset.filter(record_state_id__in=RecordState.STATES_IN_PROCESSING)
        return queryset.exclude(record_state_id__in=RecordState.STATES_IN_PROCESSING)

    def filter_expired(self, queryset, name, value):
        if value:
            return queryset.filter(ans_limit_date__lt=date.today()).exclude(
                record_state_id__in=RecordState.CLOSED_STATES)
        return queryset

    def filter_near_expire(self, queryset, name, value):
        if value:
            return queryset.near_to_expire_records()
        return queryset

    def filter_normalized_record_id(self, queryset, name, value):
        return queryset.filter(**{f"normalized_record_id__{value.lookup_expr}": value.value.upper()})

    def filter_applicant_dni(self, queryset, name, value):
        return queryset.filter(
            **{"request__applicant__citizen__dni__startswith": value.value.upper()})

    def filter_applicant_cif(self, queryset, name, value):
        return queryset.filter(
            **{"request__applicant__social_entity__cif__startswith": value.value.upper()})

    def base_filter_applicant_response(self, queryset, value, response_channel_ids):
        kwargs = {
            "recordcardresponse__enabled": True,
            "recordcardresponse__response_channel_id__in": response_channel_ids
        }
        if ResponseChannel.LETTER in response_channel_ids:
            kwargs["recordcardresponse__address_mobile_email__unaccent__startswith"] = value
        else:
            kwargs["recordcardresponse__address_mobile_email__startswith"] = value

        return queryset.filter(**kwargs)

    def filter_applicant_address_response(self, queryset, name, value):
        return self.base_filter_applicant_response(queryset, value, [ResponseChannel.LETTER])

    def filter_applicant_phone_response(self, queryset, name, value):
        return self.base_filter_applicant_response(queryset, value, [ResponseChannel.SMS, ResponseChannel.TELEPHONE])

    def filter_applicant_email_response(self, queryset, name, value):
        return self.base_filter_applicant_response(queryset, value, [ResponseChannel.EMAIL])

    def filter_open_records(self, queryset, name, value):
        if not self.user_group:
            return RecordCard.objects.none()
        # If this filter is used, filter the RecordCard associated to the user profile
        queryset = queryset.filter(responsible_profile__group_plate__startswith=self.user_group.group_plate)

        if not value:
            return queryset.filter(record_state_id__in=RecordState.CLOSED_STATES)

        return queryset.filter(record_state_id__in=RecordState.OPEN_STATES)

    def filter_active_claims(self, queryset, name, value):
        if not value:
            return queryset.exclude(citizen_alarm=True, record_state_id__in=RecordState.OPEN_STATES)
        return queryset.filter(citizen_alarm=True, record_state_id__in=RecordState.OPEN_STATES)

    def filter_has_communication_media(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(communication_media__isnull=False)

    def filter_theme_group(self, queryset, name, value):
        element_detail_pks = value.elementdetail_set.filter(deleted__isnull=True, element__deleted__isnull=True,
                                                            element__area__deleted__isnull=True)
        return queryset.filter(element_detail_id__in=element_detail_pks)

    def filter_response_channel(self, queryset, name, value):
        return queryset.filter(recordcardresponse__response_channel_id=value.pk)

    def filter_feature(self, queryset, name, value):
        feature_records_pks = RecordCardFeatures.objects.filter(feature=value, enabled=True).values_list(
            "record_card_id", flat=True)
        special_feature_records_pks = RecordCardSpecialFeatures.objects.filter(
            feature=value, enabled=True).values_list("record_card_id", flat=True)
        record_card_pks = feature_records_pks.union(special_feature_records_pks)
        return queryset.filter(pk__in=record_card_pks)

    def filter_create_operator(self, queryset, name, value):
        return queryset.filter(user_id__startswith=value.upper())

    def filter_validate_operator(self, queryset, name, value):
        return queryset.filter(recordcardaudit__validation_user__startswith=value.upper())

    def filter_close_operator(self, queryset, name, value):
        return queryset.filter(recordcardaudit__close_user__startswith=value.upper())

    def filter_plan_operator(self, queryset, name, value):
        return queryset.filter(recordcardaudit__planif_user__startswith=value.upper())

    def filter_resolute_operator(self, queryset, name, value):
        return queryset.filter(recordcardaudit__resol_user__startswith=value.upper())

    def filter_reasigned_records(self, queryset, name, value):
        return queryset.filter(recordcardreasignation__user_id__startswith=value.upper()).distinct()

    def filter_ariadna_record(self, queryset, name, value):
        record_card_pks = AriadnaRecord.objects.filter(code__exact=value).values_list("record_card_id", flat=True)
        return queryset.filter(pk__in=record_card_pks)

    def filter_features_values(self, queryset):
        feature_base_key = "feature_"
        value_base_key = "value_{}"
        value_base_lookup = "valueic_{}"

        features_keys = [data_key for data_key, value in self.request.GET.items() if feature_base_key in data_key]
        for feature_key in features_keys:
            feature_number = feature_key.split(feature_base_key)[1]

            feature_pk = self.request.GET.get(feature_key)
            value = self.request.GET.get(value_base_key.format(feature_number))
            if value:
                value_lookup = {"value": value}
            else:
                value = self.request.GET.get(value_base_lookup.format(feature_number), "")
                value_lookup = {"value__ilike_contains": value}

            if feature_pk and value:
                feature_records_pks = RecordCardFeatures.objects.filter(
                    feature_id=feature_pk, enabled=True, **value_lookup).values_list("record_card_id", flat=True)
                special_feature_records_pks = RecordCardSpecialFeatures.objects.filter(
                    feature_id=feature_pk, enabled=True, value=value).values_list("record_card_id", flat=True)
                record_card_pks = feature_records_pks.union(special_feature_records_pks)
                queryset = queryset.filter(pk__in=record_card_pks)

        return queryset

    def filter_streets(self, queryset):
        street_base_key = "street_"
        number_base_key = "number_{}"

        street_params = {data_key: value for data_key, value in self.request.GET.items() if street_base_key in data_key}
        ubication_ids = []
        for street_key, street_value in street_params.items():
            street_number = street_key.split(street_base_key)[1]
            number_value = self.request.GET.get(number_base_key.format(street_number))
            if number_value:
                number_filter = self._streets_numbers_filter(number_value)
                ubication_ids += Ubication.objects.filter(
                    number_filter, street__unaccent__iexact=street_value
                ).values_list("id", flat=True).distinct("id")
            else:
                ubication_ids += Ubication.objects.filter(
                    street__unaccent__iexact=street_value).values_list("id", flat=True).distinct("id")
        if street_params:
            queryset = queryset.filter(ubication_id__in=ubication_ids)
        return queryset

    def _streets_numbers_filter(self, number_value):
        if "-" not in number_value:
            return Q(street2__unaccent__iexact=number_value.zfill(4))

        try:
            interval = number_value.split("-")
            lower_limit = interval[0].strip()
            higher_limit = interval[1].strip()
            return reduce(
                lambda previous, x: previous | Q(street2__unaccent__iexact=str(x).zfill(4)),
                range(int(lower_limit), int(higher_limit)+1),
                Q()
            )
        except Exception:
            logger.info(f'RECORDFILTERS | STREET NUMBERS ERROR | {number_value}')
            return Q()


class WorkflowFilter(filters.FilterSet):
    normalized_record_id = filters.Filter(field_name="normalized_record_id", method="filter_normalized_record_id")
    applicant_identifier = filters.Filter(label=_(u"Applicant Identifier"), method="filter_applicant_identifier")

    class Meta:
        model = Workflow
        fields = ("normalized_record_id", "applicant_identifier")

    def filter_normalized_record_id(self, queryset, name, value):
        workflow_pks = RecordCard.objects.filter(
            normalized_record_id=value, workflow__isnull=False).values_list("workflow_id", flat=True)
        return queryset.filter(pk__in=workflow_pks)

    def filter_applicant_identifier(self, queryset, name, value):
        workflow_pks = RecordCard.objects.filter(
            Q(request__applicant__citizen__dni__exact=value.upper()) |
            Q(request__applicant__social_entity__cif__exact=value.upper()),
            workflow__isnull=False
        ).values_list("workflow_id", flat=True)
        return queryset.filter(pk__in=workflow_pks)


class ApplicantFilter(filters.FilterSet):
    applicant_type = filters.Filter(field_name="applicant_type", label="tipus de sol·licitant",
                                    method="filter_applicant_type")
    dni = filters.CharFilter(field_name="citizen__dni", label=_("DNI"), method="filter_upper_startwith")
    dni__exact = filters.Filter(field_name="citizen__dni", label=_("DNI"), lookup_expr="exact")
    name = filters.Filter(field_name="citizen__name", label=_("Name"), lookup_expr="unaccent__ilike_contains")
    first_surname = filters.Filter(field_name="citizen__first_surname", label=_("First Surname"),
                                   lookup_expr="unaccent__ilike_contains")
    second_surname = filters.Filter(field_name="citizen__second_surname", label=_("Second Surname"),
                                    lookup_expr="unaccent__ilike_contains")
    full_normalized_name = filters.Filter(
        field_name="citizen__full_normalized_name", label=_("Full name"), lookup_expr="unaccent__ilike_contains"
    )

    cif = filters.CharFilter(field_name="social_entity__cif", label=_("CIF"), method="filter_upper_startwith")
    cif__exact = filters.Filter(field_name="social_entity__cif", label=_("CIF"), lookup_expr="exact")
    social_reason = filters.Filter(field_name="social_entity__social_reason", label=_("Raó social"),
                                   lookup_expr="unaccent__ilike_contains")
    pend_anonymize = filters.BooleanFilter(field_name="pend_anonymize")

    class Meta:
        model = Applicant
        fields = ("applicant_type", "dni", "name", "first_surname", "second_surname", "full_normalized_name",
                  "cif", "social_reason", "dni__exact", "pend_anonymize")

    def filter_applicant_type(self, queryset, name, value):
        if value == "citizen":
            return queryset.filter(citizen__isnull=False)
        elif value == "social_entity":
            return queryset.filter(social_entity__isnull=False)
        else:
            return queryset

    def filter_upper_startwith(self, queryset, name, value):
        return queryset.filter(**{"{}__startswith".format(name): value.upper()})
