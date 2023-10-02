import json
import uuid

import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.http import urlencode
from drf_yasg import openapi
from model_mommy import mommy
from rest_framework import status
from rest_framework.status import HTTP_403_FORBIDDEN, HTTP_204_NO_CONTENT, HTTP_200_OK
from rest_framework.test import APIClient
from safedelete import HARD_DELETE

from iris_masters.permissions import MASTERS_EXCEL
from main.urls import OPEN_API_URL_NAME
from profiles.models import Group


@pytest.mark.django_db
class BaseOpenAPITest:
    """
    BaseClass for creating RestFramework view tests that take advantage of the OpenAPI specification. The main goals
    of this class are:
     - Check if an API call is conformant to the OpenAPI schema defined.
     - Give abstractions for creating integration and functional API tests.
     - Generate deterministic test cases easily.

    This class can be extended for more common and concrete use cases.
    """
    path = None
    open_api_format = '.json'
    open_api_url_name = OPEN_API_URL_NAME
    base_api_path = '/api'
    cached_spec = None
    api_client_cls = APIClient
    use_extra_get_params = False

    @cached_property
    def client(self):
        return self.given_an_api_client()

    def given_an_api_client(self):
        """
        :return: APIClient instance for running the requests.
        """
        return self.api_client_cls()

    def given_a_user(self):
        return self.user

    @cached_property
    def user(self):
        """
        :return: User for authenticated requests, override for custom needs.
        """
        user = User.objects.create(username='test')
        setattr(user, 'imi_data', {'user': 'test', 'dptcuser': str(uuid.uuid4())[:10]})
        return user

    def operation_test(self, method, path, path_spec, force_params=None, format_value='json'):
        """
        Tests an operation for the given OpenAPI path. This method runs the operation and checks if the response is
        conformant to its OpenAPI specification.

        This can be useful for detecting:
         - HTTP Response types not expected in your OpenAPI schema definition.

        In the near future this class will also check:
         - if the response data is conformant to the OpenAPI schema definition.

        :param method:
        :param path:
        :param path_spec:
        :param force_params:
        :param format_value:
        :return:
        """
        self.when_is_authenticated()
        response = self.operation(method, path, path_spec, force_params, format_value=format_value)
        self.should_return_response(response, path_spec)
        return response

    def operation(self, method, path, path_spec, force_params=None, format_value='json'):
        """
        Executes one of the operations of the path (each path is composed of n operations that could be run with a
        request).
        :param method: HTTP verb.
        :param path: Relative URI of the operation.
        :param path_spec: OpenAPI spec as dict for part.
        :param force_params: Explicitly force params.
        :param format_value: request format
        :return: Response for the request made for executing the operation.
        """
        body = self.get_body_parameters(path_spec, force_params)
        return getattr(self.client, method)(self.prepare_path(path, path_spec, force_params), body, format=format_value)

    def when_is_authenticated(self):
        """
        Authenticates the next request.
        """
        user = self.given_a_user()
        self.client.force_authenticate(user=user)
        return user

    def prepare_path(self, path, path_spec, force_params=None):
        """
        :param path: Relative URI of the operation.
        :param path_spec: OpenAPI spec as dict for part.
        :param force_params: Explicitly force params.
        :return: Path for performing a request to the given OpenAPI path.
        """
        endpoint_path = '{}{}?{}'.format(
            self.base_api_path,
            path.format(**self.prepare_parameters(self.get_parameters(path_spec, openapi.IN_QUERY), force_params)),
            urlencode({"page_size": force_params["page_size"]}) if force_params and "page_size" in force_params else ""
        )
        if self.use_extra_get_params:
            force_params.pop("page_size", None)
            querystring_params = self.prepare_parameters(self.get_parameters(path_spec, openapi.IN_QUERY), force_params)
            endpoint_path += "&{}".format(urlencode(querystring_params))
        return endpoint_path

    def get_parameters(self, path_spec, part):
        """
        :param path_spec: OpenAPI spec fot the path.
        :param part: Part of the request (body, query, etc).
        :return: The OpenAPI parameters of the path for the given part of the request.
        """
        return [param for param in path_spec['parameters'] if param.get('in') == part]

    def prepare_parameters(self, parameter, force_params=None):
        """
        :param parameter: Parameter list for generate.
        :param force_params: Overrides the default parameters with new ones.
        :return: Parameters for making the request.
        """
        return force_params if force_params else self.get_default_data()

    def get_body_parameters(self, path_spec, force_params):
        return self.prepare_parameters(self.get_parameters(path_spec, openapi.IN_BODY), force_params)

    def get_default_data(self):
        """
        :return: Default request data.
        """
        return {}

    @classmethod
    def spec(cls):
        if not getattr(cls, 'cached_spec'):
            setattr(cls, 'cached_spec', cls().get_open_api())
        return cls.cached_spec

    def get_open_api(self):
        """
        :return: Fetches the OpenAPI spec as dict.
        """
        url = reverse(self.open_api_url_name) + '?format=openapi'
        response = self.client.get(url, format='json')
        return json.loads(response.content)

    def should_return_response(self, response, path_spec):
        """
        :todo: Validate data with its associated JSON Schema, but for doing so we need a valid way for converting
        between formats.

        try:
            if response_spec.get('schema'):
                validate_obj_dict(response.data, response_spec.get('schema'), self.spec)
        except JSONSchemaValidationError as e:
            pytest.fail(str(e))
        """
        response_spec = path_spec['responses'].get(str(response.status_code))
        assert response_spec, """
        Unexpected response code {}, you should review and update your OpenAPI schema in order to document this
        response code.
        """.format(response.status_code)


