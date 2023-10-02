import logging
from copy import deepcopy
from datetime import timedelta, datetime

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import F, Q, Prefetch, Count, Avg, Sum
from django.db.models.signals import post_save
from django.shortcuts import get_object_or_404
from django.utils import translation
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, renderers
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter

from rest_framework.generics import CreateAPIView, RetrieveAPIView, DestroyAPIView
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import (HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST,
                                   HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT)
from rest_framework.views import APIView

from emails.emails import InternalClaimEmail, ExternalTramitationEmail, RecordCardAnswer
from excel_export.mixins import ExcelExportListMixin
from integrations.hooks import send_twitter
from iris_masters.models import RecordState, Reason, ResponseChannel, ApplicantType, Parameter, ResolutionType
from integrations.services.pdf.hooks import create_letter_code
from iris_masters.views import BasicMasterListApiView, BasicMasterSearchMixin, BasicMasterViewSet
from main.api.filters import UnaccentSearchFilter
from main.api.pagination import RecordCardPagination
from main.api.schemas import (create_swagger_auto_schema_factory, get_swagger_auto_schema_factory,
                              list_swagger_auto_schema_factory, update_swagger_auto_schema_factory,
                              destroy_swagger_auto_schema_factory, retrieve_swagger_auto_schema_factory)
from main.api.serializers import GetGroupFromRequestMixin
from main.utils import SPANISH, LIST_ACTION, CREATE_ACTION, UPDATE_ACTIONS, DELETE_ACTION, get_user_traceability_id
from main.views import UpdatePatchAPIView, ModelCRUViewSet, PermissionCustomSerializerMixin
from profiles.models import Group
from profiles.permission_registry import ADMIN_GROUP
from profiles.permissions import IrisPermission, IrisPermissionChecker
from profiles.serializers import GroupShortSerializer
from profiles.tasks import send_allocated_notification
from record_cards.anonymize.citizen_anonymize import CitizenAnonymize
from record_cards.applicant_sources.applicant_source import IrisSource
from record_cards.base_views import (RecordCardActions, RecordCardGetBaseView, WorkflowStateChangeAction,
                                     CustomChunkedUploadView, RecordStateChangeAction, RecordStateChangeMixin,
                                     WorkflowActions)
from record_cards.filters import ApplicantFilter, RecordCardFilter, WorkflowFilter
from record_cards.models import (Applicant, ApplicantResponse, Citizen, Comment, RecordCard, Request, SocialEntity,
                                 RecordCardTextResponse, RecordCardBlock, Ubication, Workflow,
                                 WorkflowComment, WorkflowPlan, WorkflowResolution, WorkflowResolutionExtraFields,
                                 RecordFile, RecordChunkedFile, RecordCardStateHistory, MonthIndicator,
                                 InternalOperator, record_card_resend_answer)
from record_cards.mixins import (SetRecordStateHistoryMixin, RecordCardResponsibleProfileMixin,
                                 RecordCardRestrictedConversationPermissionsMixin, RecordCardIndicatorsMixin,
                                 RecordCardExcelExportListMixin, PermissionActionMixin, RecordCardActionCheckMixin)
from record_cards.permissions import RECARD_ANSWER_NO_LETTER, RECARD_ANSWER_NOSEND, RECARD_REASSIGN_OUTSIDE
from record_cards.record_actions.claim_validate import ClaimValidation
from record_cards.record_actions.exceptions import RecordClaimException
from record_cards.record_actions.external_validators import get_external_validator

from record_cards.record_actions.reasignations import PossibleReassignations
from record_cards.record_actions.record_files import GroupManageFiles
from record_cards.record_actions.record_set_possible_similar import RecordCardSetPossibleSimilar
from record_cards.record_actions.state_machine import RecordCardStateMachine
from record_cards.schemas import post_record_card_schema_factory
from record_cards.serializers import (
    ApplicantResponseSerializer, ApplicantSerializer, CitizenSerializer, CommentSerializer, RecordCardCancelSerializer,
    WorkflowPlanSerializer, RecordCardSerializer, RecordCardUrgencySerializer,
    RecordCardManagementIndicatorsSerializer, RequestSerializer, SocialEntitySerializer, UbicationSerializer,
    RecordCardDetailSerializer, WorkflowResoluteSerializer, RecordCardTextResponseSerializer, WorkflowSerializer,
    RecordCardMonthIndicatorsSerializer, RecordCardTraceabilitySerializer, RecordCardReasignationSerializer,
    RecordCardReasignableSerializer, RecordCardMultiRecordstListSerializer, RecordCardThemeChangeSerializer,
    RecordCardValidateCheckSerializer, RecordChunkedFileSerializer, RecordCardRestrictedSerializer,
    RecordCardApplicantListSerializer, ClaimShortSerializer, ClaimDescriptionSerializer, RecordCardClaimCheckSerializer,
    RecordCardUpdateSerializer, RecordCardShortNotificationsSerializer, RecordCardManagementAmbitIndicatorsSerializer,
    InternalOperatorSerializer, RecordCardBlockSerializer, RecordCardWillBeSolvedSerializer,
    RecordUbicationListSerializer, RecordCardCheckSerializer, RecordCardListRegularSerializer,
    WorkflowResoluteDraftSerializer, WorkflowResoluteExtraFieldsSerializer,
    ApplicantRegularSerializer, TwitterRecordSerializer, RecordCardBaseListRegularSerializer, WorkflowFieldsSerializer)
from record_cards.tasks import (register_possible_similar_records, save_last_applicant_response,
                                calculate_month_indicators, sync_applicant_to_source,
                                set_record_card_audits, remove_applicant_zero, geocode_ubication)
from record_cards import permissions as record_permissions
from record_cards.templates import render_record_response
from themes.actions.group_tree import GroupThemeTree
from themes.models import ElementDetail
import pytz
from main.storage.imi_minio_storage import IMIMinioMediaStorage


from django.utils import timezone
COPY_FILES_FROM_PARAM = "copy_files_from"


logger = logging.getLogger(__name__)


class UbicationListView(BasicMasterListApiView):
    """
    List of available ubications
    """
    queryset = Ubication.objects.filter(enabled=True)
    serializer_class = UbicationSerializer


