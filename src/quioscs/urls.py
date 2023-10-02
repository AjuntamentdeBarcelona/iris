from django.urls import path

from quioscs.views import ElementDetailSearchView, ElementDetailRetrieveView, RecordCardCreateView

urlpatterns = [
    path('details/', ElementDetailSearchView.as_view(), name='details_list'),
    path('details/<int:pk>/', ElementDetailRetrieveView.as_view(), name='details_detail'),
    path('record_cards/', RecordCardCreateView.as_view(), name='record_card_create'),
]
