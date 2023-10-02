from django.urls import path
from . import views

urlpatterns = [
    path("scheduled/", views.ManualScheduleAPIList.as_view(), name="scheduled_tasks"),
    path("scheduled/<int:pk>/", views.ManualScheduleDetail.as_view(), name="scheduled_tasks_detail"),
]
