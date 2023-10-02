from django.db.models import Q, Prefetch, OuterRef, Exists
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend

from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, permissions, status
from rest_framework.filters import OrderingFilter
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST
from rest_framework.views import APIView

from excel_export.mixins import (ExcelExportListMixin, ExcelTranslatableDescriptionExportMixin,
                                 ExcelDescriptionExportMixin)
from iris_masters.models import RecordState, Parameter, RecordType
from iris_masters.views import (BasicMasterViewSet, BasicMasterListApiView, BasicMasterSearchMixin,
                                BasicMasterAdminPermissionsMixin, AutocompleteBaseSearchView,
                                BasicOrderingFieldsSearchMixin)
from main.api.filters import UnaccentSearchFilter
from main.api.pagination import IrisMaxPagination
from main.api.schemas import (destroy_swagger_auto_schema_factory, create_swagger_auto_schema_factory,
                              update_swagger_auto_schema_factory, get_swagger_auto_schema_factory,
                              list_swagger_auto_schema_factory, retrieve_swagger_auto_schema_factory)
from main.api.serializers import GetGroupFromRequestMixin
from main.utils import get_translated_fields, get_user_traceability_id
from main.views import MultipleSerializersMixin, UpdateListView
from profiles.models import Group
from profiles.permissions import IrisPermissionChecker
from record_cards.models import RecordCard
from record_cards.permissions import RECARD_THEME_CHANGE_SYSTEM
from themes.actions.possible_theme_change import PossibleThemeChange
from themes.actions.theme_copy import ElementDetailCopy
from themes.filters import ElementDetailFilter, ElementFilter
from themes.actions.group_tree import GroupThemeTree
from themes.models import (Area, Element, ElementDetail, ThemeGroup, ElementDetailFeature, ApplicationElementDetail,
                           Keyword, Zone)
from themes.serializers import (ElementDetailFeatureListSerializer, ElementListSerializer, AreaListSerializer,
                                AreaSerializer, ElementSerializer, ElementDetailSerializer,
                                ElementDetailCreateSerializer, ElementDetailListSerializer,
                                ElementDetailSearchSerializer, ThemeGroupSerializer, ElementDetailCheckSerializer,
                                ElementDetailActiveSerializer, ElementDetailDeleteRegisterSerializer,
                                ElementDetailCopySerializer, ZoneSerializer)
from themes.actions.theme_set_ambits import ThemeSetAmbits
from themes.actions.theme_tree import ThemeTreeBuilder
from themes.tasks import rebuild_theme_tree, register_theme_ambits, elementdetail_delete_action_execute


@method_decorator(name="list", decorator=list_swagger_auto_schema_factory(ZoneSerializer))
class ZoneViewSet(ExcelDescriptionExportMixin, BasicOrderingFieldsSearchMixin,
                  BasicMasterAdminPermissionsMixin, BasicMasterViewSet):
    """
        Viewset to display theme Zones (List).
        The list endpoint:
         - can be exported to excel
         - can be ordered by description
         - supports unaccent search by description
        """

    queryset = Zone.objects.order_by("description")
    serializer_class = ZoneSerializer
    filename = "theme-zones.xlsx"
    ordering_fields = ["description"]
    search_fields = ["#description"]


@method_decorator(name="create", decorator=create_swagger_auto_schema_factory(ThemeGroupSerializer))
@method_decorator(name="update", decorator=update_swagger_auto_schema_factory(ThemeGroupSerializer))
@method_decorator(name="partial_update", decorator=update_swagger_auto_schema_factory(ThemeGroupSerializer))
@method_decorator(name="destroy", decorator=destroy_swagger_auto_schema_factory())
@method_decorator(name="list", decorator=list_swagger_auto_schema_factory(ThemeGroupSerializer))
class ThemeGroupViewSet(ExcelDescriptionExportMixin, BasicOrderingFieldsSearchMixin,
                        BasicMasterAdminPermissionsMixin, BasicMasterViewSet):
    """
    Viewset to manage ThemeGroups Medias (CRUD).
    Administration permission needed to create, update and destroy.
    The list endpoint:
     - can be exported to excel
     - can be ordered by description
     - supports unaccent search by description
    """

    queryset = ThemeGroup.objects.order_by("description")
    serializer_class = ThemeGroupSerializer
    filename = "theme-groups.xlsx"
    ordering_fields = ["description"]
    search_fields = ["#description"]