class OpenAPIResourceListMixin:
    """
    Mixin with list test operation

    You can configure:
    - paginate_by: if you want to set a greater result, but is better to have a lower value since creating and testing
    with more objects is a performance problem, not a test-case.

    List test operations
    ********************
    - test_list
    - should_return_list
    """

    paginate_by = 10
    model_class = None
    delete_previous_objects = False
    object_tuples = ()
    add_user_id = True
    soft_delete = False

    def list(self, force_params=None):
        """
        Performs the list operation for this CRUD resource.
        :param force_params: Force params for the request.
        :return: Operation result
        """
        return self.operation_test('get', self.path, self.spec()['paths'][self.path]['get'], force_params)

    @pytest.mark.parametrize("object_number", (
            0,
            1,
            paginate_by + 1 if paginate_by else 2
    ))
    def test_list(self, object_number):
        if self.model_class and self.delete_previous_objects:
            # If there are previous objects on data load delete it all to test list
            if self.soft_delete:
                self.model_class.all_objects.all().delete(force_policy=HARD_DELETE)
            else:
                self.model_class.objects.all().delete()

        if self.model_class and object_number > 1 and self.object_tuples:
            # If we have to create N objects and the ids are setted by default,
            # mommy can override the objects using the same id more than one time
            object_number = self.paginate_by
            [self.given_a_tupled_object(object_id) for object_id, _ in self.object_tuples[:object_number]]
        else:
            [self.given_an_object() for _ in range(0, object_number)]
        response = self.list(force_params={'page_size': self.paginate_by})
        assert response.status_code == HTTP_200_OK
        self.should_return_list(object_number, self.paginate_by, response)

    def should_return_list(self, expected, paginate_by, response):
        """
        Tests if the response result id a list result, taking pagination in account.
        :param expected: Total objects created.
        :param paginate_by: Items per page
        :param response: Response being checked
        """
        if paginate_by:
            assert response.data['count'] == expected
            assert len(response.data['results']) <= paginate_by
        else:
            assert len(response.data) == expected

    def given_a_tupled_object(self, object_id):
        if not self.add_user_id:
            return mommy.make(self.model_class, id=object_id)
        return mommy.make(self.model_class, id=object_id, user_id='2222')


class RemovePermissionCheckerMixin:

    def remove_permission_checker(self):
        if hasattr(self.user, "permission_checker"):
            delattr(self.user, "permission_checker")


class OpenAPIResourceExcelExportMixin(RemovePermissionCheckerMixin, OpenAPIResourceListMixin):

    @pytest.mark.parametrize("object_number", (0, 1, 5))
    def test_excel_export(self, object_number):
        if self.model_class and object_number > 1 and self.object_tuples:
            # If we have to create N objects and the ids are setted by default,
            # mommy can override the objects using the same id more than one time
            object_number = self.paginate_by
            [self.given_a_tupled_object(object_id) for object_id, _ in self.object_tuples[:object_number]]
        else:
            [self.given_an_object() for _ in range(0, object_number)]
        self.add_excel_permission()
        self.add_permission()
        self.client.credentials(**{"HTTP_ACCEPT": "application/xlsx"})
        self.remove_permission_checker()
        response = self.list(force_params={'page_size': self.paginate_by})
        assert response.status_code == HTTP_200_OK

    def add_excel_permission(self):
        if hasattr(self.user, "usergroup"):
            group = self.user.usergroup.group
        else:
            group = mommy.make(Group, user_id="222222", profile_ctrl_user_id="232222")
            self.set_usergroup(group)
        self.set_permission(MASTERS_EXCEL, group)

    def add_permission(self):
        pass

    @pytest.mark.parametrize("has_permissions,expected_response", ((True, HTTP_200_OK), (False, HTTP_403_FORBIDDEN)))
    def test_permissions(self, has_permissions, expected_response):
        object_number = 4
        if self.model_class and object_number > 1 and self.object_tuples:
            # If we have to create N objects and the ids are setted by default,
            # mommy can override the objects using the same id more than one time
            object_number = self.paginate_by
            [self.given_a_tupled_object(object_id) for object_id, _ in self.object_tuples[:object_number]]
        else:
            [self.given_an_object() for _ in range(0, object_number)]
        if has_permissions:
            self.add_excel_permission()
        self.add_permission()
        self.client.credentials(**{"HTTP_ACCEPT": "application/xlsx"})
        self.remove_permission_checker()
        response = self.list(force_params={'page_size': self.paginate_by})
        assert response.status_code == expected_response


