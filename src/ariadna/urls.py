from django.urls import path, re_path
from ariadna.views import AriadnaList, AriadnaRetrieveDestroyView

urlpatterns = [
    path("", AriadnaList.as_view({"get": "list", "post": "create"}), name="ariadna"),
    re_path(r"(?P<year>([0-9]){4})/(?P<input_number>([0-9]){3,7})/",
            AriadnaRetrieveDestroyView.as_view(), name="ariadna_detail"),
]
