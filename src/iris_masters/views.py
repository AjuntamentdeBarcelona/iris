from datetime import timedelta

from django.utils import timezone
from django.db.models import Exists, OuterRef, Prefetch, Q
from django.contrib.auth.models import User
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_control
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema

from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.status import (HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST,
                                   HTTP_404_NOT_FOUND)
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from excel_export.mixins import ExcelExportListMixin, ExcelDescriptionExportMixin
from iris_masters.filters import InputChannelFilter, AnnouncementFilter
from iris_masters import permissions as masters_permissions
from iris_masters.models import (Announcement, ApplicantType, Application, CommunicationMedia, InputChannel, MediaType,
                                 Parameter, Process, Reason, RecordState, RecordType, ResponseChannel, Support,
                                 InputChannelSupport, District, ResolutionType, ExternalService,
                                 InputChannelApplicantType, LetterTemplate)
from iris_masters.permissions import ANNOUNCEMENTS
from iris_masters.serializers import (AnnouncementSerializer, InputChannelSerializer, ParameterSerializer,
                                      ProcessSerializer, RecordStateSerializer, RecordTypeSerializer,
                                      ResponseChannelSerializer, SupportSerializer, master_serializer_factory,
                                      DistrictSerializer, ResolutionTypeSerializer, ExternalServiceSerializer,
                                      CommunicationMediaSerializer, MediaTypeSerializer, ReasonSerializer,
                                      InputChannelShortSerializer, CancelReasonSerializer, ShortRecordTypeSerializer,
                                      ApplicantTypeSerializer, LetterTemplateSerializer, InputChannelExcelSerializer,
                                      SupportExcelSerializer, ParameterRegularSerializer)
from iris_masters.tasks import masters_data_checks
from main.api.filters import UnaccentSearchFilter
from main.api.pagination import IrisOnlyMaxPagination
from main.api.schemas import (destroy_swagger_auto_schema_factory, create_swagger_auto_schema_factory,
                              update_swagger_auto_schema_factory, list_swagger_auto_schema_factory,
                              retrieve_swagger_auto_schema_factory)
from main.utils import get_translated_fields
from main.views import MultipleSerializersMixin, UpdateListView, ModelListRetrieveUpdateViewSet
from profiles.permissions import IrisPermission

BROWSER_CACHE_MAX_AGE = 60 * 60 * 7


class BasicMasterViewSet(MultipleSerializersMixin, ModelViewSet):
    permission_classes = (IsAuthenticated,)


class BasicMasterListApiView(ListAPIView):
    permission_classes = (IsAuthenticated,)

    def get_serializer(self, *args, **kwargs):
        self.serializer = super().get_serializer(*args, **kwargs)
        return self.serializer


class BasicMasterSearchMixin:
    filter_backends = (UnaccentSearchFilter, DjangoFilterBackend)
    search_fields = get_translated_fields("#description")


class BasicOrderingFieldsSearchMixin(BasicMasterSearchMixin):
    filter_backends = (UnaccentSearchFilter, DjangoFilterBackend, OrderingFilter)
    ordering_fields = get_translated_fields("description")


class BasicMasterAdminPermissionsMixin:
    permission_codename = masters_permissions.ADMIN

    def get_permissions(self):
        if self.request.method != "GET":
            return [IrisPermission(self.permission_codename), IsAuthenticated()]
        return super().get_permissions()


class AutocompleteBaseSearchView(BasicMasterSearchMixin, BasicMasterListApiView):
    model = None
    queryset_filters = None  # dict
    filterset_class = None  # filter class

    def get_serializer_class(self):
        return master_serializer_factory(self.model, extra_readonly_fields=("description",))

    def get_queryset(self):
        if self.queryset_filters:
            return self.model.objects.filter(**self.queryset_filters)
        return self.model.objects.all()


class MediaTypeViewSet(BasicMasterSearchMixin, BasicMasterViewSet):
    """
    List of Media Types on the system, ordered by description.
    """
    queryset = MediaType.objects.filter(enabled=True).order_by("description")
    serializer_class = MediaTypeSerializer


