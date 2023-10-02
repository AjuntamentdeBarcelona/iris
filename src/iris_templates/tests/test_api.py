import uuid

import pytest
from model_mommy import mommy
from rest_framework.status import HTTP_201_CREATED, HTTP_200_OK

from iris_masters.models import ResponseType, RecordType
from iris_templates.models import IrisTemplate, IrisTemplateRecordTypes
from main.open_api.tests.base import (SoftDeleteCheckMixin, BaseOpenAPIResourceTest, BaseOpenAPITest,
                                      OpenAPIResourceListMixin, DictListGetMixin)


class TestIrisTemplate(SoftDeleteCheckMixin, BaseOpenAPIResourceTest):
    path = "/templates/templates/"
    base_api_path = "/services/iris/api"
    deleted_model_class = IrisTemplate

    def get_default_data(self):
        return {
            "description": uuid.uuid4(),
            "write_medium_catalan": uuid.uuid4(),
            "write_medium_spanish": uuid.uuid4(),
            "sms_medium_catalan": uuid.uuid4(),
            "sms_medium_spanish": uuid.uuid4(),
            "response_type_id": mommy.make(ResponseType, user_id="22222222").pk
        }

    def given_create_rq_data(self):
        return {
            "description": uuid.uuid4(),
            "write_medium_catalan": uuid.uuid4(),
            "write_medium_spanish": uuid.uuid4(),
            "sms_medium_catalan": uuid.uuid4(),
            "sms_medium_spanish": uuid.uuid4(),
            "response_type_id": mommy.make(ResponseType, user_id="22222222").pk
        }

    def when_data_is_invalid(self, data):
        data.pop("write_medium_catalan", None)
        data.pop("sms_medium_spanish", None)

    def test_record_types_valid(self):
        rq_data = self.given_create_rq_data()
        record_type_pk = mommy.make(RecordType, user_id="2222222").pk
        rq_data["record_types"] = [{"record_type": record_type_pk}]
        self.when_is_authenticated()
        response = self.create(rq_data)
        assert response.status_code == HTTP_201_CREATED
        self.should_create_object(response, rq_data)
        assert IrisTemplateRecordTypes.objects.get(iris_template_id=response.json()["id"],
                                                   record_type_id=record_type_pk)


class TestResponseType(SoftDeleteCheckMixin, BaseOpenAPIResourceTest):
    path = "/templates/response_types/"
    base_api_path = "/services/iris/api"
    deleted_model_class = ResponseType

    def get_default_data(self):
        return {
            "description": uuid.uuid4()
        }

    def given_create_rq_data(self):
        return {
            "description": uuid.uuid4()
        }

    def when_data_is_invalid(self, data):
        data["description"] = None


class TestRecordTypeTemplatesListView(OpenAPIResourceListMixin, BaseOpenAPITest):
    path = "/templates/record_type/{id}/templates/"
    base_api_path = "/services/iris/api"

    @pytest.mark.parametrize("object_number", (0, 1, 3))
    def test_list(self, object_number):
        record_type = mommy.make(RecordType, user_id="222222")
        [self.given_an_object(record_type) for _ in range(0, object_number)]
        response = self.list(force_params={"page_size": self.paginate_by, "id": record_type.pk})
        self.should_return_list(object_number, self.paginate_by, response)

    def given_an_object(self, record_type):
        """
        Hook method for creating a resource instance for testing. Each call must generate a new object.
        :return: Resource instance
        """
        response_type = mommy.make(ResponseType, user_id="222")
        iris_template = mommy.make(IrisTemplate, user_id="2222", response_type=response_type)
        IrisTemplateRecordTypes.objects.create(iris_template=iris_template, record_type=record_type)


class TestVariablesList(DictListGetMixin, BaseOpenAPITest):
    path = "/templates/variables/"
    base_api_path = "/services/iris/api"

    def test_variables_list(self):
        variables = ["DIES_RESPOSTA_CI", "DIES_PER_RECLAMAR", "DIES_ANTIGUITAT_RESPOSTA", "PERFIL_DERIVACIO_ALCALDIA",
                     "codi_fitxa", "departament_fitxa", "nombre_reclamacions"]
        response = self.dict_list_retrieve()
        assert response.status_code == HTTP_200_OK
        api_variables = [var["name"] for var in response.json()]
        for var in variables:
            assert var.lower() in api_variables
