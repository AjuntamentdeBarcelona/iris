from django.urls import path
from rest_framework.routers import DefaultRouter

from features.views import ValuesTypeViewSet, FeatureViewSet, MaskListView

features_router = DefaultRouter()

features_router.register(r"values_types", ValuesTypeViewSet)
features_router.register(r"features", FeatureViewSet)

urlpatterns = features_router.urls + [
    path(r"masks/", MaskListView.as_view(), name="mask_list"),
]