@method_decorator(name="create", decorator=create_swagger_auto_schema_factory(CommunicationMediaSerializer))
@method_decorator(name="update", decorator=update_swagger_auto_schema_factory(CommunicationMediaSerializer))
@method_decorator(name="partial_update", decorator=update_swagger_auto_schema_factory(CommunicationMediaSerializer))
@method_decorator(name="destroy", decorator=destroy_swagger_auto_schema_factory())
@method_decorator(name="list", decorator=list_swagger_auto_schema_factory(CommunicationMediaSerializer))
class CommunicationMediaViewSet(ExcelDescriptionExportMixin, BasicOrderingFieldsSearchMixin,
                                BasicMasterAdminPermissionsMixin, BasicMasterViewSet):
    """
    Viewset to manage Communication Medias (CRUD).
    Administration permission needed to create, update and destroy.
    The list endpoint:
     - can be exported to excel
     - can be ordered by description
     - supports unaccent search by description
    """

    queryset = CommunicationMedia.objects.all().select_related("media_type").order_by("description")
    serializer_class = CommunicationMediaSerializer
    search_fields = ("#description",)
    filename = "communication-media.xlsx"
    ordering_fields = ["description"]


class ReasonListView(BasicMasterSearchMixin, BasicMasterListApiView):
    """
    List of Reasons of the system
    """
    queryset = Reason.objects.all()
    serializer_class = ReasonSerializer


@method_decorator(name="create", decorator=create_swagger_auto_schema_factory(ReasonSerializer))
@method_decorator(name="update", decorator=update_swagger_auto_schema_factory(ReasonSerializer))
@method_decorator(name="partial_update", decorator=update_swagger_auto_schema_factory(ReasonSerializer))
@method_decorator(name="destroy", decorator=destroy_swagger_auto_schema_factory())
@method_decorator(name="list", decorator=list_swagger_auto_schema_factory(CancelReasonSerializer))
class CancelReasonViewSet(ExcelDescriptionExportMixin, BasicOrderingFieldsSearchMixin,
                          BasicMasterAdminPermissionsMixin, BasicMasterViewSet):
    """
    Viewset to manage Cancel Reasons (Reasons with reason_type="1")(CRUD).
    Administration permission needed to create, update and destroy.
    The list endpoint:
     - can be exported to excel
     - can be ordered by description
     - supports unaccent search by description
    """
    queryset = Reason.objects.all()
    serializer_class = CancelReasonSerializer
    reason_type = Reason.TYPE_1  # Cancel reasons
    filename = "cancel-reasons.xlsx"
    ordering_fields = ["description"]
    search_fields = ["#description"]

    def get_queryset(self):
        return super().get_queryset().filter(reason_type=self.reason_type).order_by("description")

    def create(self, request, *args, **kwargs):
        request.data.update({"reason_type": self.reason_type})
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        request.data.update({"reason_type": self.reason_type})
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, "_prefetched_objects_cache", None):
            # If "prefetch_related" has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)


@method_decorator(name="list", decorator=list_swagger_auto_schema_factory(CancelReasonSerializer))
class ReassignationReasonViewSet(CancelReasonViewSet):
    """
    Viewset to manage Reassignation Reasons (Reasons with reason_type="2")(CRUD).
    Administration permission needed to create, update and destroy.
    The list endpoint:
     - can be exported to excel
     - can be ordered by description
     - supports unaccent search by description
    """

    reason_type = Reason.TYPE_2  # Reasignation reasons
    filename = "reasignations-reasons.xlsx"


@method_decorator(name="create", decorator=create_swagger_auto_schema_factory(AnnouncementSerializer))
@method_decorator(name="update", decorator=update_swagger_auto_schema_factory(AnnouncementSerializer))
@method_decorator(name="partial_update", decorator=update_swagger_auto_schema_factory(AnnouncementSerializer))
@method_decorator(name="destroy", decorator=destroy_swagger_auto_schema_factory())
@method_decorator(name="list", decorator=list_swagger_auto_schema_factory(AnnouncementSerializer))
class AnnouncementViewSet(ExcelExportListMixin, BasicOrderingFieldsSearchMixin, BasicMasterAdminPermissionsMixin,
                          ModelViewSet):
    """
    Viewset to manage Announcements (CRUD).
    Administration permission or Announcements Permission needed to create, update and destroy.
    The list endpoint:
     - can be exported to excel
     - can be ordered by the different language descriptions
     - supports unaccent search by the different language descriptions
     - can be filtered by created_at (gte or lte) and expiration_date (gte or lte)
    """

    queryset = Announcement.objects.all()
    permission_codename = ANNOUNCEMENTS
    serializer_class = AnnouncementSerializer
    permission_classes = (IsAuthenticated,)
    filterset_class = AnnouncementFilter
    filename = "announcements.xlsx"
    nested_excel_fields = {
        ExcelExportListMixin.NESTED_BASE_KEY: ["id", "title", "description", "expiration_date", "important"],
    }
    ordering_fields = ["title", "description", "expiration_date", "important"]

    def get_queryset(self):
        qs = super().get_queryset().filter(
            Q(expiration_date__gt=timezone.now()) | Q(expiration_date__isnull=True),
            created_at__gte=(timezone.now() - timedelta(days=90))
        ).order_by("-created_at")
        seen_by = User.objects.filter(pk=self.request.user.pk, announcement__pk=OuterRef("pk"))
        return qs.annotate(is_seen=Exists(seen_by))


