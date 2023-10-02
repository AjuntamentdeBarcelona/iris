import uuid

from model_mommy import mommy
from rest_framework.status import HTTP_200_OK

from features.models import ValuesType, Mask, Values, Feature
from features.serializers import ValuesTypeSerializer
from main.test.mixins import AdminUserMixin
from main.open_api.tests.base import BaseOpenAPIResourceTest,  OpenAPIResourceListMixin, BaseOpenAPITest
from record_cards.tests.utils import SetPermissionMixin, SetUserGroupMixin


class TestValuesType(SetUserGroupMixin, SetPermissionMixin, AdminUserMixin, BaseOpenAPIResourceTest):
    path = "/features/values_types/"
    base_api_path = "/services/iris/api"

    def get_default_data(self):
        return {
            "description": uuid.uuid4(),
            "description_gl": uuid.uuid4(),
            "description_es": uuid.uuid4(),
            "description_en": uuid.uuid4(),
            "values": [{"description": uuid.uuid4(),
                        "description_gl": uuid.uuid4(),
                        "description_es": uuid.uuid4(),
                        "description_en": uuid.uuid4()}]
        }

    def given_create_rq_data(self):
        return {
            "description": uuid.uuid4(),
            "description_gl": uuid.uuid4(),
            "description_en": uuid.uuid4(),
            "description_es": uuid.uuid4(),
            "values": [{"description": uuid.uuid4(),
                        "description_gl": uuid.uuid4(),
                        "description_es": uuid.uuid4(),
                        "description_en": uuid.uuid4()}]
        }

    def given_a_partial_update(self, obj):
        """
        :param obj: Object that will be updated.
        :return: Dictionary with attrs for creating a partial update on a given obj
        """
        return self.values_type_update(obj)

    def given_a_complete_update(self, obj):
        """
        :param obj: Object that will be updated.
        :return: Dictionary with attrs for creating a partial update on a given obj
        """
        return self.values_type_update(obj)

    @staticmethod
    def values_type_update(obj):
        obj["values"][0]["description"] = uuid.uuid4()
        return obj

    def when_data_is_invalid(self, data):
        data["description_es"] = ''

    def test_values_delete(self):
        values_type = ValuesType.objects.create(description="test", description_es="test", description_gl="test",
                                                description_en="test")
        for _ in range(3):
            Values.objects.create(description=uuid.uuid4(), description_gl=uuid.uuid4(), description_es=uuid.uuid4(),
                                  description_en=uuid.uuid4(), values_type=values_type)
        rq_data = ValuesTypeSerializer(instance=values_type).data
        rq_data["values"] = [{"description": uuid.uuid4(), "description_gl": uuid.uuid4(),
                              "description_es": uuid.uuid4(), "description_en": uuid.uuid4()}]
        response = self.put(force_params=rq_data)
        assert response.status_code == HTTP_200_OK
        values_type = ValuesType.objects.get(id=values_type.pk)
        assert values_type.values_set.filter(deleted__isnull=True).count() == 1

    def test_value_update_descriptions(self):
        values_type = ValuesType.objects.create(description="test", description_es="test", description_gl="test",
                                                description_en="test")
        value = Values.objects.create(description=uuid.uuid4(), description_gl=uuid.uuid4(),
                                      description_es=uuid.uuid4(),
                                      description_en=uuid.uuid4(), values_type=values_type)
        rq_data = ValuesTypeSerializer(instance=values_type).data
        rq_data["values"][0]["description_gl"] = "test"

        response = self.put(force_params=rq_data)
        assert response.status_code == HTTP_200_OK
        assert response.json()["values"][0]["description_gl"] == "test"
        values_type = ValuesType.objects.get(id=values_type.pk)
        assert values_type.values_set.filter(deleted__isnull=True).count() == 1
        assert Values.all_objects.get(pk=value.pk, deleted__isnull=False)


class TestFeature(SetUserGroupMixin, SetPermissionMixin, AdminUserMixin, BaseOpenAPIResourceTest):
    path = "/features/features/"
    base_api_path = "/services/iris/api"
    model_class = Feature
    delete_previous_objects = True

    def get_default_data(self):
        return {
            "values_type_id": mommy.make(ValuesType, user_id="222").pk,
            "description": uuid.uuid4(),
            "description_gl": uuid.uuid4(),
            "description_es": uuid.uuid4(),
            "description_en": uuid.uuid4(),
            "explanatory_text": uuid.uuid4(),
            "explanatory_text_es": None,
            "explanatory_text_gl": None,
            "explanatory_text_en": None
        }

    def given_create_rq_data(self):
        return {
            "mask_id": mommy.make(Mask, id=Mask.ANY_CHAR).pk,
            "description": uuid.uuid4(),
            "description_gl": uuid.uuid4(),
            "description_en": uuid.uuid4(),
            "description_es": uuid.uuid4(),
            "explanatory_text": uuid.uuid4(),
            "explanatory_text_gl": uuid.uuid4(),
            "explanatory_text_es": uuid.uuid4(),
            "explanatory_text_en": uuid.uuid4()
        }

    def when_data_is_invalid(self, data):
        data["description_es"] = ''

    def given_a_partial_update(self, obj):
        """
        :param obj: Object that will be updated.
        :return: Dictionary with attrs for creating a partial update on a given obj
        """
        obj.pop("mask_id", None)
        return obj

    def given_a_complete_update(self, obj):
        """
        :param obj: Object that will be updated.
        :return: Dictionary with attrs for creating a partial update on a given obj
        """
        obj.pop("mask_id", None)
        obj.pop("explanatory_text", None)
        obj.pop("explanatory_text_gl", None)
        obj.pop("explanatory_text_es", None)
        obj.pop("explanatory_text_en", None)
        return obj


class TestMaskList(OpenAPIResourceListMixin, BaseOpenAPITest):
    path = "/features/masks/"
    base_api_path = "/services/iris/api"

    paginate_by = 8
    model_class = Mask
    delete_previous_objects = True
    object_tuples = Mask.MASKS
    add_user_id = False
    soft_delete = False

    def given_an_object(self):
        return Mask.objects.create(id=Mask.INTEGER, type=Mask.NUMBER, description="description")
