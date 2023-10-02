import pytest
from model_mommy import mommy

from iris_masters.models import ResponseType, RecordType
from iris_templates.models import IrisTemplate, IrisTemplateRecordTypes
from main.test.mixins import FieldsTestSerializerMixin
from themes.tests.test_serializers import UniqueValidityTest
from iris_templates.serializers import IrisTemplateSerializer, IrisTemplateShortSerializer


@pytest.mark.django_db
class TestIrisTemplateSerializer(UniqueValidityTest):
    serializer_class = IrisTemplateSerializer

    def given_fields(self):
        return ["description"]

    def get_extra_data(self):
        return {
            "write_medium_catalan": "test",
            "write_medium_spanish": "test",
            "sms_medium_catalan": "test",
            "sms_medium_spanish": "test",
            "response_type_id": mommy.make(ResponseType, user_id="22222222").pk
        }

    @pytest.mark.parametrize("description,add_response_type_id,valid", (
            ("test", True, True),
            ("", True, False),
            ("test", False, False)
    ))
    def test_iris_template_serializer(self, description, add_response_type_id, valid):
        data = {
            "description": description,
            "write_medium_catalan": "test",
            "write_medium_spanish": "test",
            "sms_medium_catalan": "test",
            "sms_medium_spanish": "test",
        }
        if add_response_type_id:
            data["response_type_id"] = mommy.make(ResponseType, user_id="22222222").pk

        ser = IrisTemplateSerializer(data=data)
        assert ser.is_valid() is valid, "IrisTemplate Serializer fails"
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize("write_medium_catalan,write_medium_spanish,sms_medium_catalan,sms_medium_spanish,valid", (
            ("test", "test", "test", "test", True),
            ("", "test", "test", "test", False),
            ("test", None, "test", "test", False),
            ("test", "test", None, "test", False),
            ("test", "test", "test", "", False),
    ))
    def test_serializer_write_mediums(self, write_medium_catalan, write_medium_spanish, sms_medium_catalan,
                                      sms_medium_spanish, valid):
        data = {
            "description": "description",
            "response_type_id": mommy.make(ResponseType, user_id="22222222").pk,
            "write_medium_catalan": write_medium_catalan,
            "write_medium_spanish": write_medium_spanish,
            "sms_medium_catalan": sms_medium_catalan,
            "sms_medium_spanish": sms_medium_spanish,
        }

        ser = IrisTemplateSerializer(data=data)
        assert ser.is_valid() is valid, "IrisTemplate Serializer fails"
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize("same_response_type,same_record_type,valid", (
            (False, False, True),
            (False, True, True),
            (True, False, True),
            (True, True, False),
    ))
    def test_iris_templates_record_types(self, same_response_type, same_record_type, valid):

        response_type_pk = mommy.make(ResponseType, user_id="2222222").pk
        if same_response_type:
            previous_response_type_pk = response_type_pk
        else:
            previous_response_type_pk = mommy.make(ResponseType, user_id="2222222").pk

        record_type_pk = mommy.make(RecordType, user_id="2222222").pk
        if same_record_type:
            previous_record_type_pk = record_type_pk
        else:
            previous_record_type_pk = mommy.make(RecordType, user_id="2222222").pk

        previos_template = mommy.make(IrisTemplate, user_id="asdadsa", response_type_id=previous_response_type_pk)
        IrisTemplateRecordTypes.objects.create(iris_template_id=previos_template.pk,
                                               record_type_id=previous_record_type_pk)

        data = {
            "description": "test",
            "write_medium_catalan": "test",
            "write_medium_spanish": "test",
            "sms_medium_catalan": "test",
            "sms_medium_spanish": "test",
            "response_type_id": response_type_pk,
            "record_types": [{"record_type": record_type_pk}]
        }
        ser = IrisTemplateSerializer(data=data)
        assert ser.is_valid() is valid, "IrisTemplate Serializer fails"
        assert isinstance(ser.errors, dict)
        if valid is True:
            template = ser.save()
            assert IrisTemplateRecordTypes.objects.get(iris_template_id=template.id, record_type_id=record_type_pk)


@pytest.mark.django_db
class TestIrisTemplateShortSerializer(FieldsTestSerializerMixin):
    serializer_class = IrisTemplateShortSerializer
    data_keys = ["id", "user_id", "created_at", "updated_at", "description", "response_type", "write_medium_catalan",
                 "write_medium_spanish", "sms_medium_catalan", "sms_medium_spanish"]

    def get_instance(self):
        response_type = mommy.make(ResponseType, user_id="222")
        return mommy.make(IrisTemplate, user_id="2222", response_type=response_type)
