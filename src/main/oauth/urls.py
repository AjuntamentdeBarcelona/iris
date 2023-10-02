from django.urls import path

from main.oauth import views

urlpatterns = [
    path(f'login/<str:backend>/', views.authenticate_user, name='oauth_login'),
]