@method_decorator(name="put", decorator=swagger_auto_schema(responses={
    HTTP_200_OK: "Announcement Seen By Updated",
    HTTP_404_NOT_FOUND: "Announcement Not Found"}))
class AnnouncementSeenView(APIView):
    """
    Mark an Announcement as seen by the user.
    """

    permission_classes = (IsAuthenticated,)

    def put(self, request, *args, **kwargs):
        try:
            announcement = Announcement.objects.get(id=self.kwargs["id"], deleted__isnull=True)
            announcement.seen_by.add(request.user)
            return Response(data={}, status=HTTP_200_OK)
        except Announcement.DoesNotExist:
            return Response(data="Invalid item id", status=HTTP_404_NOT_FOUND)


@method_decorator(name="retrieve", decorator=retrieve_swagger_auto_schema_factory(RecordTypeSerializer))
@method_decorator(name="list", decorator=cache_control(max_age=BROWSER_CACHE_MAX_AGE))
class RecordTypeListRetrieveUpdateViewSet(ModelListRetrieveUpdateViewSet):
    """
    Viewset to retrieve, list and update Record Types (RU).
    """

    queryset = RecordType.objects.all().prefetch_related("iristemplaterecordtypes_set")
    serializer_class = RecordTypeSerializer
    short_serializer_class = ShortRecordTypeSerializer


@method_decorator(name="get", decorator=cache_control(max_age=BROWSER_CACHE_MAX_AGE))
class RecordStateView(BasicMasterListApiView):
    """
    List of available Record States of the system
    """
    queryset = RecordState.objects.filter(enabled=True)
    serializer_class = RecordStateSerializer


@method_decorator(name="list", decorator=cache_control(max_age=BROWSER_CACHE_MAX_AGE))
class ResponseChannelView(BasicMasterListApiView):
    """
    List of available Response Channels of the system
    """
    queryset = ResponseChannel.objects.all()
    serializer_class = ResponseChannelSerializer


@method_decorator(name="get", decorator=list_swagger_auto_schema_factory(ParameterSerializer))
class ParameterListView(ExcelExportListMixin, BasicMasterListApiView):
    """
    List of available Parameters, excluding the deprecated.
    The endpoint:
     - can be exported to excel
     - can be filtered by category
    """
    queryset = Parameter.objects.filter(show=True).exclude(category=Parameter.DEPRECATED)
    serializer_class = ParameterSerializer
    filterset_fields = ["category"]
    pagination_class = IrisOnlyMaxPagination
    filename = "parameters.xlsx"
    nested_excel_fields = {
        ExcelExportListMixin.NESTED_BASE_KEY: ["name", "valor", "description"]
    }


class ParameterVisibleListView(BasicMasterListApiView):
    """
    List of visible (and available) Parameters, excluding the deprecated.
    """
    queryset = Parameter.objects.filter(show=True, visible=True).exclude(
        category=Parameter.DEPRECATED
    ).only('parameter', 'valor')
    serializer_class = ParameterRegularSerializer
    pagination_class = IrisOnlyMaxPagination
    authentication_classes = []
    permission_classes = []


@method_decorator(name="list", decorator=cache_control(max_age=BROWSER_CACHE_MAX_AGE))
class ProcessListView(BasicMasterListApiView):
    """
    List of Process of the system, ordered by ID
    """
    queryset = Process.objects.order_by('id')
    serializer_class = ProcessSerializer