class ApplicantPermissionsMixin:

    def create(self, request, *args, **kwargs):
        if self.user_cant_create():
            return Response("Acces not Allowed", status=HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

    def user_cant_create(self):
        permission_checker = IrisPermissionChecker.get_for_user(self.request.user)
        citizen_create_permission = permission_checker.has_permission(record_permissions.CITIZENS_CREATE)
        return not citizen_create_permission

    def get_permissions(self):
        if self.action in UPDATE_ACTIONS or self.action == CREATE_ACTION:
            return [IsAuthenticated(), IrisPermission(record_permissions.CITIZENS_CREATE)]
        if self.action == DELETE_ACTION:
            return [IsAuthenticated(), IrisPermission(record_permissions.CITIZENS_DELETE)]
        return super().get_permissions()

    def destroy(self, request, *args, **kwargs):
        if self.user_cant_destroy():
            return Response("Acces not Allowed", status=HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

    def user_cant_destroy(self):
        permission_checker = IrisPermissionChecker.get_for_user(self.request.user)
        citizen_delete_permission = permission_checker.has_permission(record_permissions.CITIZENS_DELETE)
        return not citizen_delete_permission


@method_decorator(name="create", decorator=create_swagger_auto_schema_factory(CitizenSerializer))
@method_decorator(name="update", decorator=update_swagger_auto_schema_factory(CitizenSerializer))
@method_decorator(name="partial_update", decorator=update_swagger_auto_schema_factory(CitizenSerializer))
@method_decorator(name="list", decorator=list_swagger_auto_schema_factory(CitizenSerializer))
@method_decorator(name="destroy", decorator=destroy_swagger_auto_schema_factory())
class CitizenViewSet(ApplicantPermissionsMixin, BasicMasterViewSet):
    """
    Viewset for Citizens (CRUD).
    When a citizen is destroyed, it's set to be anonymized.
    To be able to create/update, the user needs CITIZENS_CREATE permission.
    To delete the permission CITIZENS_DELETE is needed.
    """
    queryset = Citizen.objects.all().select_related("district")
    serializer_class = CitizenSerializer

    def perform_destroy(self, instance):
        if instance.can_be_anonymized:
            CitizenAnonymize(instance).anonymize()
        else:
            instance.applicant_set.all().update(pend_anonymize=True)

        super().perform_destroy(instance)


@method_decorator(name="create", decorator=create_swagger_auto_schema_factory(SocialEntitySerializer))
@method_decorator(name="update", decorator=update_swagger_auto_schema_factory(SocialEntitySerializer))
@method_decorator(name="partial_update", decorator=update_swagger_auto_schema_factory(SocialEntitySerializer))
@method_decorator(name="list", decorator=list_swagger_auto_schema_factory(SocialEntitySerializer))
@method_decorator(name="destroy", decorator=destroy_swagger_auto_schema_factory())
class SocialEntityViewSet(ApplicantPermissionsMixin, BasicMasterViewSet):
    """
    Viewset for Social Entities (CRUD).
    To be able to create/update, the user needs CITIZENS_CREATE permission.
    To delete the permission CITIZENS_DELETE is needed.
    """

    queryset = SocialEntity.objects.all().select_related("district")
    serializer_class = SocialEntitySerializer


class ApplicantSearch(APIView):
    """
    Finds applicants in different sources. Currently, they are found in IRIS2 and MIB database.
    """
    serializer_class = ApplicantRegularSerializer
    applicant_source_class = IrisSource
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        ser = self.get_serializer()
        return self.get_response(ser)

    def get_applicants(self):
        if getattr(self, 'swagger_fake_view', False):
            return []

        applicants = self.applicant_source.find(self.request.GET)

        ordering = self.request.GET.get("ordering")
        if ordering:
            # ordering expected as: citizen__first_surname or social_entity__social_reason
            ordering = ordering.split("__")
            return sorted(applicants, key=lambda x: getattr(getattr(x, ordering[0]), ordering[1]).upper())

        return applicants

    def get_serializer(self):
        applicants = self.get_applicants()
        return self.serializer_class(instance=applicants, many=True)

    def get_response(self, ser):
        return Response(ser.data, status=status.HTTP_200_OK)

    @cached_property
    def applicant_source(self):
        return self.applicant_source_class()


@method_decorator(name="create", decorator=create_swagger_auto_schema_factory(ApplicantSerializer))
@method_decorator(name="update", decorator=update_swagger_auto_schema_factory(ApplicantSerializer))
@method_decorator(name="partial_update", decorator=update_swagger_auto_schema_factory(ApplicantSerializer))
@method_decorator(name="list", decorator=list_swagger_auto_schema_factory(ApplicantSerializer))
@method_decorator(name="destroy", decorator=destroy_swagger_auto_schema_factory())
class ApplicantViewSet(ExcelExportListMixin, ApplicantPermissionsMixin, BasicMasterViewSet):
    """
    Viewset for Applicants (CRUD).
    When an applicant is destroyed, it's set to be anonymized.
    To be able to create/update, the user needs CITIZENS_CREATE permission.
    To delete the permission CITIZENS_DELETE is needed.
    The list endpoint:
     - can be exported to excel.
     - can be ordered by citizen dni, citizen name, citizen surnames, social entity cif and social entity social reason
     - can be filtered by applicant type, dni, citizen name, citizen surnames, citizen full name, cif, social entity
     social reason or pending to anomymize
    """

    queryset = Applicant.objects.all().select_related("citizen", "citizen__district", "social_entity",
                                                      "social_entity__district")
    serializer_class = ApplicantSerializer
    filterset_class = ApplicantFilter
    filename = "applicants.xlsx"
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    ordering_fields = ["citizen__dni", "citizen__name", "citizen__first_surname", "citizen__second_surname",
                       "social_entity__cif", "social_entity__social_reason"]
    nested_excel_fields = {
        ExcelExportListMixin.NESTED_BASE_KEY: ["citizen", "social_entity"],
        "citizen": {ExcelExportListMixin.NESTED_BASE_KEY: ["dni", "name", "first_surname", "second_surname"]},
        "social_entity": {ExcelExportListMixin.NESTED_BASE_KEY: ["cif", "social_reason"]}
    }

    def perform_create(self, serializer):
        super().perform_create(serializer)
        self.sync_to_source(serializer.instance)

    def perform_update(self, serializer):
        super().perform_update(serializer)
        self.sync_to_source(serializer.instance)

    @staticmethod
    def sync_to_source(applicant):
        sync_applicant_to_source.delay(applicant.pk)

    def perform_destroy(self, instance):
        if instance.citizen:
            instance.anonymize()
            instance.citizen.delete()
        else:
            instance.social_entity.delete()

        super().perform_destroy(instance)


class DefaultApplicantView(RetrieveAPIView):
    """
    Endpoint to Retrieve the default applicant for the RecordCards that need it.
    """
    queryset = Applicant.objects.all().select_related("citizen", "citizen__district", "social_entity",
                                                      "social_entity__district")
    serializer_class = ApplicantSerializer

    def get_object(self):
        return self.filter_queryset(self.get_queryset()).filter(
            citizen__dni=Parameter.objects.get(parameter="AGRUPACIO_PER_DEFECTE").valor
        ).first()


class ApplicantResponseRetrieveView(RetrieveAPIView):
    """
    Get the saved applicant response data to perform a pre-fill on record card response
    """
    permission_classes = (IsAuthenticated,)
    queryset = ApplicantResponse.objects.filter(enabled=True)
    serializer_class = ApplicantResponseSerializer
    lookup_field = "applicant_id"

    def get_object(self):
        # return always the empty values
        return ApplicantResponse(applicant=self.applicant)

    @cached_property
    def applicant(self):
        if getattr(self, 'swagger_fake_view', False):
            app_resp = ApplicantResponse.objects.first()
            if app_resp:
                return app_resp.applicant
            return
        return get_object_or_404(Applicant, pk=self.kwargs.get(self.lookup_field))

    def get_serializer(self, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        kwargs["context"] = self.get_serializer_context()
        if getattr(self, 'swagger_fake_view', False):
            instance = self.send_response_context(ApplicantResponse.objects.first(),
                                                  kwargs["context"])
        else:
            instance = self.send_response_context(args[0], kwargs["context"])
        return serializer_class(instance, **kwargs)

    def send_response_context(self, instance, context):
        """
        Check if applicant of instance is an internal operator or not.
        If it's an internal operator, an empty instance is returned and the send_response is updated depending
        on applicant_type config.
        Else returns the applicant response instnce with send_response flag set to True

        :param instance: applicant response instance
        :param context: serializer context
        :return: if applicant of applicant response is internal operator returns none, else applicant response insntance
        """
        if self.applicant.is_nd:
            context["send_response"] = False
        else:
            applicant_type_id = self.request.GET.get("applicant_type_id")
            input_channel_id = self.request.GET.get("input_channel_id")
            is_internal_operator = instance.applicant.is_internal_operator(applicant_type_id, input_channel_id)
            if is_internal_operator:
                context["send_response"] = ApplicantType.get_send_response(applicant_type_id)
                return
            else:
                context["send_response"] = True
                return instance


@method_decorator(name="post", decorator=post_record_card_schema_factory(
    responses={
        HTTP_204_NO_CONTENT: "Remove applicant zero task queued",
    }))
class RemoveApplicantZero(APIView):
    """
    Endpoint to delay task to remove applicant with ID = 0 from IRIS1
    """

    def post(self, request, *args, **kwargs):
        remove_applicant_zero.delay()
        return Response(status=HTTP_204_NO_CONTENT)


@method_decorator(name="create", decorator=create_swagger_auto_schema_factory(InternalOperatorSerializer))
@method_decorator(name="update", decorator=update_swagger_auto_schema_factory(InternalOperatorSerializer))
@method_decorator(name="partial_update", decorator=update_swagger_auto_schema_factory(InternalOperatorSerializer))
@method_decorator(name="list", decorator=list_swagger_auto_schema_factory(InternalOperatorSerializer))
@method_decorator(name="retrieve", decorator=retrieve_swagger_auto_schema_factory(InternalOperatorSerializer))
@method_decorator(name="destroy", decorator=destroy_swagger_auto_schema_factory())
class InternalOperatorViewSet(ExcelExportListMixin, BasicMasterSearchMixin, BasicMasterViewSet):
    """
    Viewset for Intenal Operators, applicants registered by document, applicant type and input channel (CRUD).
    The list endpoint:
     - can be exported to excel.
     - can be ordered by document and applicant type and input channel descriptions
     - supports unaccent search by document
    """

    permission_classes = (IsAuthenticated,)
    queryset = InternalOperator.objects.all().select_related("applicant_type", "input_channel")
    serializer_class = InternalOperatorSerializer
    search_fields = ["#document"]
    filter_backends = (UnaccentSearchFilter, DjangoFilterBackend, OrderingFilter)
    ordering_fields = ["document", "applicant_type__description", "input_channel__description"]
    filename = "internal-operators.xlsx"
    nested_excel_fields = {
        ExcelExportListMixin.NESTED_BASE_KEY: ["document", "applicant_type", "input_channel"],
        "applicant_type": {
            ExcelExportListMixin.NESTED_BASE_KEY: ["description"]
        },
        "input_channel": {
            ExcelExportListMixin.NESTED_BASE_KEY: ["description"]
        }
    }
    permission_codename = ADMIN_GROUP

    def get_permissions(self):
        return [IrisPermission(self.permission_codename)]


class RequestViewSet(ModelCRUViewSet):
    """
    Viewset for Requests (CRUD).
    """
    queryset = Request.objects.filter(enabled=True).select_related(
        "applicant", "applicant__citizen", "applicant__citizen__district", "input_channel", "applicant__social_entity",
        "applicant__social_entity__district", "application", "communication_media", "applicant__applicantresponse",
        "application", "input_channel", "communication_media")
    serializer_class = RequestSerializer


record_card_swagger = swagger_auto_schema(request_body=RecordCardSerializer,
                                          responses={
                                              HTTP_201_CREATED: RecordCardSerializer,
                                              HTTP_400_BAD_REQUEST: "Bad request: Validation Error",
                                              HTTP_403_FORBIDDEN: "User has no permissions",
                                              HTTP_409_CONFLICT: "Multirecord can not be done because "
                                                                 "record is closed or cancelled"
                                          })

record_card_update_swagger = swagger_auto_schema(request_body=RecordCardThemeChangeSerializer,
                                                 responses={
                                                     HTTP_200_OK: RecordCardSerializer,
                                                     HTTP_400_BAD_REQUEST: "Bad request: Validation Error",
                                                     HTTP_403_FORBIDDEN: "User has no permissions",
                                                     HTTP_404_NOT_FOUND: "Not found: resource not exists",
                                                     HTTP_409_CONFLICT: "Action can not be done with a closed or "
                                                                        "cancelled record"})


class RecordCardCheckPermissionsSerializerMixin(RecordCardRestrictedConversationPermissionsMixin,
                                                PermissionCustomSerializerMixin):
    no_permission_serializer = RecordCardRestrictedSerializer
    no_permission_list_serializer = RecordCardListRegularSerializer


class RecordCardOrdering(OrderingFilter):

    def get_ordering(self, request, queryset, view):
        order = super().get_ordering(request, queryset, view)
        if order:
            return [self.get_ubication_ordering(o) if 'ubication__street' in o else o for o in order]
        return order

    def get_ubication_ordering(self, o):
        method = 'desc' if o[0] == '-' else 'asc'
        o = o[1:] if o[0] == '-' else o
        return getattr(F(o), method, 'asc')(nulls_last=True)


class RecordCardListOrderingMixin:
    filter_backends = (DjangoFilterBackend, RecordCardOrdering)
    ordering_fields = ["urgent", "normalized_record_id", "record_type__description", "record_state__description",
                       "created_at", "ans_limit_date", "element_detail__element__area__description",
                       "element_detail__element__description", "element_detail__description",
                       "ubication__street", "ubication__district_id", "responsible_profile__description"]


@method_decorator(name="create", decorator=record_card_swagger)
@method_decorator(name="update", decorator=record_card_update_swagger)
@method_decorator(name="partial_update", decorator=record_card_update_swagger)
@method_decorator(name="list", decorator=list_swagger_auto_schema_factory(RecordCardListRegularSerializer))
@method_decorator(name="retrieve", decorator=retrieve_swagger_auto_schema_factory(RecordCardSerializer))
class RecordCardViewSet(RecordCardExcelExportListMixin, RecordCardListOrderingMixin,
                        RecordCardCheckPermissionsSerializerMixin, ModelCRUViewSet):
    """
    Viewset for Record Cards (CRU).
    The list of records is used to retrieve the search of records. The list endpoint:
     - can be exported to excel.
     - can be ordered by urgent, normalized_record_id, record type, record state, created_at, ANS limit date,
     area description, element description, theme description, ubication street or district and responsible profile
     - can be filtered by multiple parameters, for example: urgent, input_channel, support, applicant fields, etc

    When a RecordCard is retrieved, the user that has request it is updated as the user displayed.
    The lookup used on the detail retrieve is the normalized_record_id field.
    In addition to permissions to actions, depending on the configuration of the RecordCard and the group assigned
    to the user the RecordCard will be displayed with all its information or only a restricted subset.

    On the data validation, there are some rules to take into account:
     - the Theme used has to be active
     - to create a RecordCard, the user needs to have an assigned group and it can't be the anonymous group
     - if selected support is Communication Media, a communication Media and a publishing date have to be set.
     - the inputChannel has to be allowed for the user group
     - the support has to be allowed for the inputChannel
     - to set mayorship to True, the input Channel has to allow it
     - to set mayorship to True, the user hast to have the MAYORSHIP permission
     - the applicant must be set and can not be blocked if record state is not NO_PROCESSED.
     - the citizen ND can only be used if the selected support and user group that creates the record are allowed to it
     - a register code from Ariadna has to be set if the support requires it
     - to set a multirecord the user need RECARD_MULTIRECORD permission and the Record from can not have a multirecord

    Permissions:
     - To be able to create RecordCards, the record CREATE permission is needed
     - To be able to create RecordCards with multirecords, the record RECARD_MULTIRECORD permission is needed
     - To be able to update RecordCards, the record UPDATE permission is needed
     - To be able to retrieve the list without filters, the record RECARD_SEARCH_NOFILTERS is needed
    """

    queryset = RecordCard.objects.order_by("-created_at")
    serializer_class = RecordCardSerializer
    short_serializer_class = RecordCardBaseListRegularSerializer
    filterset_class = RecordCardFilter
    lookup_field = "normalized_record_id"
    lookup_url_kwarg = "reference"
    pagination_class = RecordCardPagination
    filename = "records.xlsx"

    def list(self, request, *args, **kwargs):
        filter_params = self.get_filter_params(request)
        if not filter_params and not IrisPermissionChecker.get_for_user(request.user).has_permission(
                record_permissions.RECARD_SEARCH_NOFILTERS
        ):
            return Response("Access Not Allowed", status=HTTP_403_FORBIDDEN)

        return super().list(request, *args, **kwargs)

    def paginate_queryset(self, queryset):
        if self.request.method == "GET" and 'map' in self.request.GET:
            self.paginator.page_size = int(Parameter.get_parameter_by_key("MAP_SEARCH_RECORDS", 150))
            self.paginator.max_page_size = self.paginator.page_size
        return super().paginate_queryset(queryset)

    def get_filter_params(self, request):
        filter_params = request.GET.copy()
        filter_params.pop("page", None)
        filter_params.pop("page_size", None)
        return filter_params

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == LIST_ACTION:
            if not self.is_export:
                queryset = queryset.filter(responsible_profile__isnull=False).select_related(
                    "ubication", "ubication__district", "request", "request__applicant", "workflow").only(
                    "id", "user_id", "created_at", "updated_at", "process", "mayorship", "normalized_record_id",
                    "alarm", "ans_limit_date", "urgent", "user_displayed", "reassignment_not_allowed", "claims_number",
                    "pend_applicant_response", "response_time_expired", "applicant_response", "reasigned",
                    "citizen_alarm", "citizen_web_alarm", "similar_process", "cancel_request",
                    "possible_similar_records", "response_to_responsible", "pend_response_responsible", "ubication",
                    "ubication__district", "ubication__street", "ubication__street2", "record_state", "record_type",
                    "element_detail", "responsible_profile", "request", "request__applicant", "workflow")
            else:
                queryset = queryset.filter(responsible_profile__isnull=False).select_related(
                    "element_detail", "element_detail__element", "element_detail__element__area", "record_state",
                    "responsible_profile", "record_type", "ubication", "ubication__district", "request",
                    "request__applicant", "workflow")
                queryset = self.queryset_export_extras(queryset)
        else:
            queryset = queryset.select_related(
                "request", "request__applicant", "ubication", "ubication__district", "workflow"
            ).prefetch_related(
                Prefetch("recordcardblock_set", queryset=RecordCardBlock.objects.all()),
                Prefetch("recordfile_set", queryset=RecordFile.objects.all()))
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        self.set_element_detail_context(context)
        return context

    def set_element_detail_context(self, context):
        element_detail = None
        if self.action in UPDATE_ACTIONS:
            element_detail = self.record_instance.element_detail
        elif self.action == CREATE_ACTION:
            element_detail_id = self.request.data.get("element_detail_id")
            try:
                element_detail = ElementDetail.objects.get(pk=element_detail_id)
            except ElementDetail.DoesNotExist:
                element_detail = None
        if element_detail:
            context.update({"element_detail": element_detail})

    def get_serializer_class(self):
        if self.request.method == "GET" and 'map' in self.request.GET:
            return RecordUbicationListSerializer
        if self.request.method == "GET" and self.is_retrieve:
            return RecordCardDetailSerializer
        elif self.request.method == "PUT" or self.request.method == "PATCH":
            return RecordCardUpdateSerializer
        return super().get_serializer_class()

    def get_permissions(self):
        if self.action == CREATE_ACTION:
            if self.request.data.get('multirecord_from'):
                return [IrisPermission(record_permissions.RECARD_MULTIRECORD)]
            return [IrisPermission(record_permissions.CREATE)]
        if self.action in UPDATE_ACTIONS:
            return [IrisPermission(record_permissions.UPDATE)]

        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        serializer_data = self.get_creation_data()
        serializer_data.update({"creation_department": ''})

        logger.info(f"APPLICANT TYPE ID : {serializer_data.get('applicant_type_id')}")
        logger.info(f"APPLICANT ID : {serializer_data.get('applicant_id')}")

        serializer = self.get_serializer(data=serializer_data)
        serializer.is_valid(raise_exception=True)
        multirecord_from = serializer.validated_data.get("multirecord_from")
        if multirecord_from and multirecord_from.record_state_id in RecordState.CLOSED_STATES:
            return Response(_("Action can not be done with a closed or cancelled record"), status=HTTP_409_CONFLICT)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=HTTP_201_CREATED, headers=headers)

    def get_creation_data(self):
        return self.request.data.copy()

    def perform_create(self, serializer):
        record_card = serializer.save()
        send_allocated_notification.delay(record_card.responsible_profile_id, record_card.pk)
        register_possible_similar_records.delay(record_card.pk)
        applicant = record_card.request.applicant
        atype = record_card.applicant_type_id
        if record_card.ubication:
            # Mayorship records should not be derivated in initial state
            derivate_id = None if record_card.mayorship else record_card.pk
            geocode_ubication.delay(record_card.ubication.pk, derivate_id=derivate_id, user_id=record_card.user_id)
        if applicant and not applicant.is_internal_operator(atype, record_card.input_channel_id):
            save_last_applicant_response.delay(record_card.request.applicant_id, record_card.recordcardresponse.pk)
        copy_files_record_pk = self.request.data.get(COPY_FILES_FROM_PARAM)
        if copy_files_record_pk:
            user_group = self.get_group_from_request(self.request)
            record_card.copy_files(user_group, copy_files_record_pk)
        self.record_card = record_card
        self.post_create(record_card)

    @cached_property
    def record_instance(self):
        return self.get_object()

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.record_instance
        if instance.record_state_id in RecordState.CLOSED_STATES:
            return Response(_("Action can not be done with a closed or cancelled record"), status=HTTP_409_CONFLICT)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, "_prefetched_objects_cache", None):
            # If "prefetch_related" has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)

    def perform_update(self, serializer):
        record_card = serializer.save()
        register_possible_similar_records.delay(record_card.pk)
        if record_card.ubication and not hasattr(record_card.ubication, "extendedgeocodeubication"):
            geocode_ubication.delay(record_card.ubication.pk)

    def retrieve(self, request, *args, **kwargs):
        instance = self.record_instance
        user_group = self.get_group_from_request(request)
        self.update_user_displayed(user_group, instance)
        serializer = self.get_serialized_instance(user_group, instance)
        return Response(serializer.data)

    def update_user_displayed(self, user_group, instance):
        """
        If user can tramit record card (is_allowed), update the user displayed field

        :param user_group: Group of user
        :param instance: record card retrieved
        :return:
        """
        if instance.record_state_id not in RecordState.CLOSED_STATES:
            if self.group_is_allowed(user_group, instance) and \
                    get_user_traceability_id(self.request.user) != instance.user_displayed:
                instance.user_displayed = get_user_traceability_id(self.request.user)
                instance.save(update_fields=["user_displayed", "updated_at"])

    def group_is_allowed(self, user_group, instance):
        # The user that has created the record card, can see it
        # or we are in list, whose serializer does not include sensitive fields
        if not instance.mayorship and (
                get_user_traceability_id(self.request.user) == instance.user_id or not self.is_retrieve
        ):
            return True
        if user_group:
            if instance.mayorship:
                if self.has_mayorship_perms() or self.can_response_messages(instance, user_group):
                    return True
            else:
                # If theme has NOT group profiles, everybody can see the record
                if not instance.element_detail.has_group_profiles:
                    return True

                group_can_see = instance.element_detail.group_can_see(user_group.group_plate)
                if group_can_see:
                    return True

            can_tramit = instance.group_can_tramit_record(user_group)
            return can_tramit or self.can_response_messages(instance, user_group)
        else:
            return False

    def has_mayorship_perms(self):
        return IrisPermissionChecker.get_for_user(
            self.request.user
        ).has_permission(record_permissions.MAYORSHIP)

    def post_create(self, record_card):
        record_card.send_record_card_created()


swagger_record_update_check = swagger_auto_schema(request_body=RecordCardUpdateSerializer,
                                                  responses={
                                                      HTTP_200_OK: RecordCardCheckSerializer,
                                                      HTTP_400_BAD_REQUEST: "Bad request: Validation Error",
                                                      HTTP_403_FORBIDDEN: "User has no permissions",
                                                      HTTP_404_NOT_FOUND: "Not found: resource not exists"})


@method_decorator(name="put", decorator=swagger_record_update_check)
@method_decorator(name="patch", decorator=swagger_record_update_check)
class RecordCardUpdateCheckView(GetGroupFromRequestMixin, PermissionActionMixin, RecordCardActionCheckMixin, APIView):
    """
    Endpoint to check the result that will produce the update of the description, mayorship, features,
    sepecial_features, ubication and response on a RecordCard.
    To do this action, the user needs to have record UPDATE permission.
    """

    permission_classes = (IsAuthenticated,)
    permission = record_permissions.UPDATE

    serializer_class = RecordCardUpdateSerializer
    response_serializer_class = RecordCardCheckSerializer

    def put(self, request, *args, **kwargs):
        self.do_check_action()
        return self.send_check_response()

    def patch(self, request, *args, **kwargs):
        self.do_check_action()
        return self.send_check_response()

    @cached_property
    def record_card(self):
        """
        Get record card instance
        :return: RecordCard
        """
        return get_object_or_404(RecordCard, normalized_record_id=self.kwargs["normalized_record_id"], enabled=True)

    def get_record_next_state(self):
        """
        :return: Next RecordCard state code
        """
        data_response = self.request.data.get("recordcardresponse")
        response_channel_id = data_response.get("response_channel") if data_response else None
        if self.record_card.pending_answer_has_toclose_automatically(response_channel_id):
            return RecordState.objects.get(id=RecordState.CLOSED)
        return self.record_card.record_state

    def check_valid(self):
        """
        Check data validity
        :return: Return response data
        """
        confirmation_info = {}
        self.serializer = self.get_serializer_class()(data=self.request.data, instance=self.record_card,
                                                      context={"element_detail": self.record_card.element_detail,
                                                               "request": self.request})
        if self.serializer.is_valid():
            confirmation_info["can_confirm"] = True
            confirmation_info["reason"] = None
        else:
            confirmation_info["can_confirm"] = False
            confirmation_info["reason"] = _("Post data are invalid")
        return confirmation_info, self.serializer.errors

    def get_record_next_group(self):
        """
        :return: Next RecordCard group
        """
        if not self.serializer.ubication_has_change():
            return self.record_card.responsible_profile
        derivate_group = self.record_card.derivate(get_user_traceability_id(self.request.user),
                                                   next_district_id=self.get_next_district_id(), is_check=True)
        return derivate_group if derivate_group else self.record_card.responsible_profile

    def get_next_district_id(self):
        if "ubication" in self.serializer.validated_data:
            self.record_card.ubication = Ubication(**self.serializer.validated_data.get('ubication'))
            return self.record_card.ubication.district_id
        return self.record_card.ubication.district_id if self.record_card.ubication else None


class TwitterRecordCardViewSet(RecordCardViewSet):
    """
    Viewset to create records to twitter. The records can be created without applicant.
    The information is full field using the Parameters to config twitter records.
    The records are autovalidated and closed directly.
    Permissions:
     - to create, user has to have CREATE_TWITTER permission
     - to update, user has to have record UPDATE permission
    """
    serializer_class = TwitterRecordSerializer

    def create(self, request, *args, **kwargs):
        suggestion = self.next_theme_id()
        with transaction.atomic():
            resp = super().create(request, *args, **kwargs)
            send_twitter(self.record_card, suggestion.id)
            user = request.user if request else None
            self.record_card.validate(request.META.get("HTTP_DEPARTAMENTCUSER", ""), user,
                                      next_state_code=RecordState.CLOSED, automatic=True, perform_derivation=False)
            Comment.objects.create(
                record_card=self.record_card, reason_id=Reason.RECORDCARD_TWITTER,
                group=self.get_group_from_request(self.request),
                comment=str(suggestion.id) + ' - ' + suggestion.description
            )
        return resp

    def get_permissions(self):
        if self.action == CREATE_ACTION:
            return [IrisPermission(record_permissions.CREATE_TWITTER), IsAuthenticated()]
        if self.action in UPDATE_ACTIONS:
            return [IrisPermission(record_permissions.UPDATE), IsAuthenticated()]
        return super().get_permissions()

    def next_theme_id(self):
        try:
            return ElementDetail.objects.get(pk=self.request.data.get("next_theme_id", None))
        except ElementDetail.DoesNotExist:
            raise ValidationError({'next_theme_id': _('This field is required')})

    def get_creation_data(self):
        data = super().get_creation_data()
        data["input_channel_id"] = Parameter.get_parameter_by_key("TWITTER_INPUT_CHANNEL", None)
        data["support_id"] = Parameter.get_parameter_by_key("TWITTER_SUPPORT", None)
        data["recordcardresponse"] = {'response_channel': ResponseChannel.NONE}
        data["without_applicant"] = True
        data["element_detail_id"] = Parameter.get_parameter_by_key("TWITTER_ELEMENT_DETAIL", None)
        data["applicant_type_id"] = Parameter.get_parameter_by_key("TWITTER_APPLICANT_TYPE", 0)
        return data

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['validate_group_input_channel'] = False
        return ctx


class SurveyViewSet(RecordCardViewSet):
    """
    Viewset to create surveys.
    The information is full field using the Parameters to config surveys.
    Permissions:
     - to update, user has to have record UPDATE permission
    """

    def get_permissions(self):
        if self.action == CREATE_ACTION:
            return [IsAuthenticated()]
        if self.action in UPDATE_ACTIONS:
            return [IrisPermission(record_permissions.UPDATE), IsAuthenticated()]
        return super().get_permissions()

    def get_creation_data(self):
        data = super().get_creation_data()
        data["input_channel_id"] = Parameter.get_parameter_by_key("IRIS_ENQUESTA_CANAL", 1)
        data["support_id"] = Parameter.get_parameter_by_key("IRIS_ENQUESTA_SUPORT", 1)
        data["applicant_id"] = Applicant.objects.get(
            citizen__dni=Parameter.get_parameter_by_key("AGRUPACIO_PER_DEFECTE")
        ).id
        data["element_detail_id"] = Parameter.get_parameter_by_key("IRIS_ENQUESTA", None)
        data["applicant_type_id"] = Parameter.get_parameter_by_key("IRIS_ENQUESTA_APPLICANTTYPE", 0)
        if not data.get('recordcardresponse') or data['recordcardresponse'].get('response_channel') is None:
            data['recordcardresponse'] = {'response_channel': ResponseChannel.NONE}
        if not data['recordcardresponse'].get('language', ""):
            data['recordcardresponse']['language'] = SPANISH
        return data

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['validate_group_input_channel'] = False
        ctx['validate_theme_active'] = False
        return ctx


class RecordCardPkRetrieveView(RetrieveAPIView):
    """
    View to retrieve Records by its pk.
    """
    permission_classes = (IsAuthenticated,)
    queryset = RecordCard.objects.filter(enabled=True).select_related(
        "element_detail", "element_detail__element", "element_detail__element__area", "request",
        "request__applicant", "request__applicant__citizen", "request__applicant__social_entity", "support",
        "applicant_type", "record_state", "record_type", "responsible_profile", "ubication",
        "ubication__district", "creation_group").prefetch_related(
        Prefetch("recordcardblock_set", queryset=RecordCardBlock.objects.all()))
    serializer_class = RecordCardDetailSerializer


class RecordChartPermission:

    def get_permissions(self):
        return [IsAuthenticated(), IrisPermission(record_permissions.RECARD_CHARTS)]


@method_decorator(name="get", decorator=swagger_auto_schema(
    responses={
        HTTP_200_OK: RecordCardManagementIndicatorsSerializer,
    }
))
class RecordCardGroupManagementIndicatorsView(RecordChartPermission, RecordCardIndicatorsMixin,
                                              GetGroupFromRequestMixin, RecordCardGetBaseView):
    """
    Retrieve the Group indicators for IRIS2.
    To be able to see it, the user needs RECARD_CHARTS permission.
    """
    serializer_class = RecordCardManagementIndicatorsSerializer

    def get_response_objects(self):
        group = self.get_indicators_group()
        records = self.get_records(group)
        return self.get_group_indicators(records, group)

    def get_indicators_group(self):
        return self.get_group_from_request(self.request)

    def get_records(self, user_group):
        return RecordCard.objects.filter(responsible_profile=user_group).values(
            "responsible_profile__group_plate").annotate(
            pending_validate=self.get_pending_validate_counter(), processing=self.get_processing_counter(),
            expired=self.get_expired_counter(), near_expire=self.get_near_expire_counter(),
            urgent=self.get_urgent_counter())

    def get_group_indicators(self, records, user_group):
        return {
            "urgent": self.get_indicator_count(records, user_group.group_plate, "urgent"),
            "pending_validation": self.get_indicator_count(records, user_group.group_plate, "pending_validate"),
            "processing": self.get_indicator_count(records, user_group.group_plate, "processing"),
            "expired": self.get_indicator_count(records, user_group.group_plate, "expired"),
            "near_expire": self.get_indicator_count(records, user_group.group_plate, "near_expire"),
        }

    @staticmethod
    def get_urgent_counter():
        return Count("responsible_profile", filter=Q(urgent=True) & ~Q(record_state_id__in=RecordState.CLOSED_STATES))


@method_decorator(name="get", decorator=swagger_auto_schema(
    responses={
        HTTP_200_OK: RecordCardManagementAmbitIndicatorsSerializer,
        HTTP_404_NOT_FOUND: "Group not Found"
    }
))
class RecordCardAmbitManagementIndicatorsView(RecordCardGroupManagementIndicatorsView):
    """
    Retrieve the indicators of the Ambit of the group of the user for IRIS2.
    To be able to see it, the user needs RECARD_CHARTS permission.
    """

    serializer_class = RecordCardManagementAmbitIndicatorsSerializer

    def get_indicators_group(self):
        return get_object_or_404(Group, pk=self.kwargs["group_id"])

    def get_records(self, group):
        return RecordCard.objects.filter(
            responsible_profile__group_plate__startswith=group.group_plate).values(
            "responsible_profile__group_plate").annotate(pending_validate=self.get_pending_validate_counter(),
                                                         processing=self.get_processing_counter(),
                                                         expired=self.get_expired_counter(),
                                                         near_expire=self.get_near_expire_counter())

    def get_group_indicators(self, records, group):
        group_ambit_indicators = {
            "pending_validation": self.get_indicator_count(records, group.group_plate, "pending_validate"),
            "processing": self.get_indicator_count(records, group.group_plate, "processing"),
            "expired": self.get_indicator_count(records, group.group_plate, "expired"),
            "near_expire": self.get_indicator_count(records, group.group_plate, "near_expire"),
            "childrens": []
        }
        self.update_childrens_indicators(group_ambit_indicators, records, group)
        return group_ambit_indicators

    def update_childrens_indicators(self, ambit_indicators, records, group):
        for child_group in group.get_children():
            child_ambit_indicators = {
                "group_id": child_group.pk,
                "group_name": child_group.description,
                "pending_validation": self.get_indicator_count(records, child_group.group_plate, "pending_validate"),
                "processing": self.get_indicator_count(records, child_group.group_plate, "processing"),
                "expired": self.get_indicator_count(records, child_group.group_plate, "expired"),
                "near_expire": self.get_indicator_count(records, child_group.group_plate, "near_expire")
            }
            ambit_indicators["childrens"].append(child_ambit_indicators)


@method_decorator(name="get", decorator=swagger_auto_schema(
    responses={
        HTTP_200_OK: RecordCardMonthIndicatorsSerializer,
    }
))
class RecordCardGroupMonthIndicatorsView(RecordChartPermission, GetGroupFromRequestMixin,
                                         RecordCardIndicatorsMixin, RecordCardGetBaseView):
    """
    Retrieve for a month the Group indicators for IRIS2.
    To be able to see it, the user needs RECARD_CHARTS permission.
    """

    serializer_class = RecordCardMonthIndicatorsSerializer

    def get_response_objects(self):
        user_group = self.get_group_from_request(self.request)
        if self.is_current_month:
            return self.get_current_month_indicators(user_group)
        return self.get_previous_month_indicators(user_group)

    @cached_property
    def is_current_month(self):
        today = timezone.now().date()
        return today.month == self.kwargs["month"] and today.year == self.kwargs["year"]

    def get_current_month_indicators(self, group):
        now = timezone.now()
        date_limit = datetime(now.year, now.month, 1)

        records = self.get_current_month_records(group, date_limit)
        entries_records = self.get_entries(group)
        average_close_days, average_age_days = self.get_current_month_averages(group, date_limit)
        return self.set_current_month_response(records, entries_records, group, average_close_days, average_age_days)

    def get_current_month_records(self, group, date_limit):
        records_filters = self.records_basic_filters(group)
        records = RecordCard.objects.filter(Q(closing_date__isnull=True) | Q(closing_date__gte=date_limit),
                                            **records_filters).values(
            "responsible_profile__group_plate").annotate(
            pending_validate=self.get_pending_validate_counter(), processing=self.get_processing_counter(),
            closed=self.get_closed_counter(), cancelled=self.get_cancelled_counter(),
            external=self.get_external_processing_counter(), pending=self.get_pending_counter()
        )
        return records

    def get_entries(self, group):
        entries_records = RecordCard.objects.filter(**self.records_basic_filters(group)).values(
            "responsible_profile__group_plate").annotate(
            entries=self.get_entries_counter(self.kwargs["year"], self.kwargs["month"], group)
        )
        return entries_records

    @staticmethod
    def records_basic_filters(group):
        return {"responsible_profile": group}

    def get_current_month_averages(self, group, date_limit):
        close_days_filters = self.records_basic_filters(group).copy()
        close_days_filters.update({"record_state_id": RecordState.CLOSED, "closing_date__gte": date_limit})
        average_close_days = RecordCard.objects.filter(**close_days_filters).aggregate(
            close_days=Avg(F("closing_date") - F("created_at")))
        average_close_days = average_close_days["close_days"].days if average_close_days["close_days"] else 0

        age_days_filters = self.records_basic_filters(group).copy()
        age_days_filters.update({
            "record_state_id__in": RecordState.STATES_IN_PROCESSING + RecordState.PEND_VALIDATE_STATES
        })
        average_age_days = RecordCard.objects.filter(
            Q(closing_date__isnull=True) | Q(closing_date__gte=date_limit), **age_days_filters
        ).aggregate(age_days=Avg(timezone.now() - F("created_at")))
        average_age_days = average_age_days["age_days"].days if average_age_days["age_days"] else 0

        return average_close_days, average_age_days

    def set_current_month_response(self, records, entries_records, user_group, average_close_days, average_age_days):
        return {
            "entries": self.get_indicator_count(entries_records, user_group.group_plate, "entries"),
            "pending_validation": self.get_indicator_count(records, user_group.group_plate, "pending_validate"),
            "processing": self.get_indicator_count(records, user_group.group_plate, "processing"),
            "closed": self.get_indicator_count(records, user_group.group_plate, "closed"),
            "cancelled": self.get_indicator_count(records, user_group.group_plate, "cancelled"),
            "external_processing": self.get_indicator_count(records, user_group.group_plate, "external"),
            "pending_records": self.get_indicator_count(records, user_group.group_plate, "pending"),
            "average_close_days": average_close_days,
            "average_age_days": average_age_days
        }

    def get_previous_month_indicators(self, user_group):
        try:
            return MonthIndicator.objects.get(year=self.kwargs["year"], month=self.kwargs["month"],
                                              group=user_group).__dict__
        except MonthIndicator.DoesNotExist:
            return self.empty_indicators

    @property
    def empty_indicators(self):
        return {
            "pending_validation": 0, "processing": 0, "closed": 0, "cancelled": 0, "external_processing": 0,
            "pending_records": 0, "average_close_days": 0, "average_age_days": 0, "entries": 0
        }


@method_decorator(name="get", decorator=swagger_auto_schema(
    responses={
        HTTP_200_OK: RecordCardMonthIndicatorsSerializer,
    }
))
class RecordCardAmbitMonthIndicatorsView(RecordCardGroupMonthIndicatorsView):
    """
    Retrieve the indicators of the Ambit of the group of the user for a month.
    To be able to see it, the user needs RECARD_CHARTS permission.
    """

    @staticmethod
    def records_basic_filters(group):
        return {"responsible_profile__group_plate__startswith": group.group_plate}

    @staticmethod
    def get_entries_counter(year, month, group):
        return Count("responsible_profile",
                     filter=Q(
                         recordcardreasignation__created_at__year=year,
                         recordcardreasignation__created_at__month=month,
                         recordcardreasignation__next_responsible_profile__group_plate__startswith=group.group_plate))

    def get_previous_month_indicators(self, group):
        indicators = MonthIndicator.objects.filter(
            year=self.kwargs["year"], month=self.kwargs["month"], group__group_plate__startswith=group.group_plate)
        if indicators:
            response_indicators = indicators.aggregate(
                pending_validation=Sum("pending_validation"), processing=Sum("processing"), closed=Sum("closed"),
                cancelled=Sum("cancelled"), external_processing=Sum("external_processing"), entries=Sum("entries"),
                pending_records=Sum("pending_records"))

            average_close_days, average_age_days = self.calculate_averages(indicators)

            response_indicators.update({
                "average_close_days": average_close_days,
                "average_age_days": average_age_days,
            })
            return response_indicators
        else:
            return self.empty_indicators

    @staticmethod
    def calculate_averages(indicators):
        sum_avg_close_days = 0
        ambit_closed_records = 0
        sum_avg_age_days = 0
        ambit_age_days = 0

        for indicator in indicators:
            # Only groups with closed records on the month has to be taken in account to c
            sum_avg_close_days += indicator.average_close_days * indicator.closed
            ambit_closed_records += indicator.closed

            sum_avg_age_days += indicator.average_age_days * indicator.pending_records
            ambit_age_days += indicator.pending_records

        average_close_days = int(sum_avg_close_days / ambit_closed_records)
        average_age_days = int(sum_avg_age_days / ambit_age_days)
        return average_close_days, average_age_days


@method_decorator(name="post", decorator=post_record_card_schema_factory(
    responses={
        HTTP_204_NO_CONTENT: "Calculate month indicators task queued",
    }))
class CalculateMonthIndicatorsView(APIView):
    """
    Endpoint to delay task to calculate months indicators
    """

    def post(self, request, *args, **kwargs):
        calculate_month_indicators.delay(self.kwargs["year"], self.kwargs["month"])
        return Response(status=HTTP_204_NO_CONTENT)


@method_decorator(name="get", decorator=swagger_auto_schema(
    operation_id="Record Card Traceability",
    responses={
        HTTP_200_OK: RecordCardTraceabilitySerializer,
        HTTP_404_NOT_FOUND: "RecordCard not found"
    }
))
class RecordCardTraceabilityView(RecordCardGetBaseView):
    """
    Endpoint to retrieve the traceability of a RecordCard, retrieving the record card state history, the record
    comments, the workflow comments and the reasignations.
    """

    serializer_class = RecordCardTraceabilitySerializer
    return_many = True
    record_card = None

    def get_response_objects(self):

        self.record_card = get_object_or_404(RecordCard.objects.select_related("workflow").only("id", "workflow__id"),
                                             pk=self.kwargs["pk"])
        traces = []

        self.set_recordcard_state_history(traces)
        self.set_recordcard_comments(traces)
        if self.record_card.workflow:
            self.set_recordcard_workflow_comments(traces)
        self.set_recordcard_reasignations(traces)

        traces.sort(key=lambda trace_item: trace_item["created_at"], reverse=True)
        return traces

    def set_recordcard_state_history(self, traces):
        """
        Set RecordCard state changes to traces list
        :param traces: trace list to set the records
        :return:
        """
        for state_history in self.record_card.recordcardstatehistory_set.all():
            trace = self.set_basic_trace_info(state_history, RecordCardTraceabilitySerializer.TYPE_STATE)
            trace.update({
                "previous_state": state_history.previous_state_id,
                "next_state": state_history.next_state_id,
                "automatic": state_history.automatic
            })
            traces.append(trace)

    def set_recordcard_comments(self, traces):
        """
        Set RecordCard comments to traces list
        :param traces: trace list to set the records
        :return:
        """
        for comment in self.record_card.comments.all():
            trace = self.set_basic_trace_info(comment, RecordCardTraceabilitySerializer.TYPE_REC_COMMENT)
            trace.update({
                "reason": comment.reason_id if comment.reason else None,
                "comment": comment.comment
            })

            traces.append(trace)

    def set_recordcard_workflow_comments(self, traces):
        """
        Set RecordCard comments to traces list
        :param traces: trace list to set the records
        :return:
        """
        for workflow_comment in self.record_card.workflow.workflowcomment_set.all():
            trace = self.set_basic_trace_info(workflow_comment, RecordCardTraceabilitySerializer.TYPE_WKF_COMMENT)
            trace.update({
                "task": workflow_comment.task,
                "comment": workflow_comment.comment

            })
            traces.append(trace)

    def set_recordcard_reasignations(self, traces):
        """
        Set RecordCard reasignations to traces list
        :param traces: trace list to set the records
        :return:
        """
        for reasignation in self.record_card.recordcardreasignation_set.all():
            trace = self.set_basic_trace_info(reasignation, RecordCardTraceabilitySerializer.TYPE_REASIGN)
            trace.update({
                "previous_responsible": reasignation.previous_responsible_profile.description,
                "next_responsible": reasignation.next_responsible_profile.description,
                "reason": reasignation.reason_id,
                "comment": reasignation.comment
            })
            traces.append(trace)

    @staticmethod
    def set_basic_trace_info(instance, trace_type):
        """
        Methond to set the basic info of a trace
        :param instance: Instance trace
        :param trace_type: Type of trace
        :return:
        """
        return {
            "type": trace_type,
            "created_at": instance.created_at,
            "user_id": instance.user_id,
            "group_name": instance.group.description if hasattr(instance, "group") and instance.group else None
        }


@method_decorator(name="get", decorator=swagger_auto_schema(
    operation_id="Record Card Reasignation Options",
    responses={
        HTTP_200_OK: GroupShortSerializer,
        HTTP_404_NOT_FOUND: "RecordCard not found"
    }
))
class RecordCardReasignationOptionsView(RecordCardGetBaseView):
    """
    Retrieve the possible groups to reasign a RecordCard that has a group.
    If user group has RECARD_REASSIGN_OUTSIDE permission, it will be able to reasgin outside its ambit
    """
    serializer_class = GroupShortSerializer
    return_many = True

    def get_response_objects(self):
        record_card = get_object_or_404(RecordCard, pk=self.kwargs["pk"], enabled=True)
        outside_perm = IrisPermissionChecker.get_for_user(self.request.user).has_permission(RECARD_REASSIGN_OUTSIDE)
        return PossibleReassignations(record_card, outside_perm).reasignations(self.request.user.usergroup.group)


class CheckRecordCardPermissionsMixin(GetGroupFromRequestMixin):

    def group_is_allowed(self, user_group, instance):
        """
        Check if user's groups is allowed to read all the information of the RecordCard or not
        If user group has mayorship permissions or is involved in a conversation of the RecordCard can read
        all the information, else not

        :param user_group: Group assigned to the user
        :param instance: Object to retrieve
        :return: True if user's group has permissions to see all data or is involved in a conversation
        """
        if user_group:
            return instance.group_can_tramit_record(user_group)
        else:
            return False

    def check_record_card_permissions(self, request, serializer):
        record_card = self.get_record_card(serializer)
        user_group = self.get_group_from_request(request)
        if not self.group_is_allowed(user_group, record_card):
            return Response(_("You don't have mayorship permissions to do this actions"), status=HTTP_403_FORBIDDEN)

    def get_record_card(self, serializer):
        raise NotImplementedError


class CheckRecordPermissionsUpdatePatchBaseView(CheckRecordCardPermissionsMixin, UpdatePatchAPIView):

    def patch(self, request, *args, **kwargs):
        permissions_response = self.check_record_card_permissions(request, None)
        if permissions_response:
            return permissions_response

        return self.partial_update(request, *args, **kwargs)

    def get_record_card(self, serializer):
        return self.get_object()


@method_decorator(name="patch", decorator=swagger_auto_schema(
    request_body=RecordCardReasignableSerializer,
    responses={
        HTTP_200_OK: RecordCardReasignableSerializer,
        HTTP_400_BAD_REQUEST: "Bad request: Validation Error",
        HTTP_403_FORBIDDEN: "User has no permissions to do this action",
        HTTP_404_NOT_FOUND: "Not found: resource not exists",
    }
))
class ToogleRecordCardReasignableView(CheckRecordPermissionsUpdatePatchBaseView):
    """
    Endpoint to toogle RecordCard as reasignable or not. The action can only been done if the user has
    NO_REASIGNABLE permission
    """
    serializer_class = RecordCardReasignableSerializer
    queryset = RecordCard.objects.filter(enabled=True)

    def get_permissions(self):
        return [IrisPermission(record_permissions.NO_REASIGNABLE), IsAuthenticated()]


class RelatedObjectRecordCardBaseCreateView(CheckRecordCardPermissionsMixin, CreateAPIView):

    def create(self, request, *args, **kwargs):
        self.serializer = self.get_serializer(data=request.data)
        self.serializer.is_valid(raise_exception=True)

        permissions_response = self.check_record_card_permissions(request, self.serializer)
        if permissions_response:
            return permissions_response

        closed_states_response = self.check_closed_states_actions(self.serializer)
        if closed_states_response:
            return closed_states_response

        self.perform_create(self.serializer)

        headers = self.get_success_headers(self.serializer.data)
        return Response(self.serializer.data, status=HTTP_201_CREATED, headers=headers)

    def get_record_card(self, serializer):
        return serializer.validated_data["record_card"]

    def check_closed_states_actions(self, serializer):
        """
        If record card is closed or cancelled and action can not be done, return HTTP_409.
        Else, do nothing
        """
        return None


@method_decorator(name="post", decorator=create_swagger_auto_schema_factory(
    request_body_serializer=RecordCardReasignationSerializer, responses={
        HTTP_201_CREATED: RecordCardReasignationSerializer,
        HTTP_400_BAD_REQUEST: "Bad request: Validation Error",
        HTTP_403_FORBIDDEN: "Acces not allowed",
        HTTP_409_CONFLICT: "Action can not be done with a closed or cancelled record"
    }))
class RecordCardReasignationView(RelatedObjectRecordCardBaseCreateView):
    """
    Endpoint to reasign a RecordCard from group to another.
    The action can not be done to a record in a closed state.

    """
    serializer_class = RecordCardReasignationSerializer

    def create(self, request, *args, **kwargs):
        resp = super().create(request, *args, **kwargs)
        resp.data = RecordCardDetailSerializer(self.get_record_card(self.serializer), context={"request": request}).data
        return resp

    def get_record_card(self, serializer):
        return serializer.validated_data["record_card"]

    def check_closed_states_actions(self, serializer):
        """
        If record card is closed or cancelled and action can not be done, return HTTP_409.
        Else, do nothing
        """
        record_card = self.get_record_card(serializer)
        if record_card.record_state_id in RecordState.CLOSED_STATES:
            return Response(_("Action can not be done with a closed or cancelled record"), status=HTTP_409_CONFLICT)

    def get_permissions(self):
        return [IrisPermission(record_permissions.RECARD_REASIGN), IsAuthenticated()]


class RecordCardMultiRecordsView(BasicMasterListApiView):
    """
    Given a record card, it retrieves a list of the multirecords. If record card is not a multirecord,
    return itself to allow to set the first multirecord
    """

    serializer_class = RecordCardMultiRecordstListSerializer

    def get_queryset(self):
        try:
            record_card = self.get_record_cards().get(pk=self.kwargs["id"])
        except RecordCard.DoesNotExist:
            return []

        if not record_card.is_multirecord:
            # If record card is not a multirecord, return itself to allow to set the first multirecord
            return [record_card]

        if record_card.multirecord_from:
            records_list = [record_card.multirecord_from]
            records_list += list(self.get_record_cards().filter(multirecord_from_id=record_card.multirecord_from_id))
        else:
            records_list = [record_card]
            records_list += list(self.get_record_cards().filter(multirecord_from_id=record_card.pk))

        return records_list

    def get_record_cards(self):
        return RecordCard.objects.select_related("record_state", "element_detail", "element_detail__element",
                                                 "element_detail__element__area")


@method_decorator(name="patch", decorator=swagger_auto_schema(
    request_body=RecordCardUrgencySerializer,
    responses={
        HTTP_200_OK: RecordCardUrgencySerializer,
        HTTP_403_FORBIDDEN: "User has no permissions to do this action",
        HTTP_404_NOT_FOUND: "RecordCard could not change its urgency",
        HTTP_409_CONFLICT: "Action can not be done with a closed or cancelled record"
    }
))
class ToogleRecordCardUrgencyView(CheckRecordPermissionsUpdatePatchBaseView):
    """
    Toogle urgent flag of the record. The action can not be done with a closed state.
    """

    serializer_class = RecordCardUrgencySerializer
    queryset = RecordCard.objects.filter(enabled=True)

    def patch(self, request, *args, **kwargs):
        permissions_response = self.check_record_card_permissions(request, None)
        if permissions_response:
            return permissions_response

        record_card = self.get_object()
        if record_card.record_state_id in RecordState.CLOSED_STATES:
            return Response(_("Action can not be done with a closed or cancelled record"), status=HTTP_409_CONFLICT)

        return self.partial_update(request, *args, **kwargs)


@method_decorator(name="post", decorator=post_record_card_schema_factory(
    "block", responses={
        HTTP_200_OK: RecordCardBlockSerializer,
        HTTP_403_FORBIDDEN: "Acces not allowed",
        HTTP_404_NOT_FOUND: "RecordCard could not be blocked/unblocked",
        HTTP_409_CONFLICT: "RecordCard is blocked",
    }))
class RecordCardBlockView(RecordCardActions):
    """
    Endpoint to block a RecordCard when a user is working on it.
    When a RecordCard is blocked by a user, the SPA won't allow another user to do any action on the RecordCard.
    """

    response_data = {}
    message = None

    @cached_property
    def record_card(self):
        """
        Get record card instance
        :return: RecordCard
        """
        return get_object_or_404(RecordCard, pk=self.kwargs["pk"], enabled=True)

    def check_recordcard_block(self, request):
        """
        Check if RecordCard is blocked.
        :param request:
        :return: If RecordCard is blocked, return conflict Response
        """
        if self.record_card.is_blocked(get_user_traceability_id(request.user)):
            return Response(RecordCardBlockSerializer(instance=self.record_card.current_block).data,
                            status=HTTP_409_CONFLICT)

    def do_record_card_action(self):
        """
        Block or unblock RecordCard
        :return:
        """
        blocked_response = self.check_recordcard_block(self.request)
        if blocked_response:
            return blocked_response
        self.set_record_card_block()

    def set_record_card_block(self):
        """
        Create or update RecordCardBlock from user
        """
        try:
            self.block = RecordCardBlock.objects.get(record_card_id=self.record_card.pk,
                                                     user_id=get_user_traceability_id(self.request.user))
        except RecordCardBlock.DoesNotExist:
            self.block = RecordCardBlock()
            self.block.record_card_id = self.record_card.pk
            self.block.user_id = get_user_traceability_id(self.request.user)
        expire_delta_time = int(Parameter.get_parameter_by_key("TEMPS_TREBALL_FITXA", 10))
        self.block.expire_time = timezone.now() + timedelta(minutes=expire_delta_time)
        self.block.save()

    def send_response(self):
        """
        Send view response
        :return: View Response with toogle record card block data
        """
        return Response(RecordCardBlockSerializer(instance=self.block).data, status=HTTP_200_OK)


@method_decorator(name="post", decorator=post_record_card_schema_factory(
    "validate", responses={
        HTTP_200_OK: "Validation check",
        HTTP_204_NO_CONTENT: "RecordCard validated",
        HTTP_403_FORBIDDEN: "Acces not allowed",
        HTTP_404_NOT_FOUND: "RecordCard could not be validated",
        HTTP_409_CONFLICT: "RecordCard could not be validated with indicated Record because they are not similar",
    }))
class RecordCardValidateView(SetRecordStateHistoryMixin, RecordStateChangeAction):
    """
    Endpoint to Validate a RecordCard. It changes the state of the RecordCard from
    PENDING_VALIDATE (or EXTERNAL_RETURNED) to the next state of the process.
    If the theme or the process indicates that the RecordCard has to be validated with an external service, the external
    validation is executed and the RecordCard is only validated in case of success.

    At this step, the workflow (process) of the RecordCard is created or assignated. If a RecordCard is validated to a
    similar RecordCard, it will be added to the workflow. If it's not, a new workflow will be created.

    On the check endpoint, an extra list of possible similar record card will be returned.
    """
    record_card_initial_state = RecordState.PENDING_VALIDATE
    response_serializer_class = RecordCardValidateCheckSerializer
    permission = record_permissions.VALIDATE

    @cached_property
    def record_card(self):
        """
        Get record card instance
        :return: RecordCard
        """
        return get_object_or_404(RecordCard.objects.select_related("request", "ubication"), pk=self.kwargs["pk"],
                                 record_state_id__in=[RecordState.PENDING_VALIDATE, RecordState.EXTERNAL_RETURNED])

    def do_check_action(self):
        super().do_check_action()
        ex_service = self.record_card.element_detail.external_service
        self.response_data['__action__'].update({
            'external_service': getattr(ex_service, 'sender_uid', None),
            'ask_for_external_service': bool(not self.record_card.external_is_mandatory and ex_service),
            'external_service_name': getattr(self.record_card.element_detail.external_service, 'name', None),
        })

    def do_record_card_action(self):
        """
        Validate record card and set the workflow
        :return:
        """
        external_validator = get_external_validator(self.record_card)
        send_external = self.request.data.get('send_external') or getattr(
            external_validator, "force_send_external", None)
        if self.record_card.has_to_external_validate(external_validator, send_external):
            if not external_validator.validate(**self.request.data):
                return Response(_("Cannot send the record card to the external management service"),
                                status=HTTP_400_BAD_REQUEST)

        validation_kwargs = self.get_validation_kwargs()
        if isinstance(validation_kwargs, Response):
            return validation_kwargs

        handle_state_chage_kwargs = validation_kwargs.copy()
        handle_state_chage_kwargs["send_external"] = self.request.data.get('send_external')
        if not external_validator or not external_validator.handle_state_change(**handle_state_chage_kwargs):
            self.record_card.validate(**validation_kwargs)

    def get_validation_kwargs(self):
        validate_kwargs = {
            "user_department": self.request.user.imi_data.get('dptcuser', ''),
            "user": self.request.user,
            "next_state_code": self.record_card.next_step_code
        }
        similar_record_pk = self.request.data.get("similar")
        if similar_record_pk:
            similar_record = get_object_or_404(RecordCard, pk=similar_record_pk, enabled=True)
            if not self.record_card.check_similarity(similar_record, self.request.user):
                return Response(_("RecordCard could not be validated with indicated Record because "
                                  "they are not similar"), status=HTTP_409_CONFLICT)
            validate_kwargs["similar_record"] = similar_record
        return validate_kwargs

    def do_record_card_extra_action(self):
        """
        Perform extra actions on RecordCard after the main transaction
        Review possible similar records from validated record card, in order that the alarm is setted
        :return:
        """
        super().do_record_card_extra_action()
        register_possible_similar_records.delay(self.record_card.pk)

    def check_valid(self):
        """
        Check data validity
        :return: Return response data
        """
        confirmation_info = {}
        if self.record_card.can_be_validated:
            confirmation_info["can_confirm"] = True
            confirmation_info["reason"] = None
        else:
            confirmation_info["can_confirm"] = False
            confirmation_info["reason"] = _("RecordCard could not be validated due to its validation time has expired."
                                            "Validation date: {}").format(
                self.record_card.validate_date_limit.strftime("%d-%m-%Y"))
        return confirmation_info, {}

    def get_record_next_group(self):
        """
        :return: Next RecordCard group
        """
        derivate_group = self.record_card.derivate(get_user_traceability_id(self.request.user), is_check=True,
                                                   next_state_id=self.record_card.next_step_code)
        return derivate_group if derivate_group else self.record_card.responsible_profile

    def get_extra_response_data(self):
        """
        :return: Extra response data for check action
        """
        main_similar_record_ids = self.record_card.possible_similar.filter(
            record_state_id__in=RecordState.STATES_IN_PROCESSING).values_list(
            "workflow__main_record_card_id", flat=True)
        return {
            "possible_similar": RecordCard.objects.filter(pk__in=main_similar_record_ids).only("id", "description",
                                                                                               "normalized_record_id")
        }


@method_decorator(name="post", decorator=post_record_card_schema_factory(
    request_body_serializer=RecordCardCancelSerializer,
    responses={
        HTTP_201_CREATED: "RecordCard canceled and internal claim created",
        HTTP_204_NO_CONTENT: "RecordCard canceled",
        HTTP_400_BAD_REQUEST: "Bad request: Validation Error",
        HTTP_403_FORBIDDEN: "Acces not allowed",
        HTTP_404_NOT_FOUND: "RecordCard is not available to cancel"
    }
))
class RecordCardCancelView(SetRecordStateHistoryMixin, RecordStateChangeAction):
    """
    Endpoint to cancel a RecordCard. If the Reason to cancel the RecordCard is VALIDATION_BY_ERROR or by expiration,
    a new RecordCard will be created, as an internal claim. If the Reason is the duplicity repetition, the record_id of
    the duplicated record will be added to the cancellation comment for traceability.

    """
    record_card_initial_state = RecordState.CANCELLED
    permission = record_permissions.CANCEL

    @cached_property
    def record_card(self):
        """
        Get record card instance
        :return: RecordCard
        """
        return get_object_or_404(RecordCard, ~Q(record_state__id=self.get_record_card_initial_state()),
                                 pk=self.kwargs["pk"], enabled=True)

    def do_record_card_action(self):
        """
        Do RecordAction must be implemented in each view
        :return:
        """
        self.claim = None
        group = self.get_group_from_request(self.request)
        cancel_serializer = RecordCardCancelSerializer(data=self.request.data,
                                                       context={"record_card": self.record_card, "group": group})
        if cancel_serializer.is_valid(raise_exception=True):
            reason_id = cancel_serializer.data["reason"]
            comment = cancel_serializer.data["comment"]
            expiration_reason_id = int(Parameter.get_parameter_by_key("REABRIR_CADUCIDAD", 17))
            duplicity_repetition_reason_id = int(Parameter.get_parameter_by_key("DEMANAR_FITXA", 1))

            if reason_id == Reason.VALIDATION_BY_ERROR or reason_id == expiration_reason_id:
                self.create_internal_claim()
            elif reason_id == duplicity_repetition_reason_id:
                comment += " - {}".format(cancel_serializer.data["duplicated_record_card"])

            self.perform_state_change(RecordState.CANCELLED, group)
            self.record_card.register_audit_field("close_user", get_user_traceability_id(self.request.user))
            Comment.objects.create(record_card=self.record_card, comment=comment, reason_id=reason_id,
                                   user_id=get_user_traceability_id(self.request.user), group=group)

    def create_internal_claim(self):
        """
        Create internal claim and sent a notification email to applicant
        :return:
        """
        self.claim = self.record_card.create_record_claim(get_user_traceability_id(self.request.user), self.record_card.description,
                                                          set_to_internal_claim=True)
        self.claim.update_claims_number()
        if self.claim.record_can_be_autovalidated():
            self.claim.autovalidate_record(self.request.user.imi_data.get('dptcuser'), self.request.user)

        applicant_email = self.get_applicant_email()
        if applicant_email:
            extra_context = {"new_normalized_id": self.claim.normalized_record_id,
                             "old_normalized_id": self.record_card.normalized_record_id}
            old_lang = translation.get_language()
            translation.activate(self.record_card.recordcardresponse.language)
            InternalClaimEmail().send(from_email=settings.DEFAULT_FROM_EMAIL,
                                      to=[applicant_email], extra_context=extra_context)
            translation.activate(old_lang)

    def do_record_card_extra_action(self):
        super().do_record_card_extra_action()
        if self.claim:
            send_allocated_notification.delay(self.claim.responsible_profile_id, self.claim.pk)
            if self.record_card.recordfile_set.exists():
                group = self.get_group_from_request(self.request)
                self.claim.copy_files(group, self.record_card.pk)

    def get_applicant_email(self):
        """
        Try to get the applicant emails from record card response or from the applicant response.

        :return: applicant email or none
        """
        applicant_email = None
        has_response = hasattr(self.record_card, "recordcardresponse")
        if has_response and self.record_card.recordcardresponse.response_channel_id == ResponseChannel.EMAIL:
            applicant_email = self.record_card.recordcardresponse.address_mobile_email
        else:
            applicant = self.record_card.request.applicant
            if hasattr(applicant, "applicantresponse") and applicant.applicantresponse.email:
                applicant_email = applicant.applicantresponse.email
        return applicant_email

    def send_response(self):
        """
        Send view response
        :return: View Response
        """
        if self.claim:
            return Response(data=RecordCardShortNotificationsSerializer(self.claim).data, status=HTTP_201_CREATED)

        return Response(status=HTTP_204_NO_CONTENT)


@method_decorator(name="post", decorator=post_record_card_schema_factory("close"))
class RecordCardCloseView(SetRecordStateHistoryMixin, RecordStateChangeAction):
    """
    Endpoint to set the state CLOSED to a RecordCard and register the user that has done the action.
    """

    record_card_initial_state = RecordState.CLOSED

    @cached_property
    def record_card(self):
        """
        Get record card instance
        :return: RecordCard
        """
        return get_object_or_404(RecordCard, ~Q(record_state__id=self.get_record_card_initial_state()),
                                 pk=self.kwargs["pk"], enabled=True)

    def do_record_card_action(self):
        """
        Close record card
        :return:
        """
        self.perform_state_change(RecordState.CLOSED)
        self.record_card.register_audit_field("close_user", get_user_traceability_id(self.request.user))


@method_decorator(name="post", decorator=post_record_card_schema_factory("external processing"))
class RecordCardExternalProcessingView(SetRecordStateHistoryMixin, RecordStateChangeAction):
    """
    Endpoint to set the state EXTERNAL_PROCESSING to a RecordCard
    """

    record_card_initial_state = RecordState.EXTERNAL_PROCESSING

    @cached_property
    def record_card(self):
        """
        Get record card instance
        :return: RecordCard
        """
        return get_object_or_404(RecordCard, ~Q(record_state__id=self.get_record_card_initial_state()),
                                 pk=self.kwargs["pk"], enabled=True)

    def do_record_card_action(self):
        """
        Close record card
        :return:
        """
        self.perform_state_change(RecordState.EXTERNAL_PROCESSING)


@method_decorator(name="post", decorator=post_record_card_schema_factory("external processing and email"))
class RecordCardExternalProcessingEmailView(SetRecordStateHistoryMixin, RecordStateChangeAction):
    """
    Endpoint to set the state EXTERNAL_PROCESSING to a RecordCard and send an email to the external tramitator.
    """

    record_card_initial_state = RecordState.EXTERNAL_PROCESSING

    @cached_property
    def record_card(self):
        """
        Get record card instance
        :return: RecordCard
        """
        return get_object_or_404(RecordCard, ~Q(record_state__id=self.get_record_card_initial_state()),
                                 pk=self.kwargs["pk"], enabled=True)

    def do_record_card_action(self):
        """
        Close record card
        :return:
        """
        self.perform_state_change(RecordState.EXTERNAL_PROCESSING)
        ExternalTramitationEmail(self.record_card).send()


class RecordResponseBaseView(SetRecordStateHistoryMixin, RecordCardActions):
    """
    Base View for record actions related to the response of the record.
    The possible actions are: draft answer and a the answer.
    """
    record_card_initial_state = RecordState.PENDING_ANSWER

    def get_response_instance(self, record_id):
        """

        :return: If exists returns RecordCardTextResponse instance, else None
        """
        return RecordCardTextResponse.objects.filter(record_card_id=record_id).order_by("created_at").first()

    def get_response_serializer(self):
        """

        :return: RecordCardTextResponseSerializer instance
        """
        return RecordCardTextResponseSerializer(instance=self.get_response_instance(self.record_card.id),
                                                data=self.request.data,
                                                context={"record_card": self.record_card, "request": self.request})

    @cached_property
    def user_group(self):
        return self.get_group_from_request(self.request)


@method_decorator(name="post", decorator=post_record_card_schema_factory(
    "answer", responses={
        HTTP_204_NO_CONTENT: "RecordCard save draft answer",
        HTTP_400_BAD_REQUEST: "Bad request: Validation Error",
        HTTP_403_FORBIDDEN: "Acces not allowed",
        HTTP_404_NOT_FOUND: "RecordCard is not available to save draft answer"
    }, request_body_serializer=RecordCardTextResponseSerializer))
class RecordCardDraftAnswerView(RecordResponseBaseView):
    """
    Save a draft answer for the RecordCard
    """
    permission = record_permissions.RECARD_SAVE_ANSWER

    def do_record_card_action(self):
        """
        Save a draft answer for the RecordCard

        :return:
        """
        response_serializer = self.get_response_serializer()
        if response_serializer.is_valid(raise_exception=True):
            response_serializer.save()


@method_decorator(name="post", decorator=post_record_card_schema_factory(
    "answer", responses={
        HTTP_204_NO_CONTENT: "RecordCard answer",
        HTTP_400_BAD_REQUEST: "Bad request: Validation Error",
        HTTP_403_FORBIDDEN: "Acces not allowed",
        HTTP_404_NOT_FOUND: "RecordCard is not available to answer",
        HTTP_409_CONFLICT: "User group can not answer it",
    }, request_body_serializer=RecordCardTextResponseSerializer))
class RecordCardAnswerView(RecordStateChangeMixin, RecordResponseBaseView):
    """
    If the user's group is allowed to answer the RecordCard, answer the RecordCard. After saving the answer, it closes
    the RecordCard.
    """
    permission = record_permissions.RECARD_ANSWER

    def do_record_card_action(self):
        """
        Answer and close the RecordCard
        :return:
        """

        user_group = self.get_group_from_request(self.request)
        if not self.record_card.group_can_answer(user_group)["can_answer"]:
            return Response(_("User's group can not answer the RecordCard as it's not an ambit coordinator"),
                            status=HTTP_409_CONFLICT)

        response_serializer = self.get_response_serializer()
        if response_serializer.is_valid(raise_exception=True):
            response_serializer.save()

            self.perform_state_change(RecordState.CLOSED, group=user_group)


@method_decorator(name="post", decorator=post_record_card_schema_factory(
    "answer", responses={
        HTTP_204_NO_CONTENT: "RecordCard answer",
        HTTP_400_BAD_REQUEST: "Bad request: Validation Error",
        HTTP_403_FORBIDDEN: "Acces not allowed",
        HTTP_404_NOT_FOUND: "RecordCard is not available to answer",
        HTTP_409_CONFLICT: "User group can not answer it",
    }, request_body_serializer=RecordCardTextResponseSerializer))
class WorkflowAnswerView(RecordStateChangeMixin, WorkflowActions):
    """
    It answers all the RecordCard of a workflow. This action can only be done if the RecordCard are on state
    PENDING_ANSWER. After the validation of the received answers, the process checks if all the RecordCards of the
    workflow has an answer. Once the answers are registered, all the RecordCards will be closed.
    """

    workflow_initial_state = RecordState.PENDING_ANSWER
    permission = record_permissions.RECARD_ANSWER

    def do_workflow_action(self):
        """
        Answer and close the RecordCard
        :return:
        """
        answers = self.save_answers()
        resp = self.check_answers(answers)
        if resp:
            return resp
        self.forward_workflow()

    @cached_property
    def perms(self):
        return IrisPermissionChecker.get_for_user(self.request.user)

    @cached_property
    def allow_avoid_send(self):
        return self.perms.has_permission(RECARD_ANSWER_NOSEND)

    @cached_property
    def allow_avoid_send_sicon(self):
        return self.perms.has_permission(RECARD_ANSWER_NO_LETTER)

    def do_workflow_extra_action(self):
        for record_card in self.answer_records:
            record_card.send_record_card_state_changed()

    def save_answers(self):
        """
        Saves all the answers sent.
        :return: Saved answers
        """
        answers = {}
        for answer in self.request.data:
            record_answer = self.get_response_instance(answer.get("record_card"))
            response_serializer = RecordCardTextResponseSerializer(
                instance=record_answer,
                data=answer,
                context={},
            )
            if response_serializer.is_valid(raise_exception=True) and self.check_avoid_send(response_serializer):
                if response_serializer.record_card.record_state_id != RecordState.PENDING_ANSWER:
                    raise ValidationError(_("You can only answer records in pending answer state."))
                response_serializer.save()
            answers[response_serializer.instance.record_card_id] = response_serializer.instance
        return answers

    def check_avoid_send(self, ser):
        instance, answer = ser.instance, ser.validated_data
        if answer.get('avoid_send', False):
            if self.allow_avoid_send or getattr(instance, 'is_letter', False) and self.allow_avoid_send_sicon:
                return True
            raise ValidationError("You don't have permissions for avoiding sending answer.")
        return True

    def check_answers(self, answers):
        """
        Checks if all the required answers are saved and the workflow can advance to the next state.
        :param answers: Answers saved by the save_answers method.
        :return: Response if the answers are invalid.
        """
        missing_ids = [rr.pk for rr in self.required_records if rr.id not in answers]
        if missing_ids:
            return Response(_("You must write an answer for all records before closing this process."),
                            status=HTTP_400_BAD_REQUEST)

    def forward_workflow(self):
        """
        Advances the workflow to the next state, in this case closed.
        """
        if self.required_records:
            closing_date = timezone.now()
            initial_state = self.required_records[0].record_state_id
            self.required_records.update(
                record_state_id=RecordState.CLOSED,
                updated_at=closing_date,
                close_department=self.request.user.imi_data.get('dptcuser', ''),
                closing_date=closing_date,
            )
            history = []
            user_id = get_user_traceability_id(self.request.user)
            for record_card in self.answer_records:
                # Ensure fields are available for cityos
                record_card.close_department = self.request.user.imi_data.get('dptcuser', '')
                record_card.closing_date = closing_date
                record_card.record_state_id = RecordState.CLOSED
                # Will trigger cityos send with this record_card instance
                record_card.derivate(user_id)
                post_save.send(sender=RecordCard, instance=record_card)
                record_card.register_audit_field("close_user", user_id)
                history.append(RecordCardStateHistory(
                    record_card=record_card, group=self.user_group, previous_state_id=initial_state,
                    next_state_id=record_card.record_state_id, user_id=user_id, automatic=False
                ))
            RecordCardStateHistory.objects.bulk_create(history)
        self.workflow.state_change(RecordState.CLOSED)

    @cached_property
    def record_card(self):
        """
        Get record card instance
        :return: RecordCard
        """
        return self.workflow.main_record_card

    @cached_property
    def answer_records(self):
        return self.workflow.recordcard_set.exclude(
            recordcardresponse__response_channel__in=ResponseChannel.NON_RESPONSE_CHANNELS,
        ).select_related("request", "request__applicant", "recordcardresponse")

    @cached_property
    def required_records(self):
        """
        :return: Returns the list of records that has to be answered in the workflow.
        """
        return self.answer_records.filter(
            record_state_id__in=RecordState.STATES_IN_PROCESSING
        )

    def get_response_instance(self, record_id):
        """

        :return: If exists returns RecordCardTextResponse instance, else None
        """
        return RecordCardTextResponse.objects.annotate(
            response_channel=F('record_card__recordcardresponse__response_channel_id')
        ).filter(record_card_id=record_id).order_by("created_at").first()

    @cached_property
    def user_group(self):
        return self.get_group_from_request(self.request)


@method_decorator(name="post",
                  decorator=post_record_card_schema_factory(
                      request_body_serializer=ClaimDescriptionSerializer,
                      responses={
                          HTTP_200_OK: "RecordCard claim check",
                          HTTP_201_CREATED: "RecordCard claim created",
                          HTTP_400_BAD_REQUEST: "Bad request: Validation Error",
                          HTTP_403_FORBIDDEN: "Acces not allowed",
                          HTTP_404_NOT_FOUND: "RecordCard is not available to claim",
                          HTTP_409_CONFLICT: "RecordCard claim can not be created",
                      }))
class RecordCardClaimView(RecordCardActions):
    """
    View to create a claim of a closed/cancelled RecordCard

    Conditions to be able to create a claim:

    * RecordCard state has to be closed or cancelled
    * Can not exist a previous claim on the same RecordCard
    * RecordCard has been closed less than the CLAIM_DAYS_LIMIT ago
    """
    serializer_class = ClaimDescriptionSerializer
    response_serializer_class = RecordCardClaimCheckSerializer
    permission = record_permissions.RECARD_CLAIM

    # Claim types
    CLAIM_COMMENT = "comment"
    CLAIM_RECORD = "record"
    NO_CLAIM = None

    @cached_property
    def record_card(self):
        """
        Get record card instance, we need to get the last record from the claim chain.
        :return: RecordCard
        """
        return get_object_or_404(RecordCard, pk=self.kwargs["pk"], enabled=True)

    def check_restricted_action(self, request):
        """
        Anyone can claim records, no matter if the record pertains to the user group ambit.
        """
        pass

    def check_valid(self):
        """
        Check data validity
        :return: Return response data
        """
        confirmation_info = {}

        try:
            ClaimValidation(self.record_card).validate()
            # New claim can be created
            confirmation_info["can_confirm"] = True
            confirmation_info["reason"] = None
            confirmation_info["claim_type"] = self.CLAIM_RECORD
        except RecordClaimException as claim_exception:
            confirmation_info["can_confirm"] = False
            confirmation_info["reason"] = claim_exception.message
            if claim_exception.must_be_comment:
                confirmation_info["claim_type"] = self.CLAIM_COMMENT
                confirmation_info["reason_comment_id"] = Reason.CLAIM_CITIZEN_REQUEST
            else:
                confirmation_info["claim_type"] = self.NO_CLAIM

        return confirmation_info, {}

    def get_record_next_state(self):
        """
        In a claim, the

        :return: Next RecordCard state code.
        """
        if self.record_card.record_state_id not in RecordState.CLOSED_STATES:
            return self.record_card.record_state
        return RecordState.objects.get(pk=RecordState.PENDING_VALIDATE)

    def get_record_next_group(self):
        """
        :return: Next RecordCard group assigned to claim
        """
        derivate_group = self.record_card.derivate(get_user_traceability_id(self.request.user),
                                                   next_state_id=RecordState.PENDING_VALIDATE, is_check=True)
        return derivate_group if derivate_group else self.record_card.responsible_profile

    def do_record_card_action(self):
        """
        First it checks if a claim can be created (conditions on the view). If it can be done, it creates a claim.
        :return:
        """
        self.claim = None
        try:
            ClaimValidation(self.record_card).validate()
        except RecordClaimException as claim_exception:
            return Response(claim_exception.message, status=HTTP_409_CONFLICT)

        claim_serializer = self.get_serializer_class()(data=self.request.data)
        if claim_serializer.is_valid(raise_exception=True):
            self.claim = self.record_card.create_record_claim(
                get_user_traceability_id(self.request.user),
                claim_serializer.validated_data["description"],
                creation_department=self.request.user.imi_data.get('dptcuser', '')
            )
            self.claim.update_claims_number()
            if self.claim.record_can_be_autovalidated():
                user = self.request.user if self.request else None
                self.claim.autovalidate_record(self.request.user.imi_data.get('dptcuser'), user)

    def do_record_card_extra_action(self):
        if self.claim:
            send_allocated_notification.delay(self.claim.responsible_profile_id, self.claim.pk)

    def send_response(self):
        """
        Send view response, with data of claim created
        :return: View Response
        """
        return Response(status=HTTP_201_CREATED, data=ClaimShortSerializer(instance=self.claim).data)


@method_decorator(name="post",
                  decorator=post_record_card_schema_factory(
                      request_body_serializer=RecordCardThemeChangeSerializer,
                      responses={
                          HTTP_200_OK: "RecordCard theme change check",
                          HTTP_204_NO_CONTENT: "RecordCard theme changed",
                          HTTP_400_BAD_REQUEST: "Bad request: Validation Error",
                          HTTP_403_FORBIDDEN: "Acces not allowed",
                          HTTP_404_NOT_FOUND: "RecordCard is not available to claim",
                          HTTP_409_CONFLICT: "Action can not be done with a cancelled record"
                      }))
class RecordCardThemeChangeView(RecordCardActions):
    """
    View to change the record card theme. To perform the actions, the new theme and it'"'s features have to be sent.
    In addition, a flag can be sent to indicate if the theme derivation has to be applied. The default flag value
    is True.
    """

    serializer_class = RecordCardThemeChangeSerializer
    permission = record_permissions.THEME_CHANGE

    @cached_property
    def record_card(self):
        """
        Get record card instance
        :return: RecordCard
        """
        return get_object_or_404(RecordCard, pk=self.kwargs["pk"], enabled=True)

    def check_closed_states_actions(self):
        """
        If record card is closed or cancelled and action can not be done, return HTTP_409.
        Else, do nothing
        """
        if self.record_card.record_state_id == RecordState.CLOSED:
            return
        return Response(_("Action can not be done with a cancelled record"), status=HTTP_409_CONFLICT)

    def do_record_card_action(self):
        """
        Do RecordAction must be implemented in each view
        :return:
        """
        theme_change_serializer = self.get_change_theme_serializer()
        if theme_change_serializer.is_valid(raise_exception=True):
            self.record_autovalidate = False
            new_element_detail = theme_change_serializer.validated_data["element_detail"]
            if self.record_card.record_can_be_autovalidated(new_element_detail=new_element_detail):
                self.record_autovalidate = True

            theme_change_serializer.save()
            if self.record_card.workflow:
                self.change_theme_workflow_records(theme_change_serializer)

    def change_theme_workflow_records(self, theme_change_serializer):
        records = self.record_card.workflow.recordcard_set.exclude(pk=self.record_card.pk)
        for record in records:
            theme_change_serializer.instance = record
            theme_change_serializer.save()

    def do_record_card_extra_action(self):
        """
        Perform extra actions on RecordCard after the main transaction
        :return:
        """
        if self.record_autovalidate:
            self.record_card.send_record_card_state_changed()
        elif not self.record_card.workflow:
            register_possible_similar_records.delay(self.record_card.pk)

    def check_valid(self):
        """
        Check data validity
        :return: Return response data
        """
        confirmation_info = {}
        serializer = self.get_change_theme_serializer()
        if serializer.is_valid():
            confirmation_info["can_confirm"] = True
            confirmation_info["reason"] = None
        else:
            confirmation_info["can_confirm"] = False
            confirmation_info["reason"] = _("Post data are invalid")
        self.validated_data = serializer.validated_data
        return confirmation_info, serializer.errors

    def get_change_theme_serializer(self):
        """
        :return: Theme change serializer instance
        """
        return self.get_serializer_class()(instance=self.record_card, data=self.request.data,
                                           context={"request": self.request})

    def get_record_next_group(self):
        """
        :return: Next RecordCard group
        """
        new_element_detail_id = self.request.data.get("element_detail_id")
        if not new_element_detail_id:
            return self.record_card.responsible_profile
        if self.is_check and self.validated_data.get('ubication'):
            self.record_card.ubication = Ubication(**self.validated_data.get('ubication'))
        derivate_group = self.record_card.derivate(get_user_traceability_id(self.request.user), is_check=True,
                                                   new_element_detail_id=new_element_detail_id,
                                                   next_state_id=self.get_record_next_state().pk,
                                                   next_district_id=self.get_next_district())
        return derivate_group if derivate_group else self.record_card.responsible_profile

    def get_next_district(self):
        try:
            return int(self.request.data.get('ubication', {}).get('district', None))
        except TypeError:
            return None

    def get_record_next_state(self):
        """
        :return: Next RecordCard state code
        """
        try:
            new_element_detail = ElementDetail.objects.get(pk=self.request.data.get("element_detail_id"))
        except ElementDetail.DoesNotExist:
            return self.record_card.record_state

        if self.record_card.record_can_be_autovalidated(new_element_detail):
            record_copy = deepcopy(self.record_card)
            record_copy.process_id = new_element_detail.process_id
            record_copy.record_state_id = RecordState.PENDING_VALIDATE
            try:
                return RecordState.objects.get(pk=record_copy.next_step_code)
            except RecordState.DoesNotExist:
                return self.record_card.record_state
        else:
            return self.record_card.record_state


class RecordCardAnswerResponseView(RetrieveAPIView):
    """
    Endpoint to retrieve the answer of a RecordCard.
    """
    permission_classes = (IsAuthenticated,)
    serializer_class = RecordCardTextResponseSerializer
    queryset = RecordCardTextResponse.objects.filter(enabled=True)

    def get_object(self):
        return get_object_or_404(RecordCardTextResponse, record_card_id=self.kwargs["pk"], enabled=True)


class RecordsExportExtraQuerysetMixin(RecordCardExcelExportListMixin):
    def get_queryset(self):
        if self.request.META.get("HTTP_ACCEPT") != self.EXCEL_MIME_TYPE:
            return super().get_queryset()

        return self.queryset_export_extras(self.excel_queryset)

    @property
    def excel_queryset(self):
        return RecordCard.objects.none()


@method_decorator(name="get", decorator=list_swagger_auto_schema_factory(RecordCardListRegularSerializer))
class RecordCardPendingValidationListView(RecordsExportExtraQuerysetMixin, RecordCardResponsibleProfileMixin,
                                          RecordCardListOrderingMixin, BasicMasterListApiView):
    """
    List of records PENDING VALIDATE for a group (its own records and his descendants).
    The endpoint:
     - can be exported to excel
     - can be filtered by themes, masters, alarms, etc
     - uses a regular serializer to improve the performance
    """
    serializer_class = RecordCardListRegularSerializer
    filterset_class = RecordCardFilter
    queryset = RecordCard.objects.filter(
        record_state_id__in=RecordState.PEND_VALIDATE_STATES).order_by(
        "-urgent", F("ans_limit_date").asc(nulls_last=True), "created_at").select_related(
        "ubication", "ubication__district", "request", "request__applicant", "workflow")
    filename = "pending-tasks.xlsx"
    permission_classes = (IsAuthenticated,)

    @property
    def excel_queryset(self):
        queryset = RecordCard.objects.filter(
            record_state_id__in=RecordState.PEND_VALIDATE_STATES).order_by(
            "-urgent", F("ans_limit_date").asc(nulls_last=True), "created_at").select_related(
            "element_detail", "element_detail__element", "element_detail__element__area", "record_state",
            "responsible_profile", "record_type", "ubication", "ubication__district", "request", "request__applicant",
            "workflow")
        return self.filter_queryset_by_group_plate(queryset)

    def get_serializer_class(self):
        if 'map' in self.request.GET:
            return RecordUbicationListSerializer
        return super().get_serializer_class()

    def paginate_queryset(self, queryset):
        if 'map' in self.request.GET:
            self.paginator.page_size = int(Parameter.get_parameter_by_key("MAP_SEARCH_RECORDS", 150))
            self.paginator.max_page_size = self.paginator.page_size
        return super().paginate_queryset(queryset)


@method_decorator(name="get", decorator=list_swagger_auto_schema_factory(RecordCardListRegularSerializer))
class RecordCardMyTasksListView(RecordsExportExtraQuerysetMixin, RecordCardResponsibleProfileMixin,
                                RecordCardListOrderingMixin, BasicMasterListApiView):
    """
    List of records in processing states for a group (its own records and his descendants).
    The endpoint:
     - can be exported to excel
     - can be filtered by themes, masters, alarms, etc
     - uses a regular serializer to improve the performance
    """

    serializer_class = RecordCardListRegularSerializer
    filterset_class = RecordCardFilter
    filename = "my-tasks.xlsx"
    permission_classes = (IsAuthenticated,)
    INCLUDE_PENDING_PARAM = "include_pending"

    def get_queryset(self):
        if not hasattr(self.request.user, 'usergroup'):
            return RecordCard.objects.none()

        if self.request.META.get("HTTP_ACCEPT") != self.EXCEL_MIME_TYPE:
            qs = RecordCard.objects.filter(record_state_id__in=self._get_filter_states()).order_by(
                "-urgent", F("ans_limit_date").asc(nulls_last=True), "created_at").select_related(
                "ubication", "ubication__district", "request", "request__applicant", "workflow")
        else:
            qs = self.queryset_export_extras(self.excel_queryset)

        return self.filter_queryset_by_group_plate(qs)

    def _get_filter_states(self):
        states = RecordState.STATES_IN_PROCESSING.copy()
        if self.INCLUDE_PENDING_PARAM in self.request.GET:
            states += RecordState.PEND_VALIDATE_STATES
        return states

    @property
    def excel_queryset(self):
        queryset = RecordCard.objects.filter(record_state_id__in=self._get_filter_states()).order_by(
            "-urgent", F("ans_limit_date").asc(nulls_last=True), "created_at").select_related(
            "element_detail", "element_detail__element", "element_detail__element__area", "record_state", "record_type",
            "responsible_profile", "ubication", "ubication__district", "request", "request__applicant", "workflow")
        return self.filter_queryset_by_group_plate(queryset)

    def paginate_queryset(self, queryset):
        if self.request.method == "GET" and 'map' in self.request.GET:
            self.paginator.page_size = int(Parameter.get_parameter_by_key("MAP_SEARCH_RECORDS", 150))
            self.paginator.max_page_size = self.paginator.page_size
        return super().paginate_queryset(queryset)

    def get_serializer_class(self):
        if 'map' in self.request.GET:
            return RecordUbicationListSerializer
        return super().get_serializer_class()


@method_decorator(name="post",
                  decorator=create_swagger_auto_schema_factory(request_body_serializer=CommentSerializer, responses={
                      HTTP_201_CREATED: CommentSerializer,
                      HTTP_400_BAD_REQUEST: "Bad request: Validation Error",
                      HTTP_403_FORBIDDEN: "Acces not allowed",
                      HTTP_409_CONFLICT: "Action can not be done with a cancelled record"
                  }))
class CommentCreateView(RelatedObjectRecordCardBaseCreateView):
    """
    Endpoint to create a comment on a RecordCard. If the Reason is CLAIM_CITIZEN_REQUEST or RECORDCARD_CANCEL_REQUEST,
    an alarm will be set.
    """

    serializer_class = CommentSerializer
    permission_classes = (IsAuthenticated,)

    def group_is_allowed(self, user_group, instance):
        """
        Everybody can comment
        :param user_group:
        :param instance:
        :return:
        """
        return True

    def perform_create(self, serializer):
        comment = serializer.save()
        if comment.reason_id == Reason.CLAIM_CITIZEN_REQUEST:
            comment.record_card.citizen_alarm = True
            comment.record_card.alarm = True
            comment.record_card.save(update_fields=["citizen_alarm", "alarm"])
        elif comment.reason_id == Reason.RECORDCARD_CANCEL_REQUEST:
            comment.record_card.cancel_request = True
            comment.record_card.alarm = True
            comment.record_card.save(update_fields=["cancel_request", "alarm"])

    def check_closed_states_actions(self, serializer):
        """
        If record card is closed or cancelled and action can not be done, return HTTP_409.
        Else, do nothing
        """
        record_card = self.get_record_card(serializer)
        if record_card.record_state_id == RecordState.CANCELLED:
            return Response(_("Action can not be done with a cancelled record"), status=HTTP_409_CONFLICT)


@method_decorator(name="get", decorator=get_swagger_auto_schema_factory(
    ok_message="Tasks to set possible similar records on the queue"))
class RecordCardPossibleSimilarTaskView(APIView):
    """
    Endpoint to set possible similar records task on the queue
    """

    def get(self, request, *args, **kwargs):
        filter_params = {"enabled": True}
        if "review" in request.GET:
            filter_params["possible_similar_records"] = True

        record_cards = RecordCard.objects.filter(**filter_params)
        RecordCardSetPossibleSimilar(record_cards).set_possible_similar()
        return Response(None, status=HTTP_200_OK)


@method_decorator(name="post", decorator=swagger_auto_schema(
    responses={
        HTTP_200_OK: "File uploaded",
    }
))
@method_decorator(name="put", decorator=swagger_auto_schema(
    responses={
        HTTP_200_OK: "Chunk uploaded",
        HTTP_403_FORBIDDEN: "You are not allow to perform the action with a closed or cancelled record"
    }
))
class UploadChunkedRecordFileView(CustomChunkedUploadView):
    """
    API to upload chunked file. When the file has been upload, it is registered as a file of the RecordCard.
    The number of files allowed to upload to a RecordCard can be found on Parameter API_MAX_FILES.

    Only the responsible profile, an Admin and the creation group if the record is not validated are allowed
    to upload files to a Record.

    create:
    End upload file with md5 checksum of file.

    update:
    Upload chunks file -> first included
    """
    model = RecordChunkedFile
    serializer_class = RecordChunkedFileSerializer
    http_method_names = ("post", "put", "get",)
    parser_classes = (MultiPartParser,)
    permission_classes = (IsAuthenticated,)

    def put(self, request, pk=None, *args, **kwargs):
        record_card = get_object_or_404(RecordCard, pk=request.data.get("record_card_id"))
        if record_card.record_state_id in RecordState.CLOSED_STATES and \
                not IrisPermissionChecker.get_for_user(request.user).has_permission(
                    record_permissions.RECARD_CLOSED_FILES):
            return Response(_("You are not allow to perform the action with a closed or cancelled record"),
                            status=HTTP_403_FORBIDDEN)
        return super().put(request, pk, *args, **kwargs)

    def on_completion(self, chunked_upload, request):
        file = default_storage.open(chunked_upload.file.name)

        content_file = ContentFile(file.read(), name=chunked_upload.filename)
        rf = RecordFile.objects.create(file=content_file, record_card_id=chunked_upload.record_card_id,
                                       filename=chunked_upload.filename,
                                       user_id=get_user_traceability_id(self.request.user),
                                       file_type=chunked_upload.file_type)
        setattr(chunked_upload, "record_file_id", rf.id)


@method_decorator(name="delete", decorator=swagger_auto_schema(
    responses={
        HTTP_204_NO_CONTENT: "Record File Deleted",
        HTTP_400_BAD_REQUEST: "Bad Request",
    }
))
class DeleteRecordFileView(GetGroupFromRequestMixin, DestroyAPIView):
    """
    Endpoint to delete a File uploaded to a RecordCard. A comment to traceability is registered when deleting a file.

    Only the responsible profile or an Admin are allowed to upload files to a Record.

    """
    permission_classes = (IsAuthenticated,)
    queryset = RecordFile.objects.all()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not instance.can_be_deleted:
            return Response(status=HTTP_403_FORBIDDEN)
        user_group = self.get_group_from_request(request)
        if not GroupManageFiles(instance.record_card, user_group, request.user).group_can_delete_file():
            return Response(_("Only the responsible profile of the Record Card or DAIR can delete a file"),
                            status=HTTP_400_BAD_REQUEST)

        self.perform_destroy(instance)
        comment = _("The file {} was deleted.").format(instance.filename)
        Comment.objects.create(record_card=instance.record_card, comment=comment, reason_id=Reason.RECORDFILE_DELETED,
                               user_id=get_user_traceability_id(self.request.user), group=user_group)
        return Response(status=HTTP_204_NO_CONTENT)


class WorkflowList(BasicMasterListApiView):
    """
    List of active workflows of the application. It can be filtered by normalizerd_record or applicant identifier.
    """

    serializer_class = WorkflowSerializer
    queryset = Workflow.objects.filter(enabled=True).select_related("main_record_card", "state").prefetch_related(
        Prefetch("recordcard_set", queryset=RecordCard.objects.filter(enabled=True).select_related(
            "request", "request__applicant", "request__applicant__citizen", "request__applicant__social_entity",
            "ubication")),
        Prefetch("workflowcomment_set", queryset=WorkflowComment.objects.filter(enabled=True)))
    filterset_class = WorkflowFilter


class WorkflowFields(RetrieveAPIView):
    """
    Retrieve the detail of a Worflow.
    """
    serializer_class = WorkflowFieldsSerializer
    def get_queryset(self):
        queryset = Workflow.objects.filter(id=self.kwargs.get('pk')).select_related("main_record_card", "state",
                    "workflowresolution").prefetch_related(
            Prefetch("workflowcomment_set", queryset=WorkflowComment.objects.filter(enabled=True).select_related("workflow")))
        return queryset


@method_decorator(name="post", decorator=post_record_card_schema_factory(
    "planify", request_body_serializer=WorkflowPlanSerializer,
    responses={
        HTTP_200_OK: "Workflow planify check",
        HTTP_204_NO_CONTENT: "Workflow planified",
        HTTP_403_FORBIDDEN: "User has no permissions to do this action",
        HTTP_404_NOT_FOUND: "Workflow could not be planified",
        HTTP_400_BAD_REQUEST: "Bad Request"
    }
))
class WorkflowPlanView(SetRecordStateHistoryMixin, WorkflowStateChangeAction):
    """
    Endpoint to change the state of a workflow to planing. Register the planification, change the state of the records
    of the workflow and register a traceability comment related to the workflow.
    """

    workflow_initial_state = RecordState.IN_PLANING
    permission = record_permissions.RECARD_PLAN_RESOL

    serializer_class = WorkflowPlanSerializer
    response_serializer_class = RecordCardCheckSerializer

    def do_workflow_action(self):
        """
        Plan the workflow and its record cards
        :return:
        """
        plan_serializer = WorkflowPlanSerializer(data=self.request.data, context={"record_card": self.record_card})
        if plan_serializer.is_valid(raise_exception=True):
            next_state = self.record_card.next_step_code if plan_serializer.data["action_required"] \
                else RecordState.PENDING_ANSWER
            group = self.request.user.usergroup.group if hasattr(self.request.user, "usergroup") else None

            plan_data = plan_serializer.data
            self.create_workflow_plan(plan_data)
            self.set_records_start_date_process(plan_data)

            self.perform_state_change(next_state, group=group)

            WorkflowComment.objects.create(workflow=self.workflow, task=WorkflowComment.PLAN, group=group,
                                           comment=plan_data["comment"],
                                           user_id=get_user_traceability_id(self.request.user))

    def create_workflow_plan(self, plan_data):
        """
        :param plan_data: plan data
        :return:
        """
        WorkflowPlan.objects.create(workflow=self.workflow, responsible_profile=plan_data.get("responsible_profile"),
                                    start_date_process=plan_data.get("start_date_process"),
                                    action_required=plan_data.get("action_required"))

    def set_records_start_date_process(self, plan_data):
        """
        :param plan_data: plan data
        :return:
        """
        start_date_process = plan_data.get("start_date_process")
        if start_date_process:
            self.workflow_records.update(start_date_process=start_date_process)

    def perform_state_change(self, next_state, group=None, automatic=False):
        """
        Register the state change

        :param next_state: new state code
        :param group: optional group
        :param automatic: set to True if the state change has been done automatically
        :return:
        """
        for record_card in self.workflow_records:
            record_card.register_audit_field("planif_user", get_user_traceability_id(self.request.user))
            state_change = getattr(record_card, record_card.get_state_change_method(next_state))
            state_change(next_state, self.request.user, self.request.user.imi_data.get('dptcuser', ''), group=group,
                         automatic=automatic)

        self.workflow.state_change(next_state)


@method_decorator(name="post", decorator=post_record_card_schema_factory(
    "resolute", request_body_serializer=WorkflowResoluteSerializer,
    responses={
        HTTP_200_OK: "Workflow resolute check",
        HTTP_204_NO_CONTENT: "Workflow to resolution",
        HTTP_403_FORBIDDEN: "User has no permissions to do this action",
        HTTP_404_NOT_FOUND: "Workflow is not available to resolution",
        HTTP_400_BAD_REQUEST: "Bad Request"
    }
))
class WorkflowResoluteView(SetRecordStateHistoryMixin, WorkflowStateChangeAction):
    """
    Endpoint to change the state of a workflow to resolution. Register the resolution, change the state of the records
    of the workflow and register a traceability comment related to the workflow.

    To do this action, all the record of the workflow has to be on a theme of the ambit of the group that does the
    action
    """

    workflow_initial_state = RecordState.IN_RESOLUTION
    permission = record_permissions.RECARD_PLAN_RESOL

    serializer_class = WorkflowResoluteSerializer
    response_serializer_class = RecordCardCheckSerializer

    def do_workflow_action(self):
        """
        Resolute the workflow and its record cards
        :return:
        """
        resolute_serializer = WorkflowResoluteSerializer(data=self.request.data,
                                                         context={"record_card": self.record_card})

        group = self.request.user.usergroup.group if hasattr(self.request.user, "usergroup") else None
        g_themes = GroupThemeTree(group)
        if not g_themes.is_group_record(self.record_card):
            raise ValidationError({
                'non_field_errors': _("You have to change to one of the themes of your ambit before.")
            })

        if resolute_serializer.is_valid(raise_exception=True):
            self.create_workflow_resolution(resolute_serializer.data)
            self.perform_state_change(self.record_card.next_step_code, group)
            WorkflowComment.objects.create(workflow=self.workflow, task=WorkflowComment.RESOLUTION,
                                           comment=resolute_serializer.data["resolution_comment"],
                                           group=group, user_id=get_user_traceability_id(self.request.user))

    def create_workflow_resolution(self, resolute_data):
        """
        Create RecordCardResolution instance
        :param resolute_data: resolution data
        :return:
        """
        if not self.workflowresolution_exists():
            WorkflowResolution.objects.create(
                workflow=self.workflow, service_person_incharge=resolute_data.get("service_person_incharge", ""),
                resolution_type_id=resolute_data["resolution_type"], resolution_date=resolute_data["resolution_date"])


    def workflowresolution_exists(self):
        try:
            wr = WorkflowResolution.objects.get(workflow=self.workflow)
        except WorkflowResolution.DoesNotExist:
            return False
        return True

    def perform_state_change(self, next_state, group=None, automatic=False):
        """
        Register the state change

        :param next_state: new state code
        :param group: optional group
        :param automatic: set to True if the state change has been done automatically
        :return:
        """
        dt = datetime.now()
        madrid_time = pytz.timezone("Europe/Madrid")
        final_time = madrid_time.localize(dt)

        for record_card in self.workflow_records:
            record_card.register_audit_field("resol_user", get_user_traceability_id(self.request.user))
            record_card.register_audit_field("resol_comment", self.request.data.get("resolution_comment"))
            comment_text = _("Resoluted at {} by {}").format(final_time.strftime("%Y-%m-%d %H:%M"),
                                                             get_user_traceability_id(self.request.user))
            Comment.objects.create(record_card=record_card, comment=comment_text, group=group,
                                   user_id=get_user_traceability_id(self.request.user))
            state_change = getattr(record_card, record_card.get_state_change_method(next_state))
            state_change(next_state, self.request.user, self.request.user.imi_data.get('dptcuser', ''), group=group,
                         automatic=automatic)

        self.workflow.state_change(next_state)


@method_decorator(name="get", decorator=get_swagger_auto_schema_factory(ok_message="State machine map"))
class RecordStateMapView(APIView):
    """
    Endpoint to provide a map of the RecordStateMachine, used to paint some components on the SPA
    """

    def get(self, *args, **kwargs):
        self.state_machine = RecordCardStateMachine().state_machine()
        self.add_state_names()
        return Response(data=self.state_machine)

    def add_state_names(self):
        states = {s.pk: s.description for s in RecordState.objects.filter(enabled=True)}
        for process in self.state_machine.values():
            for state, value in process.items():
                value["description"] = states[state]


class ApplicantLastRecordsListView(BasicMasterListApiView):
    """
    Giving an Applicant ID it retrieves the list (maximum 5) of the last records that the applicant has submitted
    """

    serializer_class = RecordCardApplicantListSerializer

    def get_queryset(self):
        return RecordCard.objects.filter(
            request__applicant_id=self.kwargs["id"]).select_related("element_detail").order_by("-created_at")[:5]


class RecordCardAnswerPreview(RecordCardAnswerView):
    """
    Endpoint to render the preview of the answer of the record.
    """

    renderer_classes = [renderers.StaticHTMLRenderer]

    def get_permissions(self):
        return [IsAuthenticated()]

    def do_record_card_action(self):
        """
        Answer and close the RecordCard
        :return:
        """
        user_group = self.get_group_from_request(self.request)
        if not self.record_card.group_can_answer(user_group)["can_answer"]:
            return Response(_("User's group can not answer the RecordCard as it's not an ambit coordinator"),
                            status=HTTP_409_CONFLICT)

        response_serializer = self.get_response_serializer()
        if response_serializer.is_valid(raise_exception=True):
            current = translation.get_language()
            translation.activate(self.record_card.language)
            resp = self.get_answer_preview(response_serializer.validated_data.get("response"))
            translation.activate(current)
            return resp

    def get_answer_preview(self, answer_text):
        response_channel_id = self.record_card.recordcardresponse.response_channel_id
        if response_channel_id == ResponseChannel.EMAIL:
            return self.get_email_preview(answer_text)
        elif response_channel_id == ResponseChannel.LETTER:
            return self.get_pdf_preview(answer_text)
        elif response_channel_id == ResponseChannel.SMS:
            return self.get_sms_preview(answer_text)

    def get_email_preview(self, answer_text):
        email = RecordCardAnswer(self.record_card, group=self.user_group)
        content = email.preview(answer_text).replace("\n", "")
        return Response(data=content, status=status.HTTP_200_OK, content_type="text/html")

    def get_sms_preview(self, answer_text):
        return Response(data=render_record_response(self.record_card, answer_text), status=status.HTTP_200_OK,
                        content_type="text/plain")

    def get_pdf_preview(self, answer_text):
        pdf = create_letter_code(self.record_card, None, answer_text, group=self.user_group)
        return Response(data=pdf[0].content, status=status.HTTP_200_OK,
                        content_type="application/pdf")


class RecordCardResendAnswerView(RecordCardAnswerView):
    """
    Endpoint to resend the answer of a RecordCard. RECARD_ANSWER_RESEND permission is needed.
    """

    permission_classes = []
    record_card_initial_state = RecordState.CLOSED

    def do_record_card_action(self):
        """
        Answer and close the RecordCard
        :return:
        """
        user_group = self.get_group_from_request(self.request)
        if not self.record_card.group_can_answer(user_group)["can_answer"]:
            return Response(_("User's group can not answer the RecordCard as it's not an ambit coordinator"),
                            status=HTTP_409_CONFLICT)

        record_card_resend_answer.send(self.record_card)
        Comment.objects.create(group=user_group, reason=Reason.objects.get(pk=Reason.RECORDCARD_RESEND_ANSWER),
                               record_card=self.record_card, comment=_("Resend answer"))

    def get_permissions(self):
        return [IrisPermission(record_permissions.RECARD_ANSWER_RESEND), IsAuthenticated()]


@method_decorator(name="post", decorator=swagger_auto_schema(responses={HTTP_200_OK: "Record Audit task queued"}))
class SetRecordCardAuditsView(APIView):
    """
    Endpoint to delay set_record_card_audits task
    """

    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        set_record_card_audits.delay()
        return Response(None, status=status.HTTP_200_OK)


@method_decorator(name="post", decorator=post_record_card_schema_factory(
    "validate", responses={
        HTTP_200_OK: "Validation check",
        HTTP_204_NO_CONTENT: "RecordCard validated",
        HTTP_403_FORBIDDEN: "Acces not allowed",
        HTTP_404_NOT_FOUND: "RecordCard could not be validated",
        HTTP_409_CONFLICT: "RecordCard could not be validated with indicated Record because they are not similar",
    }))
class RecordCardWillBeSolvedView(SetRecordStateHistoryMixin, RecordStateChangeAction):
    """
    Endpoint to validate a RecordCard without applicant, setting an applicant.
    Permission RESP_WILL_SOLVE is needed.
    """
    record_card_initial_state = RecordState.NO_PROCESSED
    serializer_class = RecordCardWillBeSolvedSerializer
    response_serializer_class = RecordCardSerializer
    permission = record_permissions.RESP_WILL_SOLVE

    @cached_property
    def limit_days(self):
        return int(Parameter.get_parameter_by_key("DIES_AFEGIR_CIUTADA", 30))

    def check_restricted_action(self, request):
        """
        Anyone with the permission can set applicant, no matter if the record pertains to the user group ambit.
        """
        pass

    def do_record_card_action(self):
        """
        Validate record card and set the workflow
        :return:
        """
        if self.record_card.cant_set_applicant:
            return Response(_("RecordCard could not be solved due to it is expired."
                              "Days for setting citizens: {}").format(self.limit_days),
                            status=HTTP_400_BAD_REQUEST)

        applicant = get_object_or_404(Applicant, pk=self.request.data.get("applicant"))
        self.record_card.will_be_tramited(applicant, **self.get_will_be_solved_kwargs())
        return Response(data=RecordCardSerializer(
            instance=self.record_card, context={'request': self.request}
        ).data, status=HTTP_200_OK)

    def check_valid(self):
        """
        Check data validity
        :return: Return response data
        """
        confirmation_info = {}
        if self.record_card.cant_set_applicant:
            confirmation_info["can_confirm"] = False
            confirmation_info["reason"] = _("RecordCard could not be solved due to it is expired."
                                            "Days for setting citizens: {}").format(self.limit_days)
        else:
            confirmation_info["can_confirm"] = True
            confirmation_info["reason"] = ""
        return confirmation_info, {}

    def get_extra_response_data(self):
        """
        :return: Extra response data for check action
        """
        return {}

    def get_will_be_solved_kwargs(self):
        return {
            "user_department": self.request.user.imi_data.get('dptcuser', ''),
            "user": self.request.user,
        }


# IRISMOBIL! NUEVA LLAMADA!
@method_decorator(name="post", decorator=post_record_card_schema_factory(
    "resolute", request_body_serializer=WorkflowResoluteDraftSerializer,
    responses={
        HTTP_200_OK: "Workflow resolute updated",
        HTTP_201_CREATED: "Workflow resolute created",
        HTTP_400_BAD_REQUEST: "Bad Request",
        HTTP_403_FORBIDDEN: "User has no permissions to do this action",
        HTTP_404_NOT_FOUND: "Workflow is not available to resolution",
    }
))
class WorkflowResoluteDraftView(APIView, PermissionActionMixin, GetGroupFromRequestMixin):
    """
    Endpoint to change the resolution workflow data without workflow state change.

    To do this action, all the record of the workflow has to be on a theme of the ambit of the group that does the
    action, and has to be in resolution status
    """

    workflow_required_state = RecordState.IN_RESOLUTION
    permission = record_permissions.RECARD_PLAN_RESOL
    wr_serializer = WorkflowResoluteDraftSerializer
    wref_serializer = WorkflowResoluteExtraFieldsSerializer
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):

        # If user has not permissions
        if not self.check_restricted_action(request):
            return Response("You don't have permissions to do this actions", status=HTTP_403_FORBIDDEN)

        # If the record_card is not in Resolution State
        if self.record_card.record_state_id != self.workflow_required_state:
            return Response("The RecordCard must be 'in Resolution' Status to modify Resolution Data.",
                            status=HTTP_403_FORBIDDEN)

        wr_serializer = self.wr_serializer(data=self.request.data.copy())
        if wr_serializer.is_valid():
            validated_data = wr_serializer.validated_data
            self.save_workflow_resolute_data(validated_data)
        else:
            return Response({"detail": "The request is not valid", "errors": wr_serializer.errors},
                            status=HTTP_400_BAD_REQUEST)

        data_wref = self.request.data.copy()
        data_wref.update({'workflow_resolution_id': self.kwargs['pk']})
        wref_serializer = self.wref_serializer(data=data_wref)
        if wref_serializer.is_valid():
            self.save_workflow_resolute_extra_data(wref_serializer)
        else:
            return Response({"detail": "The request is not valid", "errors": wref_serializer.errors},
                            status=HTTP_400_BAD_REQUEST)

        return Response("The Workflow has been updated",
                        status=HTTP_200_OK)

    @cached_property
    def record_card(self):
        return self.workflow.main_record_card

    @cached_property
    def workflow_resolution(self):
        """
        Get workflowResolution instance
        :return: Worflow
        """
        try:
            return WorkflowResolution.objects.get(workflow_id=self.kwargs["pk"])
        except:
            return None

    @cached_property
    def workflow_resolution_extrafield(self):
        """
        Get workflowResolution instance
        :return: Worflow
        """
        try:
            workflow_resolution_id = WorkflowResolution.objects.get(
                workflow__id=self.kwargs["pk"]).id
            return WorkflowResolutionExtraFields.objects.get(workflow_resolution_id=workflow_resolution_id)
        except:
            return None

    @cached_property
    def workflow(self):
        """
        Get workflowResolution instance
        :return: Worflow
        """
        return get_object_or_404(Workflow, id=self.kwargs["pk"])

    def check_restricted_action(self, request):
        # Check if group can tramit the record
        user_group = self.get_group_from_request(request)
        if not self.record_card.group_can_tramit_record(user_group):
            return False

        # Check if user has permissions to process records
        if not IrisPermissionChecker.get_for_user(self.request.user).has_permission(self.permission):
            return False

        return True

    def save_workflow_resolute_data(self, validated_data):
        if self.workflow_resolution is not None:
            if 'service_person_incharge' in validated_data.keys():
                self.workflow_resolution.service_person_incharge = validated_data["service_person_incharge"]
            if 'resolution_type' in validated_data.keys():
                self.workflow_resolution.resolution_type = ResolutionType.objects.get(id=validated_data["resolution_type"])
            if 'resolution_date' in validated_data.keys():
                self.workflow_resolution.resolution_date = validated_data["resolution_date"]
            self.workflow_resolution.save()
        else:
            WorkflowResolution.objects.create(
                workflow=self.workflow, service_person_incharge=validated_data.get("service_person_incharge", ""),
                resolution_type_id=validated_data.get("resolution_type", 1),
                resolution_date=validated_data.get("resolution_date", None))

        if 'resolution_comment' in validated_data.keys():
            self.save_comment(self.workflow, validated_data["resolution_comment"])

    @cached_property
    def workflow_comment(self):
        """
        Get WorkflowComment instance
        :return: Worflow
        """
        try:
            workflow_comment = WorkflowComment.objects.get(
                workflow__id=self.workflow.id)
            return workflow_comment
        except:
            return None

    def save_comment(self, workflow, comment):
        WorkflowComment.objects.create(
            workflow=workflow, group=None, task=WorkflowComment.RESOLUTION, comment=comment)

    def save_workflow_resolute_extra_data(self, serializer):

        validated_data = serializer.validated_data

        workflow_resolution_id = WorkflowResolution.objects.get(
            workflow__id=validated_data.get("workflow_resolution_id")).id
        if self.workflow_resolution_extrafield is not None:
            if 'workflow_resolution_id' in validated_data.keys():
                self.workflow_resolution_extrafield.workflow_resolution_id = workflow_resolution_id
            if 'resolution_date_end' in validated_data.keys():
                self.workflow_resolution_extrafield.resolution_date_end = validated_data["resolution_date_end"]
            if 'ubication_start' in validated_data.keys():
                ubication_start = serializer.save_ubication(validated_data['ubication_start'])
                self.workflow_resolution_extrafield.ubication_start = ubication_start
            if 'ubication_end' in validated_data.keys():
                ubication_end = serializer.save_ubication(validated_data['ubication_end'])
                self.workflow_resolution_extrafield.ubication_end = ubication_end
            self.workflow_resolution_extrafield.save()
        else:
            ubication_start, ubication_end = self.get_ubications_wref(serializer)
            WorkflowResolutionExtraFields.objects.create(
                workflow_resolution_id=workflow_resolution_id,
                resolution_date_end=validated_data.get("resolution_date_end", None),
                ubication_start=ubication_start,
                ubication_end=ubication_end)

    def get_ubications_wref(self, serializer):
        ubication_start = None
        ubication_end = None
        if serializer.validated_data.get("ubication_start"):
            ubication_start = serializer.save_ubication(serializer.validated_data['ubication_start'])
        if serializer.validated_data.get("ubication_end"):
            ubication_end = serializer.save_ubication(serializer.validated_data['ubication_end'])
        return ubication_start, ubication_end


@method_decorator(name="get", decorator=get_swagger_auto_schema_factory(ok_message="File downloaded"))
class GetDownloadMinioUrlView(APIView):
    """
    Endpoint to get the base64 file from a document uploaded on a record_card
    """

    def get(self, request, *args, **kwargs):

        data = RecordFile.objects.get(id=self.kwargs["pk"])

        if data is None or getattr(data, 'file', None) is None:
            return Response(data='Not found', status=HTTP_404_NOT_FOUND)

        response = IMIMinioMediaStorage().url(data.file.name)
        if response is None:
            return Response(data='Not found', status=HTTP_404_NOT_FOUND)

        return Response(data=response,status=HTTP_200_OK)