@method_decorator(name="create", decorator=create_swagger_auto_schema_factory(AreaSerializer))
@method_decorator(name="update", decorator=update_swagger_auto_schema_factory(AreaSerializer))
@method_decorator(name="partial_update", decorator=update_swagger_auto_schema_factory(AreaSerializer))
@method_decorator(name="destroy", decorator=destroy_swagger_auto_schema_factory())
@method_decorator(name="list", decorator=list_swagger_auto_schema_factory(AreaListSerializer))
@method_decorator(name="retrieve", decorator=retrieve_swagger_auto_schema_factory(AreaSerializer))
class AreaViewSet(ExcelTranslatableDescriptionExportMixin, BasicOrderingFieldsSearchMixin,
                  BasicMasterAdminPermissionsMixin, BasicMasterViewSet):
    """
    Viewset to manage Areas (CRUD).
    Administration permission needed to create, update and destroy.
    If the application is present on the request, only the areas on that application will be displayed
    The list endpoint:
     - can be exported to excel
     - can be ordered by language descriptions
     - supports unaccent search by language descriptions
    """

    serializer_class = AreaSerializer
    pagination_class = IrisMaxPagination
    short_serializer_class = AreaListSerializer
    filename = "areas.xlsx"

    def get_queryset(self):
        query_filters = Area.ENABLED_AREA_FILTERS
        if hasattr(self.request, "application"):
            area_pks = ApplicationElementDetail.objects.get_areapks_byapp(self.request.application)
            query_filters["pk__in"] = area_pks
        return Area.objects.filter(**query_filters).prefetch_related("areas").order_by("description")


@method_decorator(name="post", decorator=swagger_auto_schema(request_body=ElementDetailActiveSerializer(many=True),
                                                             responses={
                                                                 HTTP_204_NO_CONTENT: "Element Details updated",
                                                                 HTTP_400_BAD_REQUEST: "Bad request: Validation Error",
                                                             }))
class ElementDetailBulkActiveView(BasicMasterAdminPermissionsMixin, UpdateListView):
    """
    Endpoint to activate a set of ElemetnDetails in a bulk operation.
    Administration permission needed to perform the action.
    """
    serializer_class = ElementDetailActiveSerializer
    model_class = ElementDetail


@method_decorator(name="create", decorator=create_swagger_auto_schema_factory(ElementSerializer))
@method_decorator(name="update", decorator=update_swagger_auto_schema_factory(ElementSerializer))
@method_decorator(name="partial_update", decorator=update_swagger_auto_schema_factory(ElementSerializer))
@method_decorator(name="destroy", decorator=destroy_swagger_auto_schema_factory())
@method_decorator(name="list", decorator=list_swagger_auto_schema_factory(ElementListSerializer))
@method_decorator(name="retrieve", decorator=retrieve_swagger_auto_schema_factory(ElementSerializer))
class ElementViewSet(ExcelTranslatableDescriptionExportMixin, BasicOrderingFieldsSearchMixin,
                     BasicMasterAdminPermissionsMixin, BasicMasterViewSet):
    """
    Viewset to manage Elements (CRUD).
    Administration permission needed to create, update and destroy.
    If the application is present on the request, only the elements on that application will be displayed
    The list endpoint:
     - can be exported to excel
     - can be ordered by language descriptions
     - supports unaccent search by language descriptions
    """

    serializer_class = ElementSerializer
    filterset_fields = ("area_id",)
    pagination_class = IrisMaxPagination
    short_serializer_class = ElementListSerializer
    filename = "elements.xlsx"

    def get_queryset(self):
        query_filters = Element.ENABLED_ELEMENT_FILTERS.copy()

        if hasattr(self.request, "application"):
            element_pks = ApplicationElementDetail.objects.get_elementpks_byapp(self.request.application)
            query_filters["pk__in"] = element_pks
        details = ElementDetail.objects.filter(element_id=OuterRef('id'), deleted__isnull=True)
        return Element.objects.annotate(
            is_query=Exists(details.filter(record_type_id=RecordType.QUERY)),
            is_issue=Exists(details.exclude(record_type_id=RecordType.QUERY)),
        ).filter(
            **query_filters
        ).order_by("-is_issue", "description").select_related("area").prefetch_related("elements")


