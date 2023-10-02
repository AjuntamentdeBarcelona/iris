import uuid

import pytest
from model_mommy import mommy

from features.models import ValuesType, Mask
from main.test.mixins import FieldsTestSerializerMixin
from themes.tests.test_serializers import UniqueValidityTest

from features.serializers import (ValuesTypeSerializer, ValuesSerializer, FeatureSerializer, ValuesTypeShortSerializer,
                                  MaskSerializer)


class TestValuesTypeSerializer(UniqueValidityTest):
    serializer_class = ValuesTypeSerializer
    unique_field = "description"

    def get_extra_data(self):
        return {
            "values": [{"description": str(uuid.uuid4()), "description_gl": str(uuid.uuid4()),
                        "description_es": str(uuid.uuid4()), "description_en": str(uuid.uuid4())}]
        }

    @pytest.mark.parametrize("add_random_value, add_same_value, valid", (
            (True, False, True),
            (True, True, False),
            (False, False, True),
            (False, True, False),
    ))
    def test_values_descriptions(self, add_random_value, add_same_value, valid):

        data = {
            "description_gl": str(uuid.uuid4()),
            "description_es": str(uuid.uuid4()),
            "description_en": str(uuid.uuid4()),
            "values": [{
                "description_gl": "test",
                "description_es": "test",
                "description_en": "test",
                "order": 3
            }]
        }

        if add_random_value:
            data["values"].append({"description_gl": str(uuid.uuid4()), "description_es": str(uuid.uuid4()),
                                   "description_en": str(uuid.uuid4()), "order": 5})
        if add_same_value:
            data["values"].append({"description_gl": "test", "description_es": "test",
                                   "description_en": "test", "order": 3})

        ser = ValuesTypeSerializer(data=data)
        assert ser.is_valid() is valid
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestValuesTypeShortSerializer(FieldsTestSerializerMixin):
    serializer_class = ValuesTypeShortSerializer
    data_keys = ["id", "description", "description_es", "description_gl", "description_en", "can_delete"]

    def get_instance(self):
        return mommy.make(ValuesType, user_id="22222")


class TestValuesSerializer:
    @pytest.mark.parametrize("description_gl,description_es,description_en,order,valid", (
            ("test", "test", "test", 3, True),
            ("", "test", "test", 4, False),
            ("test", "", "test", 5, False),
            ("test", "test", "", 6, False),
            ("test", "test", "test", None, False),
    ))
    def test_values_serializer(self, description_gl, description_es, description_en, order, valid):
        data = {
            "description_gl": description_gl,
            "description_es": description_es,
            "description_en": description_en,
            "order": order,
        }
        ser = ValuesSerializer(data=data)
        assert ser.is_valid() is valid, "Values serializer fails"
        assert isinstance(ser.errors, dict)


class TestFeatureSerializer(UniqueValidityTest):
    serializer_class = FeatureSerializer
    unique_field = "description"

    def get_extra_data(self):
        return {
            "values_type_id": mommy.make(ValuesType, user_id="222").pk,
            "explanatory_text": "test",
            "explanatory_text_gl": "test",
            "explanatory_text_es": "test",
            "explanatory_text_en": "test"
        }

    @pytest.mark.parametrize("add_values_type,add_mask,add_explanatory,valid", (
            (True, True, True, False),
            (True, True, False, False),
            (True, False, True, True),
            (True, False, False, True),
            (False, True, True, True),
            (False, True, False, True),
            (False, False, True, False),
            (False, False, False, False),
    ))
    def test_mask_values_type(self, add_values_type, add_mask, add_explanatory, valid):
        feature_data = {
            "description": "test",
            "description_gl": "test",
            "description_es": "test",
            "description_en": "test",
        }
        if add_explanatory:
            feature_data["explanatory_text"] = "test"
            feature_data["explanatory_text_gl"] = "test"
            feature_data["explanatory_text_es"] = "test"
            feature_data["explanatory_text_en"] = "test"

        if add_values_type:
            feature_data["values_type_id"] = mommy.make(ValuesType, user_id="222").pk
        if add_mask:
            feature_data["mask_id"] = mommy.make(Mask, id=Mask.ANY_CHAR).pk

        ser = FeatureSerializer(data=feature_data)
        assert ser.is_valid() is valid
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestMaskSerializer(FieldsTestSerializerMixin):
    serializer_class = MaskSerializer
    data_keys = ["id", "description", "description_gl", "description_es", "description_en"]

    def get_instance(self):
        pk = Mask.INTEGER
        if not Mask.objects.filter(pk=pk):
            mask = Mask(pk=pk)
            mask.save()
            return mask
        else:
            return Mask.objects.get(pk=Mask.INTEGER)
