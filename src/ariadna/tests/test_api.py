import pytest
from model_mommy import mommy
from rest_framework import status

from ariadna.models import Ariadna
from ariadna.serializers import AriadnaSerializer
from main.open_api.tests.base import (BaseOpenAPITest, OpenAPIResourceCreateMixin, OpenAPIResourceListMixin,
                                      OpenAPIRetrieveMixin)


@pytest.mark.django_db
class TestAriadna(OpenAPIResourceListMixin, OpenAPIResourceCreateMixin, BaseOpenAPITest):
    path = "/ariadna/"
    base_api_path = "/services/iris/api"

    def given_an_object(self):
        return mommy.make(Ariadna, user_id="2222")

    def given_create_rq_data(self):
        """
        :return: Returns the data needed for creating an object. By default returns the given_an_object result.
        """
        return {
            "year": 2019,
            "input_number": 1456,
            "input_office": "aaaaaaaaaa",
            "destination_office": "aaaaaaaaaa",
            "presentation_date": "2019-07-11",
            "applicant_type": "P",
            "applicant_surnames": "aaaaaaaaaaaaa",
            "applicant_name": "test test",
            "applicant_doc": "aaaaaaaaaa",
            "matter_type": "aaaaaaaaaa",
            "issue": "aaaaaaaaaa",
            "used": False,
            "date_us": "2019-07-11T11:50:54+02:00"

        }

    def when_data_is_invalid(self, data):
        data["year"] = None
        return data


class TestAriadnaRetrieve(OpenAPIRetrieveMixin, BaseOpenAPITest):

    detail_path = "/ariadna/{year}/{input_number}/"
    base_api_path = "/services/iris/api"
    lookup_field = "code"
    path_pk_param_name = "code"

    def test_retrieve(self):
        obj = self.given_an_object()
        response = self.retrieve(force_params={"year": obj["year"], "input_number": obj["input_number"]})
        assert response.status_code == status.HTTP_200_OK
        self.should_retrieve_object(response, obj)

    def given_an_object(self):
        ariadna = mommy.make(Ariadna, user_id="2222", year=2010, input_number=334554)
        return AriadnaSerializer(instance=ariadna).data
