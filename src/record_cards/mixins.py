from copy import deepcopy
from datetime import date

from django.db.models import Count, Q, Prefetch
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from excel_export.mixins import ExcelExportListMixin
from iris_masters.models import RecordState
from profiles.permissions import IrisPermission
from record_cards.models import RecordCard, RecordCardSpecialFeatures, RecordCardTextResponse
from record_cards.permissions import MAYORSHIP
from record_cards.record_actions.group_response_messages import GroupCanResponseMessages
from record_cards.serializers import RecordCardExportSerializer
from main.utils import get_user_traceability_id


class RecordCardResponsibleProfileMixin:

    def get_queryset(self):
        if not hasattr(self.request.user, 'usergroup'):
            return RecordCard.objects.none()

        queryset = super().get_queryset()
        return self.filter_queryset_by_group_plate(queryset)

    def filter_queryset_by_group_plate(self, queryset):
        user_group = self.request.user.usergroup.group
        queryset = queryset.filter(responsible_profile__group_plate__startswith=user_group.group_plate)
        return queryset


class SetRecordStateHistoryMixin:

    @staticmethod
    def set_record_state_history(record_card, next_state_code, user, previous_state_code=None, group=None,
                                 automatic=False):
        """
        Set the recordStateHistory register for a state change on a RecordCard calling the model method
        :param record_card: RecordCard which state has changed
        :param next_state_code: new state code
        :param user: user of the request
        :param previous_state_code: optional previous state code
        :param group: optional group
        :param automatic: set to True if the state change has been done automatically
        :return:
        """
        record_card.set_record_state_history(next_state_code, user, previous_state_code, group, automatic)


class RecordCardRestrictedConversationPermissionsMixin:
    """
    Mixin to check if a group can do RecordCard action becasue:
    - mayorship permissions or unread conversation message
    - can tramit record card or unread conversation message
    """

    def group_is_allowed(self, user_group, instance):
        """
        Check if user's groups is allowed to read all the information of the RecordCard or not
        If record is set to mayorship, if group has mayorship permission or has an unread message,
        group can see all information
        If usergroup can tramit record card or has an unread message can see all information

        :param user_group: Group assigned to the user
        :param instance: Object to retrieve
        :return: True if user's group has permissions to see all data of recordCard, else False
        """
        if user_group:
            if instance.mayorship:
                return MAYORSHIP in user_group.group_permissions_codes or \
                       self.can_response_messages(instance, user_group)
            else:
                can_tramit = instance.group_can_tramit_record(user_group)
                return can_tramit or self.can_response_messages(instance, user_group)
        else:
            return False

    def can_response_messages(self, instance, user_group):
        return GroupCanResponseMessages(instance, user_group).can_response_messages()


class RecordCardIndicatorsMixin:

    @staticmethod
    def get_entries_counter(year, month, group):
        return Count("responsible_profile", filter=Q(recordcardreasignation__created_at__year=year,
                                                     recordcardreasignation__created_at__month=month,
                                                     recordcardreasignation__next_responsible_profile=group))

    @staticmethod
    def get_pending_validate_counter():
        return Count("responsible_profile", filter=Q(record_state_id__in=RecordState.PEND_VALIDATE_STATES))

    @staticmethod
    def get_processing_counter():
        return Count("responsible_profile", filter=Q(record_state_id__in=RecordState.STATES_IN_PROCESSING))

    @staticmethod
    def get_closed_counter():
        return Count("responsible_profile", filter=Q(record_state_id=RecordState.CLOSED))

    @staticmethod
    def get_cancelled_counter():
        return Count("responsible_profile", filter=Q(record_state_id=RecordState.CANCELLED))

    @staticmethod
    def get_external_processing_counter():
        return Count("responsible_profile", filter=Q(record_state_id=RecordState.EXTERNAL_PROCESSING))

    @staticmethod
    def get_pending_counter():
        return Count("responsible_profile", filter=Q(
            record_state_id__in=RecordState.STATES_IN_PROCESSING + RecordState.PEND_VALIDATE_STATES
        ))

    @staticmethod
    def get_expired_counter():
        expired_filter = Q(ans_limit_date__lt=date.today()) & ~Q(record_state_id__in=RecordState.CLOSED_STATES)
        return Count("responsible_profile", filter=expired_filter)

    @staticmethod
    def get_near_expire_counter():

        near_expire_filter = Q(ans_limit_date__gt=timezone.now()) & \
                             Q(ans_limit_nearexpire__lte=timezone.now()) & \
                             ~Q(record_state_id__in=RecordState.CLOSED_STATES)
        return Count("responsible_profile", filter=near_expire_filter)

    @staticmethod
    def get_indicator_count(queryset, group_plate, counter_key):
        count = 0
        for counter in queryset:
            if group_plate in counter["responsible_profile__group_plate"]:
                count += counter[counter_key]
        return count


