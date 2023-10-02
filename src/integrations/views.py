import uuid
import logging

from django.db.models import Q
from datetime import datetime
from django.utils.decorators import method_decorator
from django_celery_results.models import TaskResult
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.status import HTTP_204_NO_CONTENT
from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from integrations.email import send_mail_message
from integrations.filters import TaskResultFilter, BatchFileFilter
from integrations.models import BatchFile, OpenDataModel
from integrations.serializers import (RecordCardSenderSerializer, TaskResultSerializer, BatchFileSerializer,
                                      TaskTypeSerializer, TaskRetrySerializer)
from iris_masters.permissions import ADMIN
from .manual_task_schedule.models import get_tasks, get_periodic_tasks
from .tasks import (validate_batch_file, generate_open_data_report,)
from main.iris_roles import public_iris_roles
from profiles.permissions import IrisPermission
from public_api.views import PublicApiListAPIView
from django.conf import settings
from django.utils.module_loading import import_string
from record_cards.record_actions.geocode import get_geocoder_services_class
from main.utils import get_user_traceability_id

logger = logging.getLogger(__name__)


@method_decorator(name="get", decorator=public_iris_roles)
class GcodTypeStreetsView(PublicApiListAPIView):
    def get(self, request, **kwargs):
        GcodServices = get_geocoder_services_class()
        data = GcodServices().type_streets()
        return Response(
            status=status.HTTP_200_OK if data else status.HTTP_404_NOT_FOUND,
            data=data
        )


@method_decorator(name="get", decorator=public_iris_roles)
class GcodDistrictsView(PublicApiListAPIView):
    def get(self, request, **kwargs):
        GcodServices = get_geocoder_services_class()
        data = GcodServices().districts()
        return Response(
            status=status.HTTP_200_OK if data else status.HTTP_404_NOT_FOUND,
            data=data
        )


@method_decorator(name="get", decorator=public_iris_roles)
class GcodStreetsView(PublicApiListAPIView):
    def get(self, request, **kwargs):
        street_var = self.request.GET.get('var')
        GcodServices = get_geocoder_services_class()
        data = GcodServices().streets(variable=street_var)
        return Response(
            status=status.HTTP_200_OK if data else status.HTTP_404_NOT_FOUND,
            data=data
        )


@method_decorator(name="get", decorator=public_iris_roles)
class GcodNeighborhoodView(PublicApiListAPIView):
    def get(self, request, **kwargs):
        codi_dist = self.request.GET.get("codi_dist")
        GcodServices = get_geocoder_services_class()
        if codi_dist:
            data = GcodServices().neighborhood_district(codi_dist)
        else:
            data = GcodServices().neighborhood()
        return Response(
            status=status.HTTP_200_OK if data else status.HTTP_404_NOT_FOUND,
            data=data
        )


@method_decorator(name="post", decorator=swagger_auto_schema(
    operation_id="External Service Dummy",
    request_body=RecordCardSenderSerializer,
    responses={
        status.HTTP_200_OK: openapi.Response(
            description="IRIS2 expects the external system to return its id for the record card being sent.",
            schema=openapi.Schema(
                title="External Service record card creation response",
                description="",
                type=openapi.TYPE_OBJECT,
                properties={
                    "id": openapi.Schema("id", description="External system ID",
                                         type=openapi.TYPE_STRING)
                }
            )
        ),
    }
))
class ExternalServiceDummy(APIView):
    permission_classes = []

    def post(self, *args, **kwargs):
        record_card_id = self.request.data.get("id")
        uid = uuid.uuid4()
        send_mail_message(
            "Tramitació externa TEST - Fitxat rebuda",
            "Rebuda fitxa amb id intern {}, codi extern de prova generat {}".format(record_card_id, uid),
            send_to=["fmunoz@apsl.net", "jorge.sarrias.pedemonte@everis.com", "tperez@bcn.cat", "vnaranjo@ext.bcn.cat"]
        )
        return Response(data={"id": uid}, status=status.HTTP_200_OK)


class TaskTypeView(generics.GenericAPIView):
    serializer_class = TaskTypeSerializer

    def get(self, request, *args, **kwargs):
        return Response(data=self.serializer_class(instance=get_periodic_tasks(), many=True).data,
                        status=status.HTTP_200_OK)

    def get_permissions(self):
        return [IrisPermission(ADMIN)]


