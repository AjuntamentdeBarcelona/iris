from datetime import timedelta

import pytest
from django.utils import timezone

from model_mommy import mommy

from iris_masters.models import (Parameter, Support, ApplicantType, Process, RecordState, District, MediaType,
                                 RecordType, LetterTemplate, InputChannel)
from iris_masters.serializers import (ParameterSerializer, InputChannelSupportSerializer, ResolutionTypeSerializer,
                                      InputChannelApplicantTypeSerializer, InputChannelSerializer, DistrictSerializer,
                                      ResponseChannelSupportSerializer, SupportSerializer, ProcessSerializer,
                                      CommunicationMediaSerializer, AnnouncementSerializer, RecordTypeSerializer,
                                      ResponseTypeSerializer, CancelReasonSerializer, ReassignationReasonSerializer,
                                      ShortRecordTypeSerializer, RecordStateSerializer, ResponseTypeShortSerializer,
                                      LetterTemplateSerializer, ApplicantTypeSerializer, InputChannelShortSerializer)
from main.test.mixins import FieldsTestSerializerMixin
from themes.tests.test_serializers import UniqueValidityTest
from communications.tests.utils import load_missing_data
from iris_masters.tests.utils import load_missing_data_applicant, load_missing_data_process, load_missing_data_districts


@pytest.mark.django_db
class TestParameterSerializer:

    @pytest.mark.parametrize("old_valor,new_valor,show,valid", (
            ("Valor", "Valor 1", True, True),
            ("Valor", "Valor 2", False, True),
    ))
    def test_parameter_serializer(self, old_valor, new_valor, show, valid):
        error_message = "Paramenter serializer fails"
        param = mommy.make(Parameter, valor=old_valor, show=show, user_id="222")
        ser = ParameterSerializer(data={"id": param.id, "valor": new_valor})
        assert valid is ser.is_valid(), error_message
        assert isinstance(ser.errors, dict)
        parameter = ser.save()
        if parameter:
            assert parameter.valor == new_valor, error_message
        else:
            parameter = Parameter.objects.get(pk=param.pk)
            assert parameter.valor == old_valor, error_message


@pytest.mark.django_db
class TestRecordTypeSerializer(UniqueValidityTest):
    serializer_class = RecordTypeSerializer

    def get_extra_data(self):
        return {"tri": 5, "trt": 12}

    @pytest.mark.parametrize("description,tri,trt,valid", (
            ("Description test", 0, 10, True),
            ("", 0, 10, False),
            ("Description test", None, 10, False),
            ("Description test", 0, None, False),
    ))
    def test_record_type_serializer(self, description, tri, trt, valid):
        ser = RecordTypeSerializer(data={"description_es": description, "description_gl": description,
                                         "description_en": description, "tri": tri, "trt": trt})
        assert ser.is_valid() is valid
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestShortRecordTypeSerializer(FieldsTestSerializerMixin):
    serializer_class = ShortRecordTypeSerializer
    data_keys = ["id", "user_id", "created_at", "updated_at", "description", "description_es", "description_gl",
                 "description_en", "tri", "trt", "can_delete"]

    def get_instance(self):
        return mommy.make(RecordType, user_id="2222")


@pytest.mark.django_db
class TestRecordStateSerializer:

    @pytest.mark.parametrize("record_state_id", (RecordState.PENDING_VALIDATE, RecordState.CANCELLED))
    def test_process_serializer(self, record_state_id):
        load_missing_data()
        ser = RecordStateSerializer(instance=RecordState.objects.get(id=record_state_id))
        assert int(ser.data["id"]) == record_state_id, "RecordState Serializer fails"
        assert "acronym" in ser.data


