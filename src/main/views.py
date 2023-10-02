from urllib.parse import quote_plus

from django.conf import settings
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin, UpdateModelMixin, ListModelMixin
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_403_FORBIDDEN, HTTP_400_BAD_REQUEST, HTTP_204_NO_CONTENT
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from main.api.serializers import GetGroupFromRequestMixin
from main.serializers import HelloSerializer, MeSerializer
from main.tasks import celery_test_task, invalidate_cachalot
from main.utils import get_user_traceability_id


class InvalidateCache(APIView):
    """
    get:

    Hello API call returns a warm welcome for all the IRIS2 users.
    """
    serializer_class = HelloSerializer

    @swagger_auto_schema(
        operation_id='Hello IRIS',
        responses={
            status.HTTP_200_OK: HelloSerializer,
        })
    def post(self, request, *args, **kwargs):
        invalidate_cachalot()
        return Response(self.serializer_class(instance={}).data, status=status.HTTP_200_OK)


class MeView(APIView):
    """
    get:

    Me call returns information about the logged user.
    """
    serializer_class = MeSerializer

    @swagger_auto_schema(operation_id='me')
    def get(self, request, *args, **kwargs):
        user = request.user
        user_dict = {
            'fullname': user.get_full_name() or user.username,
            'email': user.email,
            'user_id': get_user_traceability_id(user),
            'username': user.username,
        }

        return Response(self.serializer_class(instance=user_dict).data, status=status.HTTP_200_OK)


@method_decorator(name='post', decorator=swagger_auto_schema(
    responses={
        HTTP_200_OK: 'Task enqueued',
    }
))
class CeleryTestTask(APIView):
    def post(self, request, *args, **kwargs):
        celery_test_task.delay()
        return Response(status=HTTP_200_OK)


class IsRetrieveMixin:

    @property
    def is_retrieve(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        return lookup_url_kwarg in self.kwargs


class MultipleSerializersMixin(IsRetrieveMixin):
    short_serializer_class = None

    def get_serializer_class(self):
        if self.request.method == 'GET' and not self.is_retrieve and self.short_serializer_class:
            return self.short_serializer_class
        return super().get_serializer_class()


class ModelCRUViewSet(MultipleSerializersMixin, CreateModelMixin, RetrieveModelMixin, UpdateModelMixin, ListModelMixin,
                      GenericViewSet):
    """
    A viewset that provides default `create()`, `retrieve()`, `update()`, `partial_update()`, and `list()` actions.
    Important: this view does not allow to delete a record, it not has the destroy() method
    """
    permission_classes = (IsAuthenticated, )


class ModelListRetrieveUpdateViewSet(MultipleSerializersMixin, RetrieveModelMixin, UpdateModelMixin, ListModelMixin,
                                     GenericViewSet):
    """
    A viewset that provides default retrieve()`, `update()`, `partial_update()`, and `list()` actions.
    Important: this view does not allow to delete a record, it not has the destroy() method
    """
    permission_classes = (IsAuthenticated, )


class UpdatePatchAPIView(UpdateModelMixin, GenericAPIView):
    """
    A view for updating a model instance. with only a patch operation
    """
    permission_classes = (IsAuthenticated, )

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)


class UpdateListView(APIView):
    """
    A view to update N objects in one request. If all data is valid, the objects will be updated. Else,
    a dictionary with the errors for each no valid object will be returned
    """

    serializer_class = None
    model_class = None

    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        invalids = {}
        serializers = [self.get_serializer_class()(instance=self.get_instance(object_data),
                                                   data=object_data) for object_data in request.data]
        for ser in serializers:
            if not ser.is_valid():
                invalids[ser.initial_data['id']] = ser.errors
        if invalids:
            return JsonResponse(invalids, status=HTTP_400_BAD_REQUEST)
        else:
            for ser in serializers:
                ser.save()
            return JsonResponse({}, status=HTTP_204_NO_CONTENT)

    def get_serializer_class(self):
        if not self.serializer_class:
            raise NotImplementedError
        return self.serializer_class

    def get_model_class(self):
        if not self.model_class:
            raise NotImplementedError
        return self.model_class

    def get_instance(self, object_data):
        model_class = self.get_model_class()
        try:
            return model_class.objects.get(pk=object_data['id'])
        except model_class.DoesNotExist:
            return None


class PermissionCustomSerializerMixin(IsRetrieveMixin, GetGroupFromRequestMixin):
    """
    Select a different serializer for an object depending on user permissions
    """

    no_permission_serializer = None
    no_permission_list_serializer = None

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        user_group = self.get_group_from_request(request)
        serializer = self.get_serialized_instance(user_group, instance)
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        user_group = self.get_group_from_request(request)
        page = self.paginate_queryset(queryset)
        if page is not None:
            return self.get_paginated_response(self.get_list_serialized_data(user_group, page))

        return Response(self.get_list_serialized_data(user_group, queryset))

    def update(self, request, *args, **kwargs):
        user_group = self.get_group_from_request(request)
        instance = self.get_object()
        if self.item_must_be_checked(instance):
            if not self.group_is_allowed(user_group, instance):
                return Response(_("You don't have permissions to do this actions"), status=HTTP_403_FORBIDDEN)

        return super().update(request, *args, **kwargs)

    def get_list_serialized_data(self, user_group, items):
        items_data = []
        for item in items:
            items_data.append(self.get_serialized_instance(user_group, item).data)
        return items_data

    def get_serialized_instance(self, user_group, instance):
        """
        Select seralizer depending on the group permissions and if the instance must be checked

        :param user_group: Group assigned to the user
        :param instance: Object to retrieve
        :return: Serialized instance
        """
        if self.item_must_be_checked(instance) and self.group_is_allowed(user_group, instance):
            serializer = self.get_serializer(instance)
        elif self.item_must_be_checked(instance):
            serializer = self.get_no_permission_serializer(instance)
        else:
            serializer = self.get_serializer(instance)
        return serializer

    def item_must_be_checked(self, instance):
        """
        Check if instance retrieve depend on permissions or not
        :param instance: Object to retrieve
        :return: True if instance must be checked or not
        """
        return True

    def group_is_allowed(self, user_group, instance):
        """
        Check if user's groups is allowed to read all the information or not

        :param user_group: Group assigned to the user
        :param instance: Object to retrieve
        :return: True if user's group has permissions to see all data
        """
        return False

    def get_no_permission_serializer(self, *args, **kwargs):
        """
        Return the serializer instance that should be used for validating and
        deserializing input, and for serializing output.
        """
        if not self.is_retrieve and self.no_permission_list_serializer:
            serializer_class = self.no_permission_list_serializer
        else:
            serializer_class = self.no_permission_serializer

        kwargs['context'] = self.get_serializer_context()
        return serializer_class(*args, **kwargs)


class AuthMethodsAPIView(APIView):
    """
    Lists the auth options and its public configuration to the frontend.

    todo: Generate URL for login using python social auth
    todo: move to another package
    """
    permission_classes = [AllowAny]

    def get(self, request):
        url = settings.OAUTH_AUTHORIZATION_URL
        client_id = settings.SOCIAL_AUTH_IRIS_OIDC_KEY
        redirect = quote_plus(settings.OAUTH_REDIRECT_LOGIN_URL)
        return Response([
            {
                'codename': 'oauth',
                'type': 'redirect',
                'label': 'Login con Ayuntamiento',
                'url': f'{url}?scope=openid&response_type=code&redirect_uri={redirect}&client_id={client_id}'
            }
        ])
