from rest_framework.routers import DefaultRouter

from protocols import views

urlpatterns = []

protocols_router = DefaultRouter()
protocols_router.register(r"", views.ProtocolsViewSet)
protocols_router.register(r"admin", views.ProtocolsIdViewSet)

urlpatterns += protocols_router.urls
