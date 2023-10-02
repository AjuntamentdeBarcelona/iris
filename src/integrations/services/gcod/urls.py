from django.urls import path
from integrations import views

urlpatterns = [
    path('type_streets/', views.GcodTypeStreetsView.as_view()),
    path('districts/', views.GcodDistrictsView.as_view()),
    path('streets/', views.GcodStreetsView.as_view()),
    path('neighborhood/', views.GcodNeighborhoodView.as_view()),
]