class RecordListOnlyFieldsMixin:
    only_fields = ("id", "user_id", "created_at", "updated_at", "description", "responsible_profile", "enabled",
                   "responsible_profile_id", "responsible_profile__group_plate", "responsible_profile__id",
                   "responsible_profile__description", "responsible_profile__profile_ctrl_user_id",
                   "responsible_profile__dist_sect_id", "responsible_profile__email", "responsible_profile__signature",
                   "responsible_profile__citizen_nd", "responsible_profile__is_ambit", "process", "mayorship",
                   "normalized_record_id", "alarm", "ans_limit_date", "urgent", "element_detail_id",
                   "element_detail__validated_reassignable", "element_detail__description",
                   "element_detail__element_id", "element_detail__element__description",
                   "element_detail__element__area_id", "claims_number",
                   "element_detail__element__area__description", "record_state", "record_state_id",
                   "record_state__user_id", "record_state__description", "record_state__acronym",
                   "record_state__enabled", "record_state__description", "ubication_id", "ubication__id",
                   "ubication__street", "ubication__street2", "ubication__xetrs89a", "ubication__yetrs89a",
                   "ubication__district", "user_displayed", "record_type", "pend_applicant_response",
                   "response_time_expired", "applicant_response", "citizen_alarm", "request",
                   "request__application_id", "request__applicant", "request__applicant__id", "similar_process",
                   "cancel_request", "reasigned", "possible_similar_records", "response_to_responsible",
                   "pend_response_responsible", "workflow", "reassignment_not_allowed",
                   "workflow__workflowresolution__resolution_type")


class RecordCardExcelExportListMixin(RecordListOnlyFieldsMixin, ExcelExportListMixin):
    export_serializer = RecordCardExportSerializer

    nested_excel_fields = {
        ExcelExportListMixin.NESTED_BASE_KEY: ["identificador", "tipusfitxa", "data_alta", "data_tancament",
                                               "dies_oberta", "antiguitat", "tipus_solicitant", "solicitant",
                                               "districte", "barri", "tipus_via", "carrer", "numero", "area", "element",
                                               "detall", "carac_especial_desc", "carac_especial", "descripcio", "estat",
                                               "perfil_responsable", "tipus_resposta", "resposta_feta",
                                               "comentari_qualitat"]
    }

    def queryset_export_extras(self, queryset):
        export_queryset = queryset._chain()
        export_queryset.query.select_related = deepcopy(queryset.query.select_related)

        export_queryset = export_queryset.select_related(
            "recordcardresponse", "recordcardresponse__response_channel", "request__applicant__citizen",
            "request__applicant__social_entity", "applicant_type").prefetch_related(
            Prefetch("recordcardspecialfeatures_set",
                     queryset=RecordCardSpecialFeatures.objects.filter(
                         enabled=True).select_related("feature", "feature__values_type")),
            Prefetch("recordcardtextresponse_set",
                     queryset=RecordCardTextResponse.objects.filter(enabled=True).order_by("created_at"))
        )
        return export_queryset.only(*self.set_only_fields())

    def set_only_fields(self):
        return self.only_fields + ("record_type__description", "closing_date", "ubication__district__name",
                                   "ubication__neighborhood", "ubication__via_type", "ubication__street",
                                   "ubication__street2", "request__applicant__citizen_id",
                                   "request__applicant__citizen__name", "request__applicant__citizen__first_surname",
                                   "request__applicant__citizen__second_surname", "recordcardresponse",
                                   "recordcardresponse__response_channel", "recordcardresponse__response_channel__id",
                                   "request__applicant__social_entity_id",
                                   "request__applicant__social_entity__social_reason", "applicant_type",
                                   "applicant_type__description", "citizen_web_alarm")


class PermissionActionMixin:
    permission = None

    def get_permissions(self):
        perms = super().get_permissions()
        if self.permission:
            perms += [IrisPermission(self.permission)]
        return perms


class RecordCardActionCheckMixin:
    serializer_class = None
    response_serializer_class = None
    response_data = None

    def do_check_action(self):
        """
        Do Record check action
        :return: Response dict data
        """
        confirmation_info, serializer_errors = self.check_valid()

        action_data = self.get_base_action_data(confirmation_info)
        action_data.update(self.get_extra_response_data())

        self.response_data = {
            "__action__": self.get_response_serializer_class()(action_data).data
        }
        if serializer_errors:
            self.response_data.update(serializer_errors)

    def check_valid(self):
        """
        Check data validity
        :return: Return response data
        """
        confirmation_info = {}
        serializer = self.get_serializer_class()(self.request.data)
        if serializer.is_valid():
            confirmation_info["can_confirm"] = True
            confirmation_info["reason"] = None
        else:
            confirmation_info["can_confirm"] = False
            confirmation_info["reason"] = _("Post data are invalid")
        return confirmation_info, serializer.errors

    def get_serializer_class(self):
        """
        Get serializer_class
        :return:
        """
        if not self.serializer_class:
            raise NotImplementedError
        return self.serializer_class

    def get_base_action_data(self, confirmation_info):
        """
        Set base response data
        :param confirmation_info: Info for confirmation
        :return:
        """
        next_group = self.get_record_next_group()
        if next_group != self.record_card.responsible_profile:
            different_ambit = self.request.user.usergroup.group.get_ambit_parent() != next_group.get_ambit_parent()
        else:
            different_ambit = False

        confirmation_info.update({
            "next_state": self.get_record_next_state(),
            "next_group": next_group,
            "different_ambit": different_ambit
        })
        return confirmation_info

    def get_extra_response_data(self):
        """
        :return: Extra response data for check action
        """
        return {}

    def get_record_next_state(self):
        """
        :return: Next RecordCard state code
        """
        return RecordState.objects.get(pk=self.record_card.next_step_code)

    def get_record_next_group(self):
        """
        :return: Next RecordCard group
        """
        derivate_group = self.record_card.derivate(user_id=get_user_traceability_id(self.request.user), is_check=True)
        return derivate_group if derivate_group else self.record_card.responsible_profile

    def get_response_serializer_class(self):
        """
        Get response_serializer_class
        :return:
        """
        if not self.response_serializer_class:
            raise NotImplementedError
        return self.response_serializer_class

    def send_check_response(self):
        """
        Send view check response
        :return: View Check Response, with serialized response data
        """
        return Response(data=self.response_data, status=HTTP_200_OK)
