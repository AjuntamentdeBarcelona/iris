from ariadna.serializers import AriadnaSerializer
from ariadna.filtersets import AriadnaFilter
from ariadna.models import Ariadna
from rest_framework.generics import RetrieveDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet


class AriadnaViewsMixin:
    permission_classes = (IsAuthenticated,)
    serializer_class = AriadnaSerializer
    queryset = Ariadna.objects.order_by('used', '-presentation_date')


class AriadnaList(AriadnaViewsMixin, ModelViewSet):
    """
    Ariadna endpoint to list and create ariadna instances.
    List can be filtered passing GET parameters:
     - year by exact
     - input_number by exact
     - used by exact
     - presentation_date by gt, gte, lt and lte
    """

    filterset_class = AriadnaFilter

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset()
        year = self.request.GET.get("year")
        input_number = self.request.GET.get("input_number")
        if year and input_number:
            queryset = queryset.filter(year=year, input_number=input_number)
        return queryset


class AriadnaRetrieveDestroyView(AriadnaViewsMixin, RetrieveDestroyAPIView):
    """
    Ariadna instance detail retrieve or delete endpoint.
    Acces by year and instand code. The lookup is done by both kwargs.
    """

    lookup_field = "code"
    lookup_url_kwarg = "code"

    def get_object(self):
        input_number = str(self.kwargs['input_number']).zfill(6)
        self.kwargs["code"] = "{year}/".format(**self.kwargs) + input_number
        return super().get_object()