class ListUpdateMixin:
    def list_update(self, force_params=None):
        """
        Performs the update bulk operation for this Resource.
        :param force_params: Force params for the request.
        :return: Operation result
        """
        return self.operation_test('post', self.path, self.spec()['paths'][self.path]['post'], force_params)


class DictListGetMixin:

    def dict_list_retrieve(self, force_params=None):
        return self.operation_test('get', self.path, self.spec()['paths'][self.path]['get'], force_params)


class PostOperationMixin:

    def post(self, force_params=None):
        """
        Performs the post operation for this Resource.
        :param force_params: Force params for the request.
        :return: Operation result
        """
        return self.operation_test('post', self.path, self.spec()['paths'][self.path]['post'], force_params)


class OrderUpdateMixin:
    def order_update(self, force_params=None):
        """
        Performs update the order of the element.indicated
        :param force_params: Force params for the request.
        :return: Operation result
        """
        return self.operation_test('post', self.path, self.spec()['paths'][self.path]['post'], force_params)


class UpdatePatchMixin:

    def patch(self, force_params=None):
        """
        Performs the update partial or patch operation based on the OpenAPI spec.
        :param force_params: Force params for the request.
        :return: Operation result
        """
        return self.operation_test('patch', self.detail_path, self.spec()['paths'][self.detail_path]['patch'],
                                   force_params)


class CreateOperationMixin:

    def create(self, force_params=None):
        """
        Performs the create operation for this Resource.
        :param force_params: Force params for the request.
        :return: Operation result
        """
        return self.operation_test('post', self.path, self.spec()['paths'][self.path]['post'], force_params)


class PreparePathIDMixin:
    """
    Mixin to have a prepare path method to add the id to the url
    """

    def prepare_path(self, path, path_spec, force_params=None):
        """
        :param path: Relative URI of the operation.
        :param path_spec: OpenAPI spec as dict for part.
        :param force_params: Explicitly force params.
        :return: Path for performing a request to the given OpenAPI path.
        """
        path = path.format(id=force_params["id"])
        return "{}{}".format(self.base_api_path, path)