@pytest.mark.django_db
class TestInputChannelSupportSerializer:

    @pytest.mark.parametrize("support,order,valid", (
            (1, 1, True),
            (2, 2, True),
            (3, None, False),
            (None, False, False)
    ))
    def test_input_channel_suport_serializer(self, support, order, valid):
        data = {"order": order}
        if support:
            data["support"] = mommy.make(Support, user_id="2222").pk
        ser = InputChannelSupportSerializer(data=data)
        assert valid is ser.is_valid(), "InputChannel Support serializer fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestInputChannelApplicantTypeSerializer:

    @pytest.mark.parametrize("applicant_type,order,valid", (
            (ApplicantType.CIUTADA, 1, True),
            (ApplicantType.COLECTIUS, 2, True),
            (ApplicantType.COLECTIUS, None, False),
            (None, False, False)
    ))
    def test_input_channel_suport_serializer(self, applicant_type, order, valid):
        load_missing_data()
        load_missing_data_applicant()
        ser = InputChannelApplicantTypeSerializer(data={"applicant_type": applicant_type, "order": order})
        assert valid is ser.is_valid(), "InputChannel Applicant Type serializer fails"
        assert isinstance(ser.errors, dict)


class NoTranslatableDescriptionMixin:
    def given_fields(self):
        return ["description"]


class TestInputChannelSerializer(NoTranslatableDescriptionMixin, UniqueValidityTest):
    serializer_class = InputChannelSerializer

    @pytest.mark.parametrize("support", (5, 6, 7))
    def test_supports_input_channel(self, support):
        fields = self.given_fields()
        description = "aaaaa"
        data = {field: description for field in fields}
        mommy.make(Support, user_id="222", pk=support)
        data.update({"supports": [{"support": support, "order": support, "description": "new_description"}]})
        ser = self.given_a_serializer(data=data)
        assert ser.is_valid(), "Input Channel Serializer fails with supports"
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize("applicant_type", (ApplicantType.CIUTADA, ApplicantType.COLECTIUS))
    def test_applicant_type_input_channel(self, applicant_type):
        load_missing_data_applicant()
        fields = self.given_fields()
        description = "aaaa"
        data = {field: description for field in fields}
        data.update({"applicant_types": [{"applicant_type": applicant_type, "order": applicant_type,
                                          "description": "new_description"}]})
        ser = self.given_a_serializer(data=data)
        assert ser.is_valid(), "Input Channel Serializer fails with applicant type"
        assert isinstance(ser.errors, dict)

    def get_extra_data(self):
        return {"can_be_mayorship": False}


@pytest.mark.django_db
class TestInputChannelShortSerializer(FieldsTestSerializerMixin):
    serializer_class = InputChannelShortSerializer
    data_keys = ["id", "user_id", "created_at", "updated_at", "description", "order", "can_delete"]

    def get_instance(self):
        return mommy.make(InputChannel, user_id="2222")


@pytest.mark.django_db
class TestResponseChannelSupportSerializer:

    @pytest.mark.parametrize("response_channel,valid", (
            (1, True),
            (None, False)
    ))
    def test_response_channel_suport_serializer(self, response_channel, valid):
        load_missing_data()
        ser = ResponseChannelSupportSerializer(data={"response_channel": response_channel})
        assert valid is ser.is_valid(), "ResponseChannel Support serializer fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestSupportSerializer(NoTranslatableDescriptionMixin, UniqueValidityTest):
    serializer_class = SupportSerializer

    @pytest.mark.parametrize("response_channel,valid", ((0, True), (10, False)))
    def test_response_channel_support(self, response_channel, valid):
        load_missing_data()
        fields = self.given_fields()
        description = "aaaa"
        data = {field: description for field in fields}
        data.update({"response_channels": [{"response_channel": response_channel}]})
        ser = self.given_a_serializer(data=data)
        assert ser.is_valid() is valid, "Support Serializer fails with response channel"
        assert isinstance(ser.errors, dict)

    def get_extra_data(self):
        return {
            "communication_media_required": True,
            "register_required": False
        }


@pytest.mark.django_db
class TestProcessSerializer:

    @pytest.mark.parametrize("process_id", (Process.CLOSED_DIRECTLY, Process.EXTERNAL_PROCESSING))
    def test_process_serializer(self, process_id):
        load_missing_data_process()
        ser = ProcessSerializer(instance=Process.objects.get(id=process_id))
        assert ser.data["id"] == process_id, "Process Serializer fails"