@method_decorator(name="update", decorator=update_swagger_auto_schema_factory(DistrictSerializer))
@method_decorator(name="partial_update", decorator=update_swagger_auto_schema_factory(DistrictSerializer))
@method_decorator(name="list", decorator=list_swagger_auto_schema_factory(DistrictSerializer))
class DistrictViewSet(BasicMasterAdminPermissionsMixin,
                      BasicOrderingFieldsSearchMixin, BasicMasterViewSet):
    """
    Viewset to manage Districts (RU).
    Administration permission needed to update.
    The list endpoint:
     - can be ordered by name
     - supports unaccent search by name
     Extra fields could be added to District model if filter selection is desired
     Example: location, zone (polygon selection or smth)
    """
    queryset = District.objects.order_by('id')
    serializer_class = DistrictSerializer
    ordering_fields = ["name"]
    search_fields = ["#name"]


@method_decorator(name="post", decorator=swagger_auto_schema(request_body=ParameterSerializer(many=True),
                                                             responses={
                                                                 HTTP_204_NO_CONTENT: "Parameters updated",
                                                                 HTTP_400_BAD_REQUEST: "Bad request: Validation Error",
                                                             }))
class ParameterUpdateListView(BasicMasterAdminPermissionsMixin, UpdateListView):
    """
    Update a list of Parameters. If all data is valid, the objects will be updated. Else,
    a dictionary with the errors for each no valid object will be returned

    Administration permission needed to update.
    """
    serializer_class = ParameterSerializer
    model_class = Parameter


class ApplicationView(BasicMasterListApiView):
    """
    List of applications available on the system
    """

    queryset = Application.objects.filter(enabled=True)
    serializer_class = master_serializer_factory(Application, ("description_hash",), ("description_hash",))


@method_decorator(name="create", decorator=create_swagger_auto_schema_factory(SupportSerializer))
@method_decorator(name="update", decorator=update_swagger_auto_schema_factory(SupportSerializer))
@method_decorator(name="partial_update", decorator=update_swagger_auto_schema_factory(SupportSerializer))
@method_decorator(name="destroy", decorator=destroy_swagger_auto_schema_factory())
@method_decorator(name="list", decorator=list_swagger_auto_schema_factory(SupportSerializer))
class SupportViewSet(ExcelDescriptionExportMixin, BasicMasterAdminPermissionsMixin, BasicOrderingFieldsSearchMixin,
                     BasicMasterViewSet):
    """
    Viewset to manage Support (CRUD).
    Administration permission needed to create, update and destroy.
    The list endpoint:
     - can be exported to excel
     - can be ordered by description
     - supports unaccent search by description
     - can be filtered by created_at (gte or lte) and expiration_date (gte or lte)
    """

    queryset = Support.objects.all().order_by("description")
    serializer_class = SupportSerializer
    export_serializer = SupportExcelSerializer
    filename = "supports.xlsx"
    search_fields = ("#description",)
    ordering_fields = ["description"]
    nested_excel_fields = {
        ExcelExportListMixin.NESTED_BASE_KEY: ["description", "order", "permet_ciutada_nd",
                                               "requireix_mitja_comunicacio", "requereix_codi_registre"],
    }


@method_decorator(name="create", decorator=create_swagger_auto_schema_factory(ApplicantTypeSerializer))
@method_decorator(name="update", decorator=update_swagger_auto_schema_factory(ApplicantTypeSerializer))
@method_decorator(name="partial_update", decorator=update_swagger_auto_schema_factory(ApplicantTypeSerializer))
@method_decorator(name="destroy", decorator=destroy_swagger_auto_schema_factory())
@method_decorator(name="list", decorator=list_swagger_auto_schema_factory(ApplicantTypeSerializer))
class ApplicantTypeViewSet(ExcelDescriptionExportMixin, BasicMasterAdminPermissionsMixin,
                           BasicOrderingFieldsSearchMixin, BasicMasterViewSet):
    """
    Viewset to manage Applicant Types (CRUD).
    Administration permission needed to create, update and destroy.
    The list endpoint:
     - can be exported to excel
     - can be ordered by description
     - supports unaccent search by description
    """
    queryset = ApplicantType.objects.all()
    serializer_class = ApplicantTypeSerializer
    filename = "applicant-type.xlsx"
    ordering_fields = ["description"]
    search_fields = ["#description"]