class OpenAPIResourceCreateMixin(CreateOperationMixin):
    """
    Basically, creating a test with consists in extending this class and at least override the methods for generating
    the data. These are:
    - get_default_data
    - given_create_rq_data

    Create test
    ***********
    - test_create_valid
    - should_create_object
    - test_create_invalid
    - should_be_invalid
    """

    def test_create_valid(self):
        rq_data = self.given_create_rq_data()
        self.when_is_authenticated()
        response = self.create(rq_data)
        assert response.status_code == status.HTTP_201_CREATED
        self.should_create_object(response, rq_data)

    def test_create_invalid(self):
        rq_data = self.given_create_rq_data()
        self.when_data_is_invalid(rq_data)
        self.when_is_authenticated()
        response = self.create(rq_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        self.should_be_invalid(response, rq_data)

    def given_an_object(self):
        """
        Hook method for creating a resource instance for testing. Each call must generate a new object.
        :return: Resource instance
        """
        resp = self.create(self.get_default_data())
        assert resp.status_code == status.HTTP_201_CREATED
        return resp.data

    def given_create_rq_data(self):
        """
        :return: Returns the data needed for creating an object. By default returns the given_an_object result.
        """
        return self.given_an_object()

    def should_create_object(self, response, rq_data):
        """
        Checks the created object.
        :param response: Response received.
        :param rq_data: RQ data sent for creating the object.
        """
        pass

    def should_be_invalid(self, response, rq_data):
        """
        Tests if a given response is a bad request validation response. You can override this method in order to
        implement custom checks.
        :param response:
        :param rq_data:
        """
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data

    def when_data_is_invalid(self, data):
        raise NotImplementedError('You must implement this method for generating the invalid data test case.')


class RetrieveOperation:

    def retrieve(self, force_params=None):
        """
        Performs the retrieve/read operation based on the OpenAPI spec.
        :param force_params: Force params for the request.
        :return: Operation result
        """
        return self.operation_test('get', self.detail_path, self.spec()['paths'][self.detail_path]['get'],
                                   force_params)


class PutOperation:

    def put(self, force_params=None):
        """
        Performs the complete update operation based on the OpenAPI spec.
        :param force_params: Force params for the request.
        :return: Operation result
        """
        return self.operation_test('put', self.detail_path, self.spec()['paths'][self.detail_path]['put'],
                                   force_params)


class OpenAPIRetrieveMixin(RetrieveOperation):
    """
    Retrieve test
    *************
    - test_retrieve
    - should_retrieve_object
    """
    lookup_field = 'id'
    path_pk_param_name = 'id'

    def test_retrieve(self):
        obj = self.given_an_object()
        try:
            response = self.retrieve(force_params={self.path_pk_param_name: obj[self.lookup_field]})
        except TypeError:
            response = self.retrieve(force_params={self.path_pk_param_name: obj.id})
        assert response.status_code == status.HTTP_200_OK
        self.should_retrieve_object(response, obj)

    def should_retrieve_object(self, response, obj):
        """
        Performs the checks on retrieve response.
        :param response: Response received.
        :param obj: Obj retrieved
        """
        pass


class OpenAPIResoureceDeleteMixin(RetrieveOperation):
    lookup_field = 'id'
    path_pk_param_name = 'id'
    check_retrieve = True

    def test_delete(self):
        obj = self.given_an_object()
        try:
            url_params = {self.path_pk_param_name: obj[self.lookup_field]}
        except TypeError:
            url_params = {self.path_pk_param_name: obj.id}
        response = self.delete(force_params=url_params)
        self.should_delete(response, url_params)

    def delete(self, force_params=None):
        """
        Performs the delete/destroy operation based on the OpenAPI spec.
        :param force_params: Force params for the request.
        :return: Operation result
        """
        return self.operation_test('delete', self.detail_path, self.spec()['paths'][self.detail_path]['delete'],
                                   force_params)

    def should_delete(self, response, url_params):
        """
        Checks if an object has been deleted by testing if the retrieve operation returns a 404.
        :param response: Response of the delete request.
        :param url_params: Params for the retrieve operation
        """
        assert response.status_code == status.HTTP_204_NO_CONTENT
        if self.check_retrieve is True:
            retrieve_response = self.retrieve(force_params=url_params)
            assert retrieve_response.status_code == status.HTTP_404_NOT_FOUND
            self.check_extra_delete_actions(url_params[self.path_pk_param_name])

    def check_extra_delete_actions(self, object_id):
        """
        Chek extra actions on delate, if needed
        :param object_id: Id of the deleted instance
        :return:
        """
        pass


class SoftDeleteCheckMixin:
    deleted_model_class = None

    def check_extra_delete_actions(self, object_id):
        """
        Chek extra actions on delate, if needed
        :param object_id: Id of the deleted instance
        :return:
        """
        if not self.deleted_model_class:
            raise Exception("Set deleted_model param")
        assert self.deleted_model_class.deleted_objects.get(pk=object_id).deleted


class OpenAPIResourceUpdateMixin(UpdatePatchMixin, PutOperation):
    """
    Basically, creating a test with consists in extending this class and at least override the methods for generating
        the data. These are:
        - get_default_data
        - given_create_rq_data

    Complete update (PUT)
    *********************
    _ test_complete_update
    - given_a_complete_update
    - should_complete_update

    Partial update (PATCH)
    **********************
    - given_a_partial_update
    - should_partial_update
    """

    path_pk_param_name = 'id'
    lookup_field = 'id'

    def test_update_put(self):
        obj = self.given_an_object()
        obj.update({self.path_pk_param_name: obj[self.lookup_field]})
        rq_data = self.given_a_complete_update(obj)
        response = self.put(force_params=rq_data)
        assert response.status_code == status.HTTP_200_OK
        self.should_complete_update(response, obj)

    def test_update_patch(self):
        obj = self.given_an_object()
        obj.update({self.path_pk_param_name: obj[self.lookup_field]})
        rq_data = self.given_a_partial_update(obj)
        response = self.patch(force_params=rq_data)
        assert response.status_code == status.HTTP_200_OK
        self.should_partial_update(response, obj)

    def given_a_partial_update(self, obj):
        """
        :param obj: Object that will be updated.
        :return: Dictionary with attrs for creating a partial update on a given obj
        """
        return obj

    def given_a_complete_update(self, obj):
        """
        :param obj: Object that will be updated.
        :return: Dictionary with attrs for creating a partial update on a given obj
        """
        return obj

    def should_partial_update(self, response, rq_data):
        """
        Performs the checks on partial update response.
        :param response: Response received.
        :param rq_data: RQ data for updating the object.
        """
        pass

    def should_complete_update(self, response, rq_data):
        """
        Performs the checks on complete update response.
        :param response: Response received.
        :param rq_data: RQ data for updating the object.
        """
        pass


class BaseOpenAPIResourceTest(OpenAPIResourceListMixin, OpenAPIResourceCreateMixin, OpenAPIRetrieveMixin,
                              OpenAPIResoureceDeleteMixin, OpenAPIResourceUpdateMixin, BaseOpenAPITest):
    """
    Class for testing a RESTFul resource based on its OpenAPI specification. It assumes that any operation specified
    in the OpenAPI spec can be translated to a CRUD operation over the resource.

    We classify the operations in two groups: global operations or detail (per object operations which path includes
    a pk parameter, so the object must exist previously).

    How to use
    ----------
    In order to create your own tests, you must at least:
    - Override the get_default_data method for getting example data. Each call must return a different object, so you
    can rely on one of the habitual tools for python and django testing.
    - Define the path static attribute

    Also, you can configure:
    - path_pk_param_name: if the URL param is named different.
    - paginate_by: if you want to set a greater result, but is better to have a lower value since creating and testing
    with more objects is a performance problem, not a test-case.

    Basically, creating a test with consists in extending this class and at least override the methods for generating
    the data. These are:
    - get_default_data
    - given_create_rq_data

    Optionally, you can customize the update test cases with more representative data.
    - given_a_complete_update
    - given_a_partial_update
    - given_an_object

    You can override any of the hooks methods for implementing custom resource logic and tests.

    List test operations on OpenAPIResoureceListMixin

    Create test operations on OpenAPIResourceCreateMixin

    Retrive test operations on OpenAPIRetrieveMixin

    Update test operations on OpenAPIResourceUpdateMixin

    Delete test operations on OpenAPIResoureceDeleteMixin

    :todo: Improve update operations tests.
    :todo: Generate data dynamically
    :todo: Soft deletes
    :todo: Test for credentials for all operations
    """
    path_pk_param_name = 'id'
    object_pk_not_exists = 0

    @pytest.mark.parametrize('operation', ['get', 'patch', 'put', 'delete'])
    def test_not_exists(self, operation):
        operation_spec = self.spec()['paths'][self.detail_path][operation]
        response = self.operation_test('get', self.detail_path, operation_spec,
                                       force_params={self.path_pk_param_name: self.object_pk_not_exists})
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @property
    def detail_path(self):
        return self.get_detail_path()

    def get_detail_path(self):
        """
        :return: URL for the instance/object RESTFul calls.
        """
        return '{}{{{}}}/'.format(self.path, self.path_pk_param_name)

    def get_paths(self):
        """
        :return: OpenAPI path specs for this test.
        """
        return self.PATHS


class BaseOpenAPICRUResourceTest(BaseOpenAPIResourceTest):

    def test_delete(self):
        pass

    @pytest.mark.parametrize('operation', ['get', 'patch', 'put'])
    def test_not_exists(self, operation):
        operation_spec = self.spec()['paths'][self.detail_path][operation]
        response = self.operation_test('get', self.detail_path, operation_spec,
                                       force_params={self.path_pk_param_name: 0})
        assert response.status_code == status.HTTP_404_NOT_FOUND


class BasePermissionsTest(OpenAPIResoureceDeleteMixin, BaseOpenAPITest):
    cases = []
    detail_path = None

    def test_delete(self):
        for case in self.cases:
            self.detail_path = case['detail_path']
            obj = self.given_an_object(case['model_class'])
            url_params = {self.path_pk_param_name: getattr(obj, self.path_pk_param_name)}
            response = self.delete(force_params=url_params)
            assert response.status_code == HTTP_403_FORBIDDEN

    def test_delete_allowed(self):
        self.set_admin_permission()
        for case in self.cases:
            self.detail_path = case['detail_path']
            obj = self.given_an_object(case['model_class'])
            url_params = {self.path_pk_param_name: getattr(obj, self.path_pk_param_name)}
            response = self.delete(force_params=url_params)
            assert response.status_code == HTTP_204_NO_CONTENT

    def given_an_object(self, model_class):
        raise NotImplementedError

    def set_admin_permission(self):
        raise NotImplementedError
