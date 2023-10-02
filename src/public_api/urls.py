from django.urls import path, include

from geo_proxy import views as geo_views

from public_api import views
SSI_RECORDS_URL = "ssi/records/"

urlpatterns = [
    path("areas", views.AreaList.as_view(), name="area"),
    path("elements", views.ElementList.as_view(), name="element"),
    path("elements/favourites", views.ElementFavouriteList.as_view(), name="element_favourite"),
    path("details", views.ElementDetailSearchView.as_view(), name="element_detail_search"),
    path("details/<int:pk>/fields", views.ElementDetailRetrieveView.as_view(), name="element_detail_retrieve"),
    path("details/last_updated/", views.ElementDetailLastUpdated.as_view(), name="element_detail_last_updated"),
    path("incidences", views.RecordCardCreateView.as_view(), name="record_card_create"),
    path("incidences/<int:pk>", views.RecordCardRetrieveView.as_view(), name="record_card_retrieve"),
    path("incidences/retrieve/<str:reference>", views.RecordCardRetrieveView.as_view(), name="record_card_retrieve"),
    path("incidences/<str:reference>/claim/", views.RecordCardClaimCreateView.as_view(), name="record_card_retrieve"),
    path("incidences/state/<slug:pk>", views.RecordCardRetrieveStateView.as_view(
            lookup_field="normalized_record_id", lookup_url_kwarg="pk"), name="recordcard_retrieve_state"),
    path("districts", views.DistrictList.as_view(), name="district_list"),
    path("geocod/", include(("integrations.services.gcod.urls", "geocod services"), namespace="geocod services")),
    path("input_channels/", views.InputChannelListView.as_view(), name="input_channels_list"),
    path("applicant_types/", views.ApplicantTypeListView.as_view(), name="applicant_types_list"),
    path("record_types/", views.RecordTypeListView.as_view(), name="record_types_list"),
    path("communications/<str:hash>/record_card/", views.MessageHashDetailView.as_view()),
    path("communications/<str:hash>/", views.MessageHashCreateView.as_view(), name="message_create_hash"),
    path("", include(("surveys.urls", "surveys"), namespace="surveys")),
    path(SSI_RECORDS_URL, views.RecordCardSSIListView.as_view(), name="records_ssi"),
    path("mobile/record_cards/", views.RecordCardMobileCreateView.as_view(), name="record_card_mobile_create"),
    path("furniture_pick_up/", views.FurniturePickUpView.as_view(), name="furniture_pick_up"),
    path("parameters/", views.ParameterListATEVisibleView.as_view(), name="parameters_ate_list"),
    path("parameters/<str:parameter>/", views.ParameterDetailATEVisibleView.as_view(), name="parameters_ate_detail"),
    path("mario/", views.MarioView.as_view(), name="mario"),
    path('geo_proxy/ubication/search/', geo_views.GeoProxySearchListView.as_view(permission_classes=[])),
    path('geo_proxy/ubication/reverse/', geo_views.GeoProxyReverseListView.as_view(permission_classes=[])),
]