@method_decorator(name="create", decorator=create_swagger_auto_schema_factory(InputChannelSerializer))
@method_decorator(name="update", decorator=update_swagger_auto_schema_factory(InputChannelSerializer))
@method_decorator(name="partial_update", decorator=update_swagger_auto_schema_factory(InputChannelSerializer))
@method_decorator(name="destroy", decorator=destroy_swagger_auto_schema_factory())
@method_decorator(name="list", decorator=list_swagger_auto_schema_factory(InputChannelShortSerializer))
@method_decorator(name="retrieve", decorator=retrieve_swagger_auto_schema_factory(InputChannelSerializer))
class InputChannelViewSet(ExcelDescriptionExportMixin, BasicOrderingFieldsSearchMixin,
                          BasicMasterAdminPermissionsMixin, BasicMasterViewSet):
    """
    Viewset to manage Input Channels (CRUD).
    Administration permission needed to create, update and destroy.
    The list endpoint:
     - can be exported to excel
     - can be ordered by description
     - supports unaccent search by description
     - can be filtered by visible or not visible
    """

    queryset = InputChannel.objects.all().order_by("description")
    serializer_class = InputChannelSerializer
    filterset_class = InputChannelFilter
    short_serializer_class = InputChannelShortSerializer
    export_serializer = InputChannelExcelSerializer
    search_fields = ("#description",)
    filename = "input_channels.xlsx"
    ordering_fields = ["description"]
    nested_excel_fields = {
        ExcelExportListMixin.NESTED_BASE_KEY: ["description", "order", "visible", "permet_gabinet_alcaldia"],
    }

    def get_queryset(self):
        return super().get_queryset().prefetch_related(
            Prefetch(
                "inputchannelapplicanttype_set",
                queryset=InputChannelApplicantType.objects.filter(enabled=True, applicant_type__deleted__isnull=True
                                                                  ).select_related("applicant_type")
            ),
            Prefetch(
                "inputchannelsupport_set",
                queryset=InputChannelSupport.objects.filter(enabled=True,
                                                            support__deleted__isnull=True).select_related("support")
            )
        )


@method_decorator(name="create", decorator=create_swagger_auto_schema_factory(ResolutionTypeSerializer))
@method_decorator(name="update", decorator=update_swagger_auto_schema_factory(ResolutionTypeSerializer))
@method_decorator(name="partial_update", decorator=update_swagger_auto_schema_factory(ResolutionTypeSerializer))
@method_decorator(name="destroy", decorator=destroy_swagger_auto_schema_factory())
@method_decorator(name="list", decorator=list_swagger_auto_schema_factory(ResolutionTypeSerializer))
class ResolutionTypeViewSet(ExcelDescriptionExportMixin, BasicOrderingFieldsSearchMixin,
                            BasicMasterAdminPermissionsMixin, BasicMasterViewSet):
    """
    Viewset to manage Resolution Types (CRUD).
    Administration permission needed to create, update and destroy.
    The list endpoint:
     - can be exported to excel
     - can be ordered by description
     - supports unaccent search by description
    """

    queryset = ResolutionType.objects.all()
    serializer_class = ResolutionTypeSerializer
    search_fields = ("#description",)
    filename = "resolution-types.xlsx"
    ordering_fields = ["description"]


class ExternalServiceListView(BasicMasterListApiView):
    """
    List of External Services of the system
    """
    queryset = ExternalService.objects.all()
    serializer_class = ExternalServiceSerializer


class LetterTemplateListView(BasicMasterAdminPermissionsMixin, BasicMasterSearchMixin, BasicMasterListApiView):
    """
    List of available Letter Templates of the system.
    The endpoint supports unaccent search by description
    """
    serializer_class = LetterTemplateSerializer
    queryset = LetterTemplate.objects.filter(enabled=True)
    search_fields = ["#description"]


@method_decorator(name="post", decorator=swagger_auto_schema(responses={
    HTTP_204_NO_CONTENT: "Masters data checks task queued"
}))
class MastersDataChecksView(APIView):
    """
    Endpoint to execute the data checks of the masters entities.
    If delay GET parameter is set to 1, the data check will be run in a celery task
    """

    def post(self, request, *args, **kwargs):
        masters_data_checks.delay() if self.request.GET.get('delay', '1') == '1' else masters_data_checks()
        return Response(status=HTTP_204_NO_CONTENT)
