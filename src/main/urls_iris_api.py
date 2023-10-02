from django.urls import include, path
from django.utils.decorators import method_decorator

from integrations.views import ExternalServiceDummy
from main.iris_roles import backoffice_roles
from main.views import MeView, AuthMethodsAPIView
from public_api.views import RecordCardSSIListView, FurniturePickUpView

urlpatterns = [
    path("auth/methods/", AuthMethodsAPIView.as_view(), name="auth-methods"),
    path("me/", MeView.as_view(), name="me"),
    path("theme/", include(("themes.urls", "themes"), namespace="themes")),
    path("masters/", include(("iris_masters.urls", "iris_masters"), namespace="iris_masters")),
    path("templates/", include(("iris_templates.urls", "iris_templates"), namespace="iris_templates")),
    path("profiles/", include(("profiles.urls", "profiles"), namespace="profiles")),
    path("record_cards/", include(("record_cards.urls", "record_cards"), namespace="record_cards")),
    path("reports/", include(("reports.urls", "reports"), namespace="reports")),
    path("features/", include(("features.urls", "features"), namespace="features")),
    path("integrations/", include(("integrations.urls", "integrations"), namespace="integrations")),
    path("communications/", include(("communications.urls", "communications"), namespace="communications")),
    path("ssi/records/", RecordCardSSIListView.as_view(), name="records_ssi"),
    path("external-tramits/test/", ExternalServiceDummy.as_view(), name="external_tramits_test"),
    path("protocols/", include(("protocols.urls", "protocols"), namespace="protocols")),
    path("ariadna/", include(("ariadna.urls", "ariadna"), namespace="ariadna")),
    path("quioscs/", include(("quioscs.urls", "quioscs"), namespace="quioscs")),
    path("supports-info/", include(("support_info.urls", "support_info"), namespace="support_info")),
    path("management/", include(("public_external_processing.urls", "public_external_processing"),
                                namespace="public_external_processing")),
    path("furniture/pick-up/", method_decorator(name="get", decorator=backoffice_roles)(FurniturePickUpView).as_view(),
         name="furniture_pick_up"),
    path("post-migrate/", include(("post_migrate.urls", "post_migrate"), namespace="post_migrate")),
    path("geo_proxy/", include(("geo_proxy.urls", "geo_proxy"), namespace="geo_proxy")),
]