class ActiveVisibleElementDetailMixin:

    def get_element_details(self):
        element_details = ElementDetail.objects.filter(
            Q(activation_date__lte=timezone.now().date()) | Q(activation_date__isnull=True),
            active=True, **ElementDetail.ENABLED_ELEMENTDETAIL_FILTERS)
        if IrisPermissionChecker.get_for_user(self.request.user).has_permission(RECARD_THEME_CHANGE_SYSTEM):
            return element_details
        # If user has not RECARD_THEME_CHANGE_SYSTEM, only the visible details can be retrieved
        return element_details.filter(Q(visible_date__lte=timezone.now().date()) | Q(visible_date__isnull=True),
                                      visible=True)


class AreaAutocompleteSearchView(ActiveVisibleElementDetailMixin, AutocompleteBaseSearchView):
    """
    List of Areas with search for autocomplete purpose
    """
    model = Area

    def get_queryset(self):
        area_ids = self.get_element_details().values_list("element__area_id", flat=True)
        return self.model.objects.filter(id__in=area_ids)


class ElementAutocompleteSearchView(ActiveVisibleElementDetailMixin, AutocompleteBaseSearchView):
    """
    List of Elements with search for autocomplete purpose. Elements can be filtered by Area.
    """

    model = Element
    filterset_class = ElementFilter

    def get_queryset(self):
        element_ids = self.get_element_details().values_list("element_id", flat=True)
        return self.model.objects.filter(id__in=element_ids)


class ElementDetailAutocompleteSearchView(ActiveVisibleElementDetailMixin, AutocompleteBaseSearchView):
    """
    List of ElementDetails with search for autocomplete purpose. The list endpoint can be filtered by area, element,
    keywords, record_type, active, activation date
    """

    model = ElementDetail
    queryset_filters = ElementDetail.ENABLED_ELEMENTDETAIL_FILTERS.copy()
    filterset_class = ElementDetailFilter

    def get_queryset(self):
        return self.get_element_details()


class ElementDetailQuerySetMixin:
    def get_queryset(self):
        query_filters = ElementDetail.ENABLED_ELEMENTDETAIL_FILTERS.copy()
        if hasattr(self.request, "application"):
            element_details_pks = ApplicationElementDetail.objects.get_elementdetailpks_byapp(self.request.application)
            query_filters["pk__in"] = element_details_pks
        return ElementDetail.objects.filter(**query_filters).order_by(
            "order", "element__order", "element__area__order").select_related(
            "element", "element__area", "process", "record_type").prefetch_related(
            Prefetch("keyword_set", queryset=Keyword.objects.filter(enabled=True)),
            Prefetch("recordcard_set",
                     queryset=RecordCard.objects.filter(enabled=True, record_state_id__in=RecordState.OPEN_STATES)),
            "feature_configs")


class ElementDetailOrderingMixin(BasicOrderingFieldsSearchMixin):
    ordering_fields = get_translated_fields("description") + ["active", "activation_date"]


@method_decorator(name="get", decorator=swagger_auto_schema(
    operation_id="theme_details_list",
    responses={
        status.HTTP_200_OK: ElementDetailListSerializer,
        status.HTTP_403_FORBIDDEN: "Acces not Allowed"
    }
))
@method_decorator(name="post", decorator=create_swagger_auto_schema_factory(ElementDetailCreateSerializer))
class ElementDetailListCreateView(ExcelExportListMixin, ElementDetailQuerySetMixin, ElementDetailOrderingMixin,
                                  MultipleSerializersMixin, BasicMasterAdminPermissionsMixin,
                                  generics.ListCreateAPIView):
    """
    Viewset to create and list ElementDetails.
    Administration permission needed to create, update and destroy.
    If the application is present on the request, only the element details on that application will be displayed.

    When an ElementDetail is created, a task to register theme ambits is delayed.

    The list endpoint:
     - can be exported to excel
     - can be ordered by language descriptions, active and activation_date
     - supports unaccent search by language descriptions
     - can be filtered by area, element, keywords, record_type, active, activation date
    """

    serializer_class = ElementDetailCreateSerializer
    pagination_class = IrisMaxPagination
    filterset_class = ElementDetailFilter
    filter_backends = (UnaccentSearchFilter, DjangoFilterBackend, OrderingFilter)
    short_serializer_class = ElementDetailListSerializer
    filename = "element_details.xlsx"
    nested_excel_fields = {
        ExcelExportListMixin.NESTED_BASE_KEY: ["element", "description_ca", "description_es", "description_en",
                                               "is_visible", "active", "activation_date"],
        "element": {
            ExcelExportListMixin.NESTED_BASE_KEY: ["description", "area"],
            "area": {
                ExcelExportListMixin.NESTED_BASE_KEY: ["description"]
            }
        },
    }

    def perform_create(self, serializer):
        element_detail = serializer.save()
        register_theme_ambits.delay(element_detail.pk)


