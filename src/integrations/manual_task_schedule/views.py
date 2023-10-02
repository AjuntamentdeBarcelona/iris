# Create your views here.
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics

from integrations.manual_task_schedule.filtersets import ManualTaskFilter
from integrations.manual_task_schedule.models import ManualScheduleLog
from integrations.manual_task_schedule.serializers import ManualScheduleLogSerializer
from integrations.manual_task_schedule.tasks import schedule_for
from iris_masters.permissions import ADMIN
from profiles.permissions import IrisPermission


class ScheduleMixin:
    queryset = ManualScheduleLog.objects.all()
    serializer_class = ManualScheduleLogSerializer

    def get_permissions(self):
        return [IrisPermission(ADMIN)]

    @property
    def username(self):
        return self.request.user.username


class ManualScheduleAPIList(ScheduleMixin, generics.ListAPIView, generics.CreateAPIView):
    """
    View to retrieve the list of the scheduled tasks.
    The list can be filteder by:
     - task by exact
     - status by exact
     - next by gte

    A new schedule can be created with the post operation.
    Once it's created, the task is scheduled for the selected time

    Administration permission  needed to create and retrieve.
    """

    filter_backends = (DjangoFilterBackend, )
    filterset_class = ManualTaskFilter

    def perform_create(self, serializer):
        serializer.validated_data['created_by'] = self.username
        super().perform_create(serializer)
        schedule_for(manual_schedule=serializer.instance)


class ManualScheduleDetail(ScheduleMixin, generics.DestroyAPIView):
    """
    View to destroy a Manual Scheduled Task.
    Administration permission  to destroy.
    """

    def perform_destroy(self, instance):
        instance.cancel(user=self.username)