@pytest.mark.django_db
class TestDistrictSerializer:

    @pytest.mark.parametrize("district_id,district_name,valid", (
            (1, "District 1", True),
            (1, "", False),
            (10, "District 10", True)
    ))
    def test_district_serializer(self, district_id, district_name, valid):
        load_missing_data_districts()
        ser = DistrictSerializer(instance=District.objects.get(id=district_id),
                                 data={"id": district_id, "name": district_name})
        assert ser.is_valid() is valid, "District Serializer fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestCancelReasonSerializer(NoTranslatableDescriptionMixin, UniqueValidityTest):
    serializer_class = CancelReasonSerializer

    def get_extra_data(self):
        return {"reason_type": "1"}


@pytest.mark.django_db
class TestReassignationReasonSerializer(NoTranslatableDescriptionMixin, UniqueValidityTest):
    serializer_class = ReassignationReasonSerializer

    def get_extra_data(self):
        return {"reason_type": "2"}


@pytest.mark.django_db
class TestResponseTypeSerializer(NoTranslatableDescriptionMixin, UniqueValidityTest):
    serializer_class = ResponseTypeSerializer


@pytest.mark.django_db
class TestApplicantTypeSerializer(NoTranslatableDescriptionMixin, UniqueValidityTest):
    serializer_class = ApplicantTypeSerializer

    def get_extra_data(self):
        return {"order": 3, "send_response": False}


@pytest.mark.django_db
class TestResponseTypeShortSerializer(NoTranslatableDescriptionMixin, UniqueValidityTest):
    serializer_class = ResponseTypeShortSerializer


@pytest.mark.django_db
class TestResolutionTypeSerializer(NoTranslatableDescriptionMixin, UniqueValidityTest):
    serializer_class = ResolutionTypeSerializer

    @pytest.mark.parametrize("description,enabled,order,can_claim_inside_ans,valid", (
            ("Test test", True, 1, True, True),
            ("", True, 1, True, False),
            ("Test test", False, 1, False, True),
            ("Test test", True, None, True, False),
    ))
    def test_resolution_type_serializer(self, description, enabled, order, can_claim_inside_ans, valid):
        ser = ResolutionTypeSerializer(data={"description": description, "enabled": enabled, "order": order,
                                             "can_claim_inside_ans": can_claim_inside_ans})
        assert ser.is_valid() is valid, "ResolutionType Serializer fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestCommunicationMediaSerializer(NoTranslatableDescriptionMixin, UniqueValidityTest):
    serializer_class = CommunicationMediaSerializer

    def get_extra_data(self):
        return {"media_type_id": mommy.make(MediaType, user_id="22222").pk}

    @pytest.mark.parametrize("description,media_type,valid", (
            ("Test test", 1, True),
            ("", 1, False),
            ("Test test", None, False),
            ("", None, False),
    ))
    def test_resolution_type_serializer(self, description, media_type, valid):
        if media_type:
            mommy.make(MediaType, pk=media_type, user_id="22222")
        ser = CommunicationMediaSerializer(data={"description": description, "media_type_id": media_type})
        assert ser.is_valid() is valid, "CommunicationMedia Serializer fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestAnnouncementSerializer:

    @pytest.mark.parametrize("title,description,expiration_date,important,xaloc,valid", (
            ("title", "Test test", timezone.now() + timedelta(days=365), True, True, True),
            ("", "Test test", timezone.now() + timedelta(days=365), True, True, False),
            ("title", "", timezone.now() + timedelta(days=365), True, True, False),
            ("title", "Test test", None, True, True, True),
            ("title", "Test test", timezone.now() + timedelta(days=365), False, True, True),
            ("title", "Test test", timezone.now() + timedelta(days=365), True, False, True),
            ("title", "Test test", timezone.now() + timedelta(days=365), True, True, True),
    ))
    def test_announcement_serializer(self, title, description, expiration_date, important, xaloc, valid):
        data = {
            "title": title,
            "description": description,
            "expiration_date": expiration_date,
            "important": important,
            "xaloc": xaloc,
        }
        ser = AnnouncementSerializer(data=data)
        assert ser.is_valid() is valid, "AnnouncementSerializer Serializer fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestLetterTemplateSerializer(FieldsTestSerializerMixin):
    serializer_class = LetterTemplateSerializer
    data_keys = ["id", "user_id", "created_at", "updated_at", "description", "name", "enabled", "order"]

    def get_instance(self):
        return mommy.make(LetterTemplate, user_id="222222")