class ElementDetailSearchView(ElementDetailQuerySetMixin, ElementDetailOrderingMixin, BasicMasterListApiView):
    """
    List of ElementDetails with search, to retrieve the activated items. The list endpoint can be filtered by area,
    element, keywords, record_type, active, activation date
    """

    search_fields = get_translated_fields("#short_description")
    filterset_class = ElementDetailFilter
    serializer_class = ElementDetailSearchSerializer

    def get_queryset(self):
        queryset = super().get_queryset().filter(
            Q(activation_date__lte=timezone.now().date()) | Q(activation_date__isnull=True), active=True)
        permission_checker = IrisPermissionChecker.get_for_user(self.request.user)

        # If user has the permission to create RecordCard with no visible themes, the queryset is retudned
        if permission_checker.has_permission(RECARD_THEME_CHANGE_SYSTEM):
            return queryset

        # else, the queryset has to be filtered by visible date (visibility)
        return queryset.filter(Q(visible_date__lte=timezone.now().date()) | Q(visible_date__isnull=True), visible=True)


class TwitterDetailSearch(ElementDetailSearchView):
    """
     List of ElementDetails with search, to retrieve the activated items for twitter theme application.
     The list endpoint can be filtered by area, element, keywords, record_type, active, activation date
     """

    def get_queryset(self):
        return super().get_queryset().filter(
            applicationelementdetail__application_id=int(Parameter.get_parameter_by_key('TWITTER_THEME_APPLICATION', 1))
        ).exclude(record_type_id=5).distinct()