class LogResultView(generics.ListAPIView):
    queryset = TaskResult.objects.all()
    serializer_class = TaskResultSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = TaskResultFilter

    def get_queryset(self):
        tasks = get_tasks()
        return super().get_queryset().filter(
            Q(task_name__in=tasks)
        ).order_by("-date_done")

    def get_permissions(self):
        return [IrisPermission(ADMIN)]


class LogResultRetryView(generics.CreateAPIView):
    serializer_class = TaskRetrySerializer

    def get_permissions(self):
        return [IrisPermission(ADMIN)]


class BatchFileListAPIView(generics.ListAPIView):
    queryset = BatchFile.objects.all()
    serializer_class = BatchFileSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = BatchFileFilter

    def get_permissions(self):
        return [IrisPermission(ADMIN)]


class BatchFileValidateView(generics.RetrieveAPIView):
    queryset = BatchFile.objects.all()
    serializer_class = BatchFileSerializer

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.validated_at:
            return Response(status=status.HTTP_409_CONFLICT)
        self.object.validate(get_user_traceability_id(self.request.user))
        validate_batch_file.delay(batch_file_id=self.object.pk)
        return Response(status=status.HTTP_200_OK, data=self.serializer_class(instance=self.object).data)

    def get_permissions(self):
        return [IrisPermission(ADMIN)]


class OpenDataDateReportView(APIView):
    permission_classes = []

    def post(self, *args, **kwargs):
        generate_open_data_report.delay(month=self.kwargs["month"], year=self.kwargs["year"])
        return Response(status=HTTP_204_NO_CONTENT)


class BatchReportsCompleteView(APIView):
    """
    View for testing all files from each batch sent
    """
    permission_classes = []

    def post(self, *args, **kwargs):
        if settings.SMS_BACKEND_PENDENTS is not None:
            try:
                sending_sms_pendents = import_string(settings.SMS_BACKEND_PENDENTS)
                sending_sms_pendents()
            except ImportError:
                logger.info(f"Unable to locate the module {settings.SMS_BACKEND_PENDENTS}, couldn't send pending SMS.")
        else:
            logger.info("No pending SMS backend sender module was specified.")
        return Response(status=HTTP_204_NO_CONTENT)


class EliminateOpendataView(APIView):
    """
    View for testing all files from each batch sent
    """
    permission_classes = []

    def get(self, *args, **kwargs):
        year = self.request.GET.get('year')
        trimester = self.request.GET.get('trimester')
        if trimester == '1':
            left_window = '01/01/' + str(year)[-2:] + ' 00:00:00'
            right_window = '31/03/' + str(year)[-2:] + ' 23:59:59'
        elif trimester == '2':
            left_window = '01/04/' + str(year)[-2:] + ' 00:00:00'
            right_window = '30/06/' + str(year)[-2:] + ' 23:59:59'
        elif trimester == '3':
            left_window = '01/07/' + str(year)[-2:] + ' 00:00:00'
            right_window = '30/09/' + str(year)[-2:] + ' 23:59:59'
        else:
            left_window = '01/10/' + str(year)[-2:] + ' 00:00:00'
            right_window = '31/12/' + str(year)[-2:] + ' 23:59:59'
        newest_date_limit = right_window
        oldest_date_limit = left_window
        last_month = datetime.strptime(newest_date_limit, '%d/%m/%y %H:%M:%S').month
        first_month = datetime.strptime(oldest_date_limit, '%d/%m/%y %H:%M:%S').month
        OpenDataModel.objects.filter(closing_month__gte=('0' + str(first_month))[-2:],
                                     closing_month__lte=('0' + str(last_month))[-2:], closing_year=year).delete()
        return Response(status=HTTP_204_NO_CONTENT)


class BatchFileChangeView(APIView):
    """
    View for testing all files from each batch sent
    """
    permission_classes = []

    def get(self, *args, **kwargs):
        batch_id = self.request.GET.get('id')
        BatchFile.objects.filter(id=int(batch_id)).update(status=1, validated_at=None, validated_by="")
        return Response(status=HTTP_204_NO_CONTENT)
