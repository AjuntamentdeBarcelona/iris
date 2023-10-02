from django.urls import path
from geo_proxy import views

urlpatterns = [
    path('ubication/search/', views.GeoProxySearchListView.as_view()),
    path('ubication/reverse/', views.GeoProxyReverseListView.as_view()),
]