@method_decorator(name="put", decorator=update_swagger_auto_schema_factory(ElementDetailSerializer))
@method_decorator(name="patch", decorator=update_swagger_auto_schema_factory(ElementDetailSerializer))
@method_decorator(name="delete", decorator=destroy_swagger_auto_schema_factory())
class ElementDetailRetrieveUpdateDestroyView(BasicMasterAdminPermissionsMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    Viewset to manage Element Detail (RUD).
    Administration permission needed to create, update and destroy.
    ElementDetail can not be deleted as it's used in an open RecordCard
    """
    serializer_class = ElementDetailSerializer
    permission_classes = (permissions.IsAuthenticated,)
    queryset = ElementDetail.objects.filter(**ElementDetail.ENABLED_ELEMENTDETAIL_FILTERS).order_by("description")

    def get_queryset(self):
        return super().get_queryset().prefetch_related("element")

    def perform_update(self, serializer):
        element_detail = serializer.save()
        register_theme_ambits.delay(element_detail.pk)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not instance.can_be_deleted:
            return Response(_("ElementDetail can not be deleted as it's used in an open RecordCard"),
                            status=status.HTTP_400_BAD_REQUEST)
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(name="post", decorator=swagger_auto_schema(
    request_body=ElementDetailSerializer,
    responses={
        status.HTTP_200_OK: ElementDetailCheckSerializer,
        status.HTTP_400_BAD_REQUEST: "Bad request: Validation Error",
        status.HTTP_403_FORBIDDEN: "Acces not allowed",
    }
))
class ElementDetailCheckView(BasicMasterAdminPermissionsMixin, APIView):
    """
    Endpoint to check if ElementDetail:
     - can be saved
     - miss mandatory fields
     - will be activated after modification
    """

    def post(self, request, *args, **kwargs):
        instance = get_object_or_404(ElementDetail, pk=self.kwargs["pk"])
        serializer = ElementDetailSerializer(instance, data=request.data, context=self.get_serializer_context())

        if serializer.is_valid(raise_exception=True):

            validated_data = serializer.validated_data
            if not self.check_active_mandatory_fields(validated_data):
                response = {
                    "can_save": True,
                    "mandatory_fields_missing": True,
                    "will_be_active": False,
                }
            else:
                active = validated_data.get("active", False)
                if not active:
                    response = {
                        "can_save": True,
                        "mandatory_fields_missing": False,
                        "will_be_active": False,
                    }
                else:
                    response = {
                        "can_save": True,
                        "mandatory_fields_missing": False,
                        "will_be_active": True,
                    }

            return Response(ElementDetailCheckSerializer(instance=response).data, status=status.HTTP_200_OK)

    @staticmethod
    def check_active_mandatory_fields(validated_data):
        """
        Check if the mandatory fields to set the theme as active are filled or not

        :param validated_data: Dict with validated data of the serializer
        :return: True if all mandatory fields are filled, else False
        """

        for field in ElementDetail.ACTIVE_MANDATORY_FIEDLS:
            if not validated_data.get(field):
                return False
        for relationship in ElementDetail.RELATION_ACTIVE_MANDATORY:
            if not validated_data.get(relationship, []):
                return False
        return True

    def get_serializer_context(self):
        """
        Extra context provided to the serializer class.
        """
        return {
            "request": self.request,
            "format": self.format_kwarg,
            "view": self
        }


@method_decorator(name="post", decorator=swagger_auto_schema(
    responses={
        status.HTTP_204_NO_CONTENT: "Element position updated",
        status.HTTP_403_FORBIDDEN: "Acces not allowed"
    }
))
class SetPositionView(BasicMasterAdminPermissionsMixin, APIView):
    """
    Endpoint to set the new position (order) to the indicated object
    """
    model_class = None
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        if not self.model_class:
            raise NotImplementedError("You must set the model_class attribute.")

        obj = get_object_or_404(self.model_class, **self.get_query_parameters())
        obj.to(self.kwargs["position"])

        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_query_parameters(self):
        query_parameters = {
            "pk": self.kwargs["pk"]
        }

        extra_parameters = {
            ElementDetail: ElementDetail.ENABLED_ELEMENTDETAIL_FILTERS.copy(),
            Element: Element.ENABLED_ELEMENT_FILTERS.copy(),
            Area: Area.ENABLED_AREA_FILTERS.copy()
        }
        query_parameters.update(extra_parameters.get(self.model_class, {}))
        return query_parameters


class ElementDetailChangeListView(GetGroupFromRequestMixin, BasicMasterSearchMixin, BasicMasterListApiView):
    """
    Given a RecordCard and the group that does the request, retrieve a list of the possible ElementDetails
    to change the RecordCard detail.
    """
    search_fields = get_translated_fields("#short_description")
    filterset_fields = ("element_id",)
    filterset_class = ElementDetailFilter
    serializer_class = ElementDetailSearchSerializer
    pagination_class = None

    @cached_property
    def record_card(self):
        try:
            return RecordCard.objects.select_related('ubication').get(pk=self.kwargs["id"])
        except RecordCard.DoesNotExist:
            raise Http404

    def get_queryset(self):
        group = self.get_group_from_request(self.request)
        return PossibleThemeChange(self.record_card, group).themes_to_change().select_related(
            "element", "element__area").prefetch_related(
            Prefetch("keyword_set", queryset=Keyword.objects.filter(enabled=True)),
            Prefetch("recordcard_set",
                     queryset=RecordCard.objects.filter(enabled=True, record_state_id__in=RecordState.OPEN_STATES)))


@method_decorator(name="get", decorator=get_swagger_auto_schema_factory(
    ok_message="Tasks to set themes ambits on the queue"))
class ElementDetailAmbitTaskView(APIView):
    """
    Delay a celery task to register the element details ambits
    """

    def get(self, request, *args, **kwargs):
        ThemeSetAmbits().set_theme_ambits()
        return Response(None, status=status.HTTP_200_OK)


class ElementDetailFeaturesListView(BasicMasterListApiView):
    """
    Given an ElementDetail, the endpoint retrieves the list of features
    """
    serializer_class = ElementDetailFeatureListSerializer

    def get_queryset(self):
        return ElementDetailFeature.objects.filter(
            element_detail_id=self.kwargs["id"], enabled=True, feature__deleted__isnull=True
        ).select_related("feature", "feature__values_type", "feature__mask"
                         ).prefetch_related("feature__values_type__values_set")


@method_decorator(name="get", decorator=get_swagger_auto_schema_factory(ok_message="Element Details Tree"))
class GetThemesTreeView(APIView):
    """
    Endpoint to retrieve the theme tree, with Area-Element-ElementDetail structure
    """

    builder_class = ThemeTreeBuilder

    def get(self, request, *args, **kwargs):
        builder = self.builder_class()
        tree_etag = builder.get_cache_mark()
        user_etag = request.META.get('HTTP_IF_NONE_MATCH', -1)
        if tree_etag == user_etag:
            return Response(status=status.HTTP_304_NOT_MODIFIED, headers={
                'ETag': builder.get_cache_mark(),
                'Cache-Control': 'no-cache'
            })

        response = builder.build()
        return Response(response, status=status.HTTP_200_OK, headers={
            'ETag': builder.get_cache_mark(),
            'Cache-Control': 'no-cache'
        })


class ThemeCacheView(APIView):
    """
    Endpoint to manage the theme tree cache.
    At the post method, it rebuilds the theme tree. If sync is on GET parameters, it does the action at the moment. Else
    the action is delayed on celery.
    At the delete method, it cleares the cached tree.
    """
    builder_class = ThemeTreeBuilder

    def delete(self, *args, **kwargs):
        self.builder_class().clear_cache()
        return Response("", status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        rebuild_theme_tree() if "sync" in request.GET else rebuild_theme_tree.delay()
        return Response("", status=status.HTTP_200_OK)


@method_decorator(name="post", decorator=create_swagger_auto_schema_factory(ElementDetailDeleteRegisterSerializer))
class CreateElementDetailDeleteRegisterView(BasicMasterAdminPermissionsMixin, CreateAPIView):
    """
    Endpoint to register an ElementDetail deletion.
    First, the register is done and after that, the deletion can be processed.
    After deletion, a post delete process is thrown, where the records that have this ElementDetail will be changed.
    """

    permission_classes = (IsAuthenticated,)
    serializer_class = ElementDetailDeleteRegisterSerializer

    def perform_create(self, serializer):
        instance = serializer.save()
        # Once ElementDetail delete register is created, we can delete the ElementDetail and perform the
        # ElementDetail's post delete action
        instance.deleted_detail.delete()
        elementdetail_delete_action_execute.delay(instance.pk)


@method_decorator(name="post", decorator=swagger_auto_schema(
    request_body=ElementDetailCopySerializer,
    responses={
        status.HTTP_201_CREATED: ElementDetailSerializer,
        status.HTTP_400_BAD_REQUEST: "Bad request: Validation Error",
        status.HTTP_403_FORBIDDEN: "Acces not allowed",
        status.HTTP_404_NOT_FOUND: "Element Detail does not exist"
    }
))
class ElementDetailCopyView(BasicMasterAdminPermissionsMixin, APIView):
    """
    Endpoint to make a copy of an ElementDetail, with a new description. If a new element is not set, it uses the
    ElementDetail of the copied register.
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        element_detail = get_object_or_404(ElementDetail, pk=self.kwargs["pk"], deleted__isnull=True)

        data = request.data.copy()
        if "element_id" not in data:
            data["element_id"] = element_detail.element_id

        serializer = ElementDetailCopySerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            copied_element_detail = ElementDetailCopy(element_detail).copy(
                get_user_traceability_id(self.request.user), serializer.validated_data)
            return Response(
                ElementDetailSerializer(instance=copied_element_detail).data, status=status.HTTP_201_CREATED)


class GroupThemeTreeListView(generics.ListAPIView):
    """
    Return a list of ElementDetails for a given group and a district
    """
    permission_classes = []
    pagination_class = None
    serializer_class = ElementDetailListSerializer
    queryset = ElementDetail.objects.all()

    @cached_property
    def group(self):
        if getattr(self, 'swagger_fake_view', False):
            return Group.objects.first()
        return get_object_or_404(Group, pk=self.kwargs.get('pk'))

    def get_queryset(self):
        return GroupThemeTree(self.group).themes_for_district(district=self.request.GET.get('district', None))
