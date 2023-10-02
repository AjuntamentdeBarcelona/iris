import base64
import random
from datetime import datetime, timedelta

from django.conf import settings

import pytest
from django.core.files.base import ContentFile
from django.utils import timezone
from mock import patch

from model_mommy import mommy

from ariadna.models import Ariadna
from communications.models import Conversation
from features.models import Feature
from iris_masters.models import (ResponseChannel, ApplicantType, Application, InputChannel, CommunicationMedia,
                                 MediaType, RecordState, Process, Reason, District, ResolutionType, RecordType, Support,
                                 Parameter)
from iris_masters.permissions import ADMIN
from main.utils import SPANISH
from main.test.mixins import FieldsTestSerializerMixin
from profiles.models import Group
from profiles.tests.utils import create_groups, dict_groups
from record_cards.models import (Citizen, SocialEntity, Applicant, ApplicantResponse, RecordCard, RecordCardFeatures,
                                 Workflow, RecordCardBlock, WorkflowPlan, WorkflowResolution, Comment,
                                 RecordCardReasignation, RecordCardStateHistory, InternalOperator, RecordFile)
from record_cards.permissions import MAYORSHIP, RESP_CHANNEL_UPDATE, RESP_WORKED, RECARD_THEME_CHANGE_AREA, \
    RECARD_ANSWER, RECARD_MULTIRECORD
from record_cards.record_actions.normalized_reference import set_reference
from record_cards.serializers import (
    UbicationSerializer, CitizenSerializer, SocialEntitySerializer, ApplicantSerializer, ApplicantResponseSerializer,
    RequestSerializer, RecordCardSerializer, RecordCardManagementIndicatorsSerializer, RecordCardFeaturesSerializer,
    RecordCardSpecialFeaturesSerializer, RecordCardUrgencySerializer, CommentSerializer, RecordCardResponseSerializer,
    RecordCardDetailSerializer, RecordCardFeaturesDetailSerializer, RecordCardSpecialFeaturesDetailSerializer,
    WorkflowPlanSerializer, RecordCardCancelSerializer, WorkflowResoluteSerializer, RecordCardTextResponseSerializer,
    RecordCardListSerializer, WorkflowSerializer, RecordCardMonthIndicatorsSerializer, RecordCardBlockSerializer,
    RecordCardTraceabilitySerializer, WorkflowPlanReadSerializer, WorkflowResolutionSerializer,
    RecordCardReasignationSerializer, RecordCardReasignableSerializer, RecordCardMultiRecordstListSerializer,
    RecordCardThemeChangeSerializer, RecordCardShortListSerializer, RecordCardCheckSerializer,
    RecordCardValidateCheckSerializer, RecordFileShortSerializer, RecordChunkedFileSerializer,
    RecordCardRestrictedListSerializer, RecordCardShortNotificationsSerializer, RecordCardApplicantListSerializer,
    ClaimShortSerializer, ClaimDescriptionSerializer, RecordCardClaimCheckSerializer, RecordCardUpdateSerializer,
    RecordCardRestrictedSerializer, RecordManagementChildrenIndicatorsSerializer,
    RecordCardManagementAmbitIndicatorsSerializer, InternalOperatorSerializer, RecordCardExportSerializer,
    RecordCardTextResponseFilesSerializer)
from record_cards.tests.utils import (CreateRecordCardMixin, SetGroupRequestMixin, FeaturesMixin, CreateRecordFileMixin,
                                      RecordUpdateMixin, SetPermissionMixin)
from themes.models import (Area, Element, ElementDetail, ElementDetailFeature, ElementDetailResponseChannel,
                           DerivationDirect)
from themes.tests.test_serializers import UniqueValidityTest
from themes.tests.utils import CreateThemesMixin
from communications.tests.utils import load_missing_data
from iris_masters.tests.utils import load_missing_data_process, \
    load_missing_data_districts, load_missing_data_applicant, load_missing_data_support, \
    load_missing_data_input, load_missing_data_reasons


@pytest.mark.django_db
class TestUbicationSerializer(CreateThemesMixin):

    @pytest.mark.parametrize(
        "via_type,street,street2,district,add_element_detail,requires_ubication,requires_ubication_district,valid", (
                ("street", "street name", "street name2", None, True, True, False, True),
                ("", "", "", District.CIUTAT_VELLA, True, False, True, True),
                ("street", "street name", "street name2", None, False, True, False, False),
                ("", "street name", "street name2", None, True, True, False, False),
                ("street", "", "street name2", None, True, True, False, False),
                ("street", "street name", "", None, True, True, False, False),
                ("", "", "", None, True, False, True, False),
                ("street", "street name", "street name2", District.EIXAMPLE, True, True, True, True),
                ("street", "street name", "street name2", District.EIXAMPLE, True, False, False, True),
        ))
    def test_ubication_serializer(self, via_type, street, street2, district, add_element_detail, requires_ubication,
                                  requires_ubication_district, valid):
        load_missing_data()
        load_missing_data_process()
        load_missing_data_districts()
        data = {}
        if via_type:
            data["via_type"] = via_type
        if street:
            data["street"] = street
        if street2:
            data["street2"] = street2
        if district:
            data["district"] = district

        context = {}
        if add_element_detail:
            context["element_detail"] = self.create_element_detail(
                requires_ubication=requires_ubication, requires_ubication_district=requires_ubication_district)

        ser = UbicationSerializer(data=data, context=context)
        assert ser.is_valid() is valid, "Ubication serializer fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestCitizenSerializer(SetGroupRequestMixin):

    @pytest.mark.parametrize("name,first_surname,dni,second_dni,birth_year,district,language,sex,citizen_nd,valid", (
            ("Ajuntament", "Ajuntament", "47855341L", None, 1952, District.CIUTAT_VELLA, SPANISH, Citizen.FEMALE, False,
             True),
            ("Ajuntament", "Ajuntament", "47855341L", None, 1952, District.CIUTAT_VELLA, SPANISH, Citizen.FEMALE, True,
             True),
            ("Ajuntament", "Ajuntament", "ND", None, 1952, District.CIUTAT_VELLA, SPANISH, Citizen.FEMALE, True,
             True),
            ("Ajuntament", "Ajuntament", "ND", None, 1952, District.CIUTAT_VELLA, SPANISH, Citizen.FEMALE, False,
             False),
            ("Ajuntament", "Ajuntament", "47855341L", "47855341L", 1952, District.CIUTAT_VELLA, SPANISH, Citizen.MALE,
             False, False),
            ("Ajuntament", "Ajuntament", "47855341L", None, 1852, District.CIUTAT_VELLA, SPANISH, Citizen.FEMALE,
             False, False),
            ("Ajuntament", "Ajuntament", "", None, 1952, District.CIUTAT_VELLA, SPANISH, Citizen.FEMALE, False, False),
            ("Ajuntament", "Ajuntament", "47855341L", "47855478I", 1952, District.CIUTAT_VELLA, SPANISH, Citizen.MALE,
             False, True),
            ("Ajuntament", "Ajuntament", "47855341L", "47855478I", 1952, District.CIUTAT_VELLA, "", Citizen.FEMALE,
             False, False),
            ("Ajuntament", "Ajuntament", "47855341L", "47855478I", 1952, 15, SPANISH, Citizen.FEMALE, False, False),
            ("Ajuntament", "Ajuntament", "47855341L", "47855478I", 1952, District.CIUTAT_VELLA, SPANISH, "", False,
             False),
            ("Ajuntament", "Ajuntament", "47855341L", None, 2952, District.CIUTAT_VELLA, SPANISH, Citizen.FEMALE,
             False, False),
    ))
    def test_citizen_serializer(self, name, first_surname, dni, second_dni, birth_year, district, language, sex,
                                citizen_nd, valid):
        if second_dni:
            mommy.make(Citizen, user_id="222", dni=second_dni)
        load_missing_data_districts()
        data = {
            "name": name,
            "first_surname": first_surname,
            "dni": dni,
            "birth_year": birth_year,
            "district": district,
            "language": language,
            "sex": sex
        }
        _, request = self.set_group_request(citizen_nd=citizen_nd)
        ser = CitizenSerializer(data=data, context={"request": request})
        ser.is_valid()
        assert ser.is_valid() is valid, "Citizen serializer fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestSocialEntitySerializer:

    @pytest.mark.parametrize("social_reason,contact,cif,second_cif,district,language,valid", (
            ("Ajuntament", "Ajuntament", "G07568654", None, District.CIUTAT_VELLA, SPANISH, True),
            ("Ajuntament", "Ajuntament", "G07568654", "G07568654", District.CIUTAT_VELLA, SPANISH, False),
            ("Ajuntament", "Ajuntament", "G07568654", "G07568357", District.CIUTAT_VELLA, SPANISH, True),
            ("Ajuntament", "Ajuntament", "G07568654", "G07568357", 15, SPANISH, False),
            ("Ajuntament", "Ajuntament", "G07568654", "G07568357", District.CIUTAT_VELLA, "", False),

    ))
    def test_social_entity_serializer(self, social_reason, contact, cif, second_cif, district, language, valid):
        if second_cif:
            mommy.make(SocialEntity, user_id="222", cif=second_cif)
        load_missing_data_districts()
        data = {
            "social_reason": social_reason,
            "contact": contact,
            "cif": cif,
            "district": district,
            "language": language
        }
        ser = SocialEntitySerializer(data=data)
        assert ser.is_valid() is valid, "SocialEntity serializer fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestApplicantSerializer(SetGroupRequestMixin):

    @pytest.mark.parametrize("citizen,citizen_dni,citizen_nd,social_entity,flag_ca,valid", (
            (True, "43968167X", True, False, False, True),
            (True, "43968167X", False, False, False, True),
            (True, "ND", True, False, False, True),
            (True, "ND", False, False, False, False),
            (True, "43968167X", True, True, False, False),
            (False, "43968167X", True, True, False, True),
            (False, "43968167X", True, False, False, False),
    ))
    def test_applicant_serializer(self, citizen, citizen_dni, citizen_nd, social_entity, flag_ca, valid):
        data = {
            "flag_ca": flag_ca,
            "user_id": "2222"
        }
        load_missing_data_districts()
        if citizen:
            data["citizen"] = {
                "user_id": "Bxx_xxxS",
                "created_at": "2008-09-30T02:00:00+02:00",
                "updated_at": "2018-11-27T01:00:00+01:00",
                "name": "AxxA",
                "first_surname": "JxxxxxZ",
                "second_surname": "UxxxxxxxD",
                "full_normalized_name": "Axxx xxxxxxx xxxxxxxxD",
                "normalized_name": "AxxA",
                "normalized_first_surname": "JxxxxxZ",
                "normalized_second_surname": "UxxD",
                "dni": citizen_dni,
                "sex": Citizen.MALE,
                "birth_year": 1900,
                "response": False,
                "mib_code": 957759,
                "blocked": False,
                "district": District.CIUTAT_VELLA,
                "language": SPANISH,
                "doc_type": 1,
            }
        if social_entity:
            data["social_entity"] = {
                "user_id": "userX",
                "created_at": "1970-01-01T01:00:00+01:00",
                "updated_at": "2018-06-28T02:00:00+02:00",
                "social_reason": "CABLEMAT. PAIDOS NURIA SULGERIN\"S\"Ñ::..",
                "normal_social_reason": "LABORATORIOSDRESTEVESA",
                "contact": "MOURE M.GLORIA",
                "cif": "125",
                "response": True,
                "mib_code": 987542,
                "blocked": False,
                "district": District.CIUTAT_VELLA,
                "language": SPANISH
            }
        _, request = self.set_group_request(citizen_nd=citizen_nd)
        ser = ApplicantSerializer(data=data, context={"request": request})
        assert ser.is_valid() is valid, "Applicant serializer fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestApplicantResponseSerializer:

    @pytest.mark.parametrize(
        "mobile,other_mobile,email,street_type,street,number,postal_code,municipality,province,language,valid", (
                ("123456789", None, "test@test.com", "street", "rambla bcn", "5A", "07845", "barcelona", "barcenlona",
                 "gl", True),
                ("123456789", "1234", "test@test.com", "street", "rambla bcn", "5A", "07845", "barcelona", "barcenlona",
                 "gl", True),
                ("123456789", None, "test@test.com", "street", "rambla bcn", "5A", "07845", "barcelona", "barcenlona",
                 "", False))
    )
    def test_applicantresponse_serializer(self, mobile, other_mobile, email, street_type, street, number, postal_code,
                                          municipality, province, language, valid):
        load_missing_data()
        citizen = mommy.make(Citizen, user_id="2222")
        applicant = mommy.make(Applicant, user_id="222", citizen=citizen)
        response_channel = ResponseChannel.objects.get(id=random.randint(0, 5))

        if other_mobile:
            citizen = mommy.make(Citizen, user_id="2222")
            other_applicant = mommy.make(Applicant, user_id="222", citizen=citizen)
            mommy.make(ApplicantResponse, applicant=other_applicant, response_channel=response_channel, user_id="222",
                       mobile_number=other_mobile)

        data = {
            "applicant": applicant.pk,
            "mobile_number": mobile,
            "email": email,
            "street_type": street_type,
            "street": street,
            "number": number,
            "postal_code": postal_code,
            "municipality": municipality,
            "province": province,
            "response_channel": response_channel.pk,
            "user_id": "22222",
            "language": language
        }

        ser = ApplicantResponseSerializer(data=data)
        assert ser.is_valid() is valid, "Applicant Response serializer fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestRequestSerializer:
    @pytest.mark.parametrize("is_applicant, valid", ((True, True), (False, False)))
    def test_request_serializer(self, is_applicant, valid):
        load_missing_data_applicant()
        input_channel = mommy.make(InputChannel, user_id="222")
        media_type = mommy.make(MediaType, user_id="222")
        data = {
            "applicant_type": ApplicantType.CIUTADA,
            "application": mommy.make(Application, user_id="222").pk,
            "input_channel": input_channel.pk,
            "communication_media": mommy.make(CommunicationMedia, user_id="222", input_channel=input_channel,
                                              media_type=media_type).pk,
            "user_id": "22222"
        }
        if is_applicant:
            citizen = mommy.make(Citizen, user_id="2222")
            data["applicant_id"] = mommy.make(Applicant, user_id="222", citizen=citizen).pk

        ser = RequestSerializer(data=data)
        assert ser.is_valid() is valid, "Request serializer fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestRecordCardSerializer(SetGroupRequestMixin, CreateRecordFileMixin, CreateRecordCardMixin):

    @pytest.mark.parametrize(
        "remove_applicant_id,remove_input_channel_id,remove_support_id,set_group_input_channel,valid", (
                (False, False, False, True, True),
                (True, False, False, True, False),
                (False, True, False, True, False),
                (False, False, True, True, False),
                (False, False, False, False, False),
        ))
    def test_record_card_serializer(self, remove_applicant_id, remove_input_channel_id, remove_support_id,
                                    set_group_input_channel, valid):
        load_missing_data()
        load_missing_data_process()
        group, request = self.set_group_request()

        if set_group_input_channel:
            record_card_data = self.get_record_card_data(group=group)
        else:
            record_card_data = self.get_record_card_data(set_group_input_channel=False)
        if remove_applicant_id:
            record_card_data.pop("applicant_id", None)
        if remove_input_channel_id:
            record_card_data.pop("input_channel_id", None)
        if remove_support_id:
            record_card_data.pop("support_id", None)
        ser = RecordCardSerializer(data=record_card_data, context={"request": request,
                                                                   "element_detail": self.create_element_detail()})

        assert ser.is_valid() is valid, "RecordCard serializer fails"
        assert isinstance(ser.errors, dict)
        if valid:
            record = ser.save()
            assert record.creation_group
            assert RecordCardStateHistory.objects.get(
                record_card=record, previous_state_id=RecordState.PENDING_VALIDATE,
                next_state_id=RecordState.PENDING_VALIDATE)

    @pytest.mark.parametrize("citizen_dni,support_nd,group_nd,valid", (
            ("43199353O", False, False, True),
            (settings.CITIZEN_ND, False, False, False),
            (settings.CITIZEN_ND, False, True, False),
            (settings.CITIZEN_ND, True, False, False),
            (settings.CITIZEN_ND, True, True, True),
            ("43569353O", True, True, True),
    ))
    def test_record_card_serializer_citizen_nd(self, citizen_dni, support_nd, group_nd, valid):
        load_missing_data()
        load_missing_data_process()
        group, request = self.set_group_request(citizen_nd=group_nd)
        record_card_data = self.get_record_card_data(citizen_dni=citizen_dni, support_nd=support_nd, group=group)
        ser = RecordCardSerializer(data=record_card_data, context={"request": request,
                                                                   "element_detail": self.create_element_detail()})
        assert ser.is_valid() is valid, "RecordCard serializer fails"

    @pytest.mark.parametrize("feature,value,valid", (
            (1, "feature 1", True),
            (2, "value 2", True),
            (3, None, False),
            (None, False, False)
    ))
    def test_record_card_features(self, feature, value, valid):
        load_missing_data()
        load_missing_data_process()
        group, request = self.set_group_request()
        feature_instance = mommy.make(Feature, user_id="222")
        data = self.get_record_card_data(group=group, feature=feature_instance)
        feature_data = {"value": value, "description": "new_description"}
        if feature:
            feature_data["feature"] = feature_instance.pk
        data.update({"features": [feature_data]})
        ser = RecordCardSerializer(data=data, context={"request": request,
                                                       "element_detail": self.create_element_detail()})
        assert ser.is_valid() is valid, "Record Card Serializer fails with features"
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize("feature,value,valid", (
            (1, "feature 1", True),
            (2, "value 2", True),
            (3, None, False),
            (None, False, False)
    ))
    def test_record_card_special_features(self, feature, value, valid):
        load_missing_data()
        load_missing_data_process()
        group, request = self.set_group_request()
        special_feature = mommy.make(Feature, user_id="222", is_special=True)
        data = self.get_record_card_data(group=group, special_feature=special_feature)
        feature_data = {"value": value, "description": "new_description"}
        if feature:
            feature_data["feature"] = special_feature.pk
        data.update({"special_features": [feature_data]})
        ser = RecordCardSerializer(data=data, context={"request": request,
                                                       "element_detail": self.create_element_detail()})
        assert ser.is_valid() is valid, "Record Card Serializer fails with special features"
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize("create_record_card,none_multirecord_from,record_card_hasmultirecord,valid", (
            (True, False, False, True),
            (True, False, True, False),
            (False, True, False, True),
            (False, False, False, False)
    ))
    def test_record_card_multirecord_from(self, create_record_card, none_multirecord_from,
                                          record_card_hasmultirecord, valid):
        load_missing_data()
        load_missing_data_process()
        if create_record_card:
            if record_card_hasmultirecord:
                previous_record_card = self.create_record_card(create_record_card_response=True)
                record_card_pk = self.create_record_card(multirecord_from=previous_record_card,
                                                         create_record_card_response=True).pk
            else:
                record_card_pk = self.create_record_card(create_record_card_response=True).pk
        elif none_multirecord_from:
            record_card_pk = None
        else:
            record_card_pk = 654654
        group, request = self.set_group_request()
        self.set_group_permissions('AAA', group, [RECARD_MULTIRECORD])
        element_detail = self.create_element_detail()
        data = self.get_record_card_data(group=group, multirecord_from=record_card_pk, element_detail=element_detail)
        ser = RecordCardSerializer(data=data, context={"request": request, "element_detail": element_detail})
        assert ser.is_valid() is valid, "Record Card Serializer fails with multirecord_from"
        assert isinstance(ser.errors, dict)
        if valid and record_card_pk:
            multirecord = RecordCard.objects.get(pk=record_card_pk)
            record = ser.save()
            assert multirecord.input_channel == record.input_channel
            assert multirecord.support == record.support
            assert multirecord.applicant_type == record.applicant_type

    @pytest.mark.parametrize("add_communication_media,add_date,valid", (
            (True, True, True),
            (False, True, False),
            (True, False, False),
            (False, False, False),
    ))
    def test_record_card_communication_media(self, add_communication_media, add_date, valid):
        load_missing_data()
        load_missing_data_process()
        load_missing_data_support()
        input_channel = mommy.make(InputChannel, user_id="222")
        media_type = mommy.make(MediaType, user_id="222")
        support = Support.objects.get(pk=Support.COMMUNICATION_MEDIA)
        group, request = self.set_group_request()
        element_detail = self.create_element_detail()
        record_card_data = self.get_record_card_data(autovalidate_records=True, input_channel=input_channel,
                                                     group=group, process_id=Process.PLANING_RESOLUTION_RESPONSE,
                                                     element_detail=element_detail, support=support)
        if add_communication_media:
            record_card_data["communication_media_id"] = mommy.make(
                CommunicationMedia, user_id="222", input_channel=input_channel, media_type=media_type).pk
        else:
            record_card_data.pop("communication_media_id", None)
        record_card_data["communication_media_date"] = timezone.now().strftime("%Y-%m-%d") if add_date else None
        ser = RecordCardSerializer(data=record_card_data, context={"request": request,
                                                                   "element_detail": element_detail})
        assert ser.is_valid() is valid, "Record Card Serializer fails communication media"
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize("object_number", (0, 1, 5))
    def test_record_files(self, tmpdir_factory, object_number):
        _, request = self.set_group_request()
        record_card = self.create_record_card()

        [self.create_file(tmpdir_factory, record_card, file_number) for file_number in range(object_number)]
        serializer_data = RecordCardSerializer(instance=record_card, context={
            "request": request, "element_detail": self.create_element_detail()}).data
        assert "files" in serializer_data
        for file_data in serializer_data["files"]:
            assert "file" in file_data
            assert "filename" in file_data
            assert "delete_url" in file_data
            assert "id" in file_data

    @pytest.mark.parametrize("register_code,register_required,create_ariadna,valid", (
            ("2019/029292", True, True, True),
            ("2019/029292", False, True, True),
            ("2019/029292", True, False, False),
            ("2019/029292", False, False, False),
            ("2019/02a292", True, True, False),
            ("9/025292", True, True, False),
            ("9/0292", True, True, False),
            (None, True, False, False),
    ))
    def test_record_card_ariadna(self, register_code, register_required, create_ariadna, valid):
        load_missing_data()
        load_missing_data_process()
        group, request = self.set_group_request()
        support = mommy.make(Support, user_id="2222", register_required=register_required)
        if create_ariadna:
            ariadna = mommy.make(Ariadna, user_id="2222")
            ariadna.code = register_code
            ariadna.save()
        record_card_data = self.get_record_card_data(support=support, group=group)
        record_card_data["register_code"] = register_code
        serializer = RecordCardSerializer(data=record_card_data,
                                          context={"request": request, "element_detail": self.create_element_detail()})
        assert serializer.is_valid() is valid
        assert isinstance(serializer.errors, dict)

    @pytest.mark.parametrize("creation_department", ("", "test-department", None))
    def test_record_card_creation_department(self, creation_department):
        load_missing_data()
        load_missing_data_process()
        group, request = self.set_group_request()
        record_card_data = self.get_record_card_data(group=group)
        if isinstance(creation_department, str):
            record_card_data["creation_department"] = creation_department
        serializer = RecordCardSerializer(data=record_card_data,
                                          context={"request": request, "element_detail": self.create_element_detail()})
        assert serializer.is_valid() is True
        assert isinstance(serializer.errors, dict)

    def test_quiosc_input_channel(self):
        load_missing_data()
        load_missing_data_process()
        group, request = self.set_group_request()
        record_card_data = self.get_record_card_data(group=group)
        record_card_data["input_channel_id"] = InputChannel.QUIOSC
        serializer = RecordCardSerializer(data=record_card_data,
                                          context={"request": request, "element_detail": self.create_element_detail()})
        assert serializer.is_valid() is False
        assert isinstance(serializer.errors, dict)

    def test_organization(self):
        load_missing_data()
        load_missing_data_process()
        group, request = self.set_group_request()
        record_card_data = self.get_record_card_data(group=group)
        record_card_data["organization"] = "organization"
        serializer = RecordCardSerializer(data=record_card_data,
                                          context={"request": request, "element_detail": self.create_element_detail()})
        assert serializer.is_valid() is True
        assert isinstance(serializer.errors, dict)

    @pytest.mark.parametrize("set_group_input_channel,set_suport_input_channel,valid", (
            (True, True, True),
            (False, True, False),
            (True, False, False),
    ))
    def test_record_input_channel(self, set_group_input_channel, set_suport_input_channel, valid):
        load_missing_data()
        load_missing_data_input()
        load_missing_data_process()
        group, request = self.set_group_request()
        input_channel = InputChannel.objects.get(pk=InputChannel.ALTRES_CANALS)
        element_detail = self.create_element_detail()
        record_card_data = self.get_record_card_data(group=group, set_group_input_channel=set_group_input_channel,
                                                     set_suport_input_channel=set_suport_input_channel,
                                                     input_channel=input_channel)
        serializer = RecordCardSerializer(data=record_card_data,
                                          context={"request": request, "element_detail": element_detail})
        assert serializer.is_valid() is valid
        assert isinstance(serializer.errors, dict)

    @pytest.mark.parametrize("applicant_blocked,allowed_theme,valid", (
            (True, False, False),
            (False, False, True),
            (True, True, True),
            (False, True, True)
    ))
    def test_record_applicant_blocked(self, applicant_blocked, allowed_theme, valid):
        load_missing_data()
        group, request = self.set_group_request()
        load_missing_data_process()
        if allowed_theme:
            element = self.create_element()
            no_block_theme_pk = int(Parameter.get_parameter_by_key("TEMATICA_NO_BLOQUEJADA", 392))
            element_detail = mommy.make(ElementDetail, user_id="22222", pk=no_block_theme_pk, element=element,
                                        process_id=Process.CLOSED_DIRECTLY, visible=True, active=True,
                                        record_type_id=mommy.make(RecordType, user_id="user_id").pk)
        else:
            element_detail = self.create_element_detail()
        citizen = mommy.make(Citizen, user_id="2222", blocked=applicant_blocked)
        applicant = mommy.make(Applicant, user_id="22222", citizen=citizen)
        record_card_data = self.get_record_card_data(group=group, element_detail=element_detail, applicant=applicant)
        serializer = RecordCardSerializer(data=record_card_data,
                                          context={"request": request, "element_detail": element_detail})
        assert serializer.is_valid() is valid
        assert isinstance(serializer.errors, dict)


@pytest.mark.django_db
class TestRecordCardUpdateSerializer(SetGroupRequestMixin, CreateRecordFileMixin, FeaturesMixin, CreateRecordCardMixin,
                                     RecordUpdateMixin):

    @pytest.mark.parametrize(
        "initial_state,description,change_features,update_mayorship,update_ubication,"
        "update_response_channel,permissions,valid", (
                (RecordState.PENDING_VALIDATE, "description", True, True, True, True, [MAYORSHIP, RESP_CHANNEL_UPDATE],
                 True),
                (RecordState.PENDING_VALIDATE, "", True, False, True, True, [RESP_CHANNEL_UPDATE], False),
                (RecordState.PENDING_VALIDATE, "description", False, False, True, True, [RESP_CHANNEL_UPDATE], True),
                (RecordState.PENDING_VALIDATE, "description", True, False, True, True, [], False),
                (RecordState.PENDING_VALIDATE, "description", False, True, True, True, [MAYORSHIP, RESP_CHANNEL_UPDATE],
                 True),
                (RecordState.PENDING_VALIDATE, "description", False, True, False, True,
                 [MAYORSHIP, RESP_CHANNEL_UPDATE], True),
                (RecordState.PENDING_VALIDATE, "description", True, True, True, True, [], False),
                (RecordState.PENDING_VALIDATE, "description", True, True, True, False, [MAYORSHIP, RESP_CHANNEL_UPDATE],
                 True),
                (RecordState.PENDING_VALIDATE, "description", True, True, True, False, [MAYORSHIP], True),

                (RecordState.CLOSED, "description", True, False, True, True, [], False),
                (RecordState.CLOSED, "description", True, False, True, True, [ADMIN], False),
                (RecordState.CLOSED, None, False, False, False, True, [ADMIN, RESP_CHANNEL_UPDATE], True),
                (RecordState.CLOSED, None, False, False, False, True, [ADMIN], False),
                (RecordState.CLOSED, None, False, False, True, True, [ADMIN], False),
                (RecordState.CLOSED, None, True, False, True, True, [ADMIN], False),
                (RecordState.CLOSED, "description", True, True, True, True, [MAYORSHIP], False),
                (RecordState.CLOSED, "description", False, False, True, True, [MAYORSHIP], False),
                (RecordState.CLOSED, "description", False, False, False, True, [MAYORSHIP], False),
                (RecordState.CLOSED, None, False, False, False, True, [RESP_CHANNEL_UPDATE, ADMIN], True),
                (RecordState.CLOSED, None, False, False, False, True, [RESP_CHANNEL_UPDATE], False),
        ))
    def test_record_card_update_serializer(self, initial_state, description, change_features,
                                           update_mayorship, update_ubication, update_response_channel, permissions,
                                           valid):
        load_missing_data()
        load_missing_data_reasons()
        _, parent, _, _, _, _ = create_groups()
        self.set_group_permissions("222222", parent, permissions)
        _, request = self.set_group_request(group=parent)

        features = self.create_features() if change_features else []
        element_detail = self.create_element_detail()
        ElementDetailResponseChannel.objects.create(elementdetail=element_detail,
                                                    responsechannel_id=ResponseChannel.SMS)

        input_channel = mommy.make(InputChannel, user_id="2222", can_be_mayorship=True)
        record_card = self.create_record_card(record_state_id=initial_state, responsible_profile=parent,
                                              create_record_card_response=True, features=features,
                                              communication_media_date=timezone.now().date(),
                                              communication_media_detail="testtesttest", element_detail=element_detail,
                                              input_channel=input_channel)

        expected_data = self.set_initial_expected_data(record_card)

        data, update_data = self.set_data_update(record_card, description, change_features, features,
                                                 update_mayorship, update_ubication, update_response_channel)

        serializer = RecordCardUpdateSerializer(instance=record_card, data=data,
                                                context={"request": request, "element_detail": element_detail})

        assert serializer.is_valid() is valid
        assert isinstance(serializer.errors, dict)
        if valid:
            record_card = serializer.save()
            assert Comment.objects.get(record_card=record_card, reason_id=Reason.RECORDCARD_UPDATED)
            self.update_expected_data(expected_data, update_data)

        assert record_card.description == expected_data["expected_description"]
        assert record_card.mayorship == expected_data["expected_mayorship"]
        assert record_card.ubication_id == expected_data["expected_ubication"]
        assert record_card.recordcardresponse.response_channel_id == expected_data["expected_response_channel"]

    @pytest.mark.parametrize("create_record_card_response", (True, False))
    def test_update_serializer_recordcardresponse(self, create_record_card_response):
        load_missing_data_reasons()
        record_card = self.create_record_card(create_record_card_response=create_record_card_response)
        if not create_record_card_response:
            record_card_response_data = {
                "response_channel": ResponseChannel.TELEPHONE,
                "address_mobile_email": "971258745",
                "language": "gl"
            }
            ElementDetailResponseChannel.objects.create(responsechannel_id=ResponseChannel.TELEPHONE,
                                                        elementdetail_id=record_card.element_detail_id)
        else:
            record_card_response_data = RecordCardResponseSerializer(instance=record_card.recordcardresponse).data
            record_card_response_data["response_channel"] = ResponseChannel.SMS
            record_card_response_data["address_mobile_email"] = "666777888"
            ElementDetailResponseChannel.objects.create(responsechannel_id=ResponseChannel.SMS,
                                                        elementdetail_id=record_card.element_detail_id)

        data = {"recordcardresponse": record_card_response_data}

        _, parent, _, _, _, _ = create_groups()
        self.set_group_permissions("222222", parent, [RESP_CHANNEL_UPDATE])
        _, request = self.set_group_request(group=parent)
        serializer = RecordCardUpdateSerializer(instance=record_card, data=data,
                                                context={"request": request,
                                                         "element_detail": record_card.element_detail})

        assert serializer.is_valid() is True
        serializer.save()
        assert Comment.objects.get(record_card=record_card, reason_id=Reason.RECORDCARD_UPDATED)


@pytest.mark.django_db
class TestRecordFileShortSerializer(CreateRecordCardMixin, CreateRecordFileMixin, FieldsTestSerializerMixin):
    serializer_class = RecordFileShortSerializer
    data_keys = ["id", "file", "filename", "delete_url", "can_delete", "file_type", "created_at"]

    def test_serializer(self, tmpdir_factory):
        ser = self.get_serializer_class()(instance=self.get_instance(tmpdir_factory))
        assert len(ser.data.keys()) == self.get_keys_number()
        for data_key in self.data_keys:
            assert data_key in ser.data, f"Required {data_key} not present in serializer data"

    def get_instance(self, tmpdir_factory):
        record_card = self.create_record_card()
        return self.create_file(tmpdir_factory, record_card, 1)


@pytest.mark.django_db
class TestRecordCardDetailSerializer(FieldsTestSerializerMixin, SetGroupRequestMixin, CreateRecordCardMixin):
    serializer_class = RecordCardDetailSerializer
    data_keys = ["id", "user_id", "created_at", "updated_at", "description", "responsible_profile", "process",
                 "mayorship", "normalized_record_id", "alarm", "auxiliary", "closing_date",
                 "ans_limit_date", "urgent", "communication_media_detail", "communication_media_date",
                 "record_parent_claimed", "reassignment_not_allowed", "page_origin", "email_external_derivation",
                 "user_displayed", "historicized", "allow_multiderivation", "start_date_process", "appointment_time",
                 "similar_process", "response_state", "notify_quality", "multi_complaint", "lopd", "citizen_alarm",
                 "ci_date", "support_numbers", "element_detail", "element_detail_id", "request_id", "ubication",
                 "record_state", "record_state_id", "record_type", "record_type_id", "applicant_type", "request",
                 "communication_media", "support", "support_id", "input_channel", "input_channel_id", "features",
                 "special_features", "actions", "alarms", "ideal_path", "current_step", "next_step_code", "comments",
                 "recordcardresponse", "recordplan", "recordcardresolution", "workflow", "blocked", "multirecord_from",
                 "is_multirecord", "external_ids", "files", "registers", "full_detail", "claimed_from",
                 "claims_number", "claims_links", "group_can_answer", "organization", "creation_group"]

    def get_instance(self):
        return self.create_record_card()

    @pytest.mark.parametrize("value", ("feature 1", "value 2"))
    def test_record_card_detail_features(self, value):
        record_card = self.create_record_card()
        _, request = self.set_group_request(group=record_card.responsible_profile)
        feature = mommy.make(Feature, user_id="222", values_type=None)
        RecordCardFeatures.objects.create(record_card=record_card, feature=feature, value=value)
        ser = RecordCardDetailSerializer(instance=record_card, context={"request": request})
        assert ser.data
        for record_card_feature in ser.data["features"]:
            if record_card_feature["feature"]["id"] == feature.pk:
                assert record_card_feature["value"] == value

    @pytest.mark.parametrize("only_ambit,group_is_ambit,group_can_answer", (
            (True, True, True),
            (True, False, False),
            (False, True, True),
            (False, False, True),
    ))
    def test_group_can_answer(self, only_ambit, group_is_ambit, group_can_answer):
        _, parent, _, _, _, _ = create_groups()
        load_missing_data_process()
        record_card = self.create_record_card(process_pk=Process.PLANING_RESOLUTION_RESPONSE,
                                              record_state_id=RecordState.PENDING_ANSWER, responsible_profile=parent)
        if only_ambit:
            record_card.claims_number = 10
            record_card.save()

        parent.is_ambit = group_is_ambit
        parent.save()

        self.set_group_permissions("user_id", parent, permissions_list=[RECARD_ANSWER])
        _, request = self.set_group_request(group=parent)
        ser = RecordCardDetailSerializer(instance=record_card, context={"request": request})
        assert ser.data["group_can_answer"]["can_answer"] is group_can_answer
        if not ser.data["group_can_answer"]["can_answer"]:
            assert "reason" in ser.data["group_can_answer"]
        assert ser.data["actions"]["answer"]["can_perform"] is group_can_answer


@pytest.mark.django_db
class TestRecordCardThemeChangeSerializer(FeaturesMixin, SetGroupRequestMixin, CreateRecordCardMixin):

    @pytest.mark.parametrize(
        "change_theme,change_features,perform_derivation,reassignment_not_allowed,create_ambit_derivation,"
        "claims_number,create_noambit_derivation,valid", (
                (True, True, True, False, True, 0, False, False),
                (True, True, False, False, True, 0, False, False),
                (True, True, None, False, True, 0, False, False),
                (True, False, True, False, True, 0, False, False),
                (False, True, True, False, True, 0, False, False),
                (False, False, True, False, True, 0, False, False),

                (True, True, True, True, True, 0, False, False),
                (True, True, True, True, False, 0, False, False),
                (True, True, True, True, False, 0, True, False),
                (True, True, True, False, False, 10, True, False),
                (True, True, True, False, True, 10, False, False),
        ))
    def test_record_card_theme_change(self, change_theme, change_features, perform_derivation, reassignment_not_allowed,
                                      create_ambit_derivation, claims_number, create_noambit_derivation, valid):

        _, parent, _, soon2, noambit_parent, _ = create_groups()
        load_missing_data_process()
        initial_features = self.create_features()
        record_card = self.create_record_card(features=initial_features, previous_created_at=True, create_worflow=True,
                                              reassignment_not_allowed=reassignment_not_allowed,
                                              claims_number=claims_number, responsible_profile=parent,
                                              record_state_id=RecordState.IN_RESOLUTION,
                                              process_pk=Process.EVALUATION_RESOLUTION_RESPONSE)
        initial_responsible = parent

        new_features = []
        _, request = self.set_group_request(group=parent)

        if change_theme:
            process = mommy.make(Process, id=Process.CLOSED_DIRECTLY)
            record_type = mommy.make(RecordType, user_id="2222")
            element_detail = mommy.make(ElementDetail, user_id="222", element=record_card.element_detail.element,
                                        short_description="test", short_description_es="test",
                                        short_description_gl="test", short_description_en="test", description="test",
                                        description_es="test", description_gl="test", description_en="test",
                                        process=process, record_type=record_type)
            new_features = self.create_features()
            for feature in new_features:
                ElementDetailFeature.objects.create(element_detail=element_detail, feature=feature, is_mandatory=True)
            if create_ambit_derivation:
                DerivationDirect.objects.create(element_detail=element_detail,
                                                record_state_id=RecordState.IN_RESOLUTION, group=soon2)
            elif create_noambit_derivation:
                DerivationDirect.objects.create(element_detail=element_detail,
                                                record_state_id=RecordState.IN_RESOLUTION, group=noambit_parent)
            element_detail.register_theme_ambit()
        else:
            element_detail = record_card.element_detail

        if change_features:
            features = new_features
        else:
            features = initial_features

        data = {
            "element_detail_id": element_detail.pk,
            "features": [{"feature": f.pk, "value": str(random.randint(0, 99))} for f in features if not f.is_special],
            "special_features": [{"feature": f.pk, "value": str(random.randint(0, 99))}
                                 for f in features if f.is_special],
        }
        if isinstance(perform_derivation, bool):
            data["perform_derivation"] = perform_derivation

        ser = RecordCardThemeChangeSerializer(instance=record_card, data=data, context={"request": request})
        assert ser.is_valid() is valid, "RecordCard Theme Change serializer fails"
        assert isinstance(ser.errors, dict)
        if valid:
            self.assert_save_data(ser, record_card, change_theme, perform_derivation, create_ambit_derivation,
                                  create_noambit_derivation, initial_responsible, parent, soon2, noambit_parent)

    @staticmethod
    def assert_save_data(serializer, record_card, change_theme, perform_derivation, create_ambit_derivation,
                         create_noambit_derivation, initial_responsible, parent, soon2, noambit_parent):
        serializer.save()
        record_card = RecordCard.objects.get(pk=record_card.pk)
        assert record_card.workflow.element_detail_modified is change_theme
        if change_theme:
            assert RecordCardFeatures.objects.filter(
                record_card_id=record_card.pk, enabled=True).count() == 6
            assert RecordCardFeatures.objects.filter(
                record_card_id=record_card.pk, enabled=True, is_theme_feature=True).count() == 3
            assert RecordCardFeatures.objects.filter(
                record_card_id=record_card.pk, enabled=True, is_theme_feature=False).count() == 3

            if perform_derivation is False:
                assert record_card.responsible_profile == initial_responsible
            else:
                if create_ambit_derivation:
                    assert record_card.responsible_profile == soon2
                elif create_noambit_derivation:
                    assert record_card.responsible_profile == noambit_parent
                else:
                    assert record_card.responsible_profile == parent
            assert Comment.objects.filter(
                record_card_id=record_card.pk, reason=Reason.FEATURES_THEME_NO_VISIBLES).count() == 2
        else:
            assert RecordCardFeatures.objects.filter(
                record_card_id=record_card.pk, enabled=True).count() == 3
            assert RecordCardFeatures.objects.filter(
                record_card_id=record_card.pk, enabled=True, is_theme_feature=True).count() == 3
            assert RecordCardFeatures.objects.filter(
                record_card_id=record_card.pk, enabled=True, is_theme_feature=False).count() == 0

    @pytest.mark.parametrize("record_state_id,valid", (
            (RecordState.PENDING_VALIDATE, True),
            (RecordState.EXTERNAL_RETURNED, True),
            (RecordState.IN_RESOLUTION, True),
            (RecordState.PENDING_ANSWER, False),
            (RecordState.CLOSED, True),
    ))
    def test_validated_record(self, record_state_id, valid):
        dair, _, _, _, _, _ = create_groups()

        initial_features = self.create_features()
        record_card = self.create_record_card(features=initial_features, previous_created_at=True, create_worflow=True,
                                              reassignment_not_allowed=False, responsible_profile=dair,
                                              record_state_id=record_state_id,
                                              process_pk=Process.EVALUATION_RESOLUTION_RESPONSE)
        _, request = self.set_group_request(group=dair)

        process = mommy.make(Process, id=Process.CLOSED_DIRECTLY)
        record_type = mommy.make(RecordType, user_id="2222")
        element_detail = mommy.make(ElementDetail, user_id="222", element=record_card.element_detail.element,
                                    short_description="test", short_description_es="test", short_description_gl="test",
                                    short_description_en="test", description="test", description_es="test",
                                    description_gl="test", description_en="test", process=process,
                                    record_type=record_type)
        features = self.create_features()

        for feature in features:
            ElementDetailFeature.objects.create(element_detail=element_detail, feature=feature, is_mandatory=True)
        DerivationDirect.objects.create(element_detail=element_detail, record_state_id=RecordState.PENDING_VALIDATE,
                                        group=record_card.responsible_profile)
        element_detail.register_theme_ambit()
        data = {
            "element_detail_id": element_detail.pk,
            "features": [{"feature": f.pk, "value": str(random.randint(0, 99))} for f in features if not f.is_special],
            "special_features": [{"feature": f.pk, "value": str(random.randint(0, 99))}
                                 for f in features if f.is_special],
            "perform_derivation": True
        }

        ser = RecordCardThemeChangeSerializer(instance=record_card, data=data, context={"request": request})
        assert ser.is_valid() is valid, "RecordCard Theme Change serializer fails (no) validated records"
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize("has_permission,different_area,valid", (
            (True, True, True),
            (True, False, True),
            (False, True, False),
            (False, False, True),
    ))
    def test_area_change_permission(self, has_permission, different_area, valid):
        _, parent, _, soon2, noambit_parent, _ = create_groups()
        load_missing_data_process()
        initial_features = self.create_features()
        record_card = self.create_record_card(features=initial_features, previous_created_at=True, create_worflow=True,
                                              reassignment_not_allowed=False, responsible_profile=parent,
                                              record_state_id=RecordState.PENDING_VALIDATE,
                                              process_pk=Process.EVALUATION_RESOLUTION_RESPONSE)
        _, request = self.set_group_request(group=parent)
        if has_permission:
            self.set_group_permissions("user_id", parent, [RECARD_THEME_CHANGE_AREA])

        process = mommy.make(Process, id=Process.CLOSED_DIRECTLY)
        record_type = mommy.make(RecordType, user_id="2222")
        if different_area:
            area = mommy.make(Area, user_id="22222")
            element = mommy.make(Element, user_id="2222", area=area)
        else:
            element = record_card.element_detail.element
        element_detail = mommy.make(ElementDetail, user_id="222", element=element, short_description="test",
                                    short_description_es="test", short_description_gl="test",
                                    short_description_en="test", description="test", description_es="test",
                                    description_gl="test", description_en="test", process=process,
                                    record_type=record_type)
        DerivationDirect.objects.create(element_detail=element_detail, record_state_id=RecordState.PENDING_VALIDATE,
                                        group=soon2)
        element_detail.register_theme_ambit()

        data = {
            "element_detail_id": element_detail.pk,
            "features": [],
            "special_features": [],
            "perform_derivation": True
        }

        ser = RecordCardThemeChangeSerializer(instance=record_card, data=data, context={"request": request})
        assert ser.is_valid() is valid, "RecordCard Theme Change serializer fails (no) validated records"
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize("record_state_id,perform_derivation", (
            (RecordState.PENDING_VALIDATE, True),
            (RecordState.PENDING_VALIDATE, False),
            (RecordState.EXTERNAL_RETURNED, True),
            (RecordState.EXTERNAL_RETURNED, False),
    ))
    def test_change_theme_autovalidate(self, record_state_id, perform_derivation):
        load_missing_data_process()
        load_missing_data_reasons()
        _, parent, _, soon2, noambit_parent, _ = create_groups()
        _, request = self.set_group_request(group=parent)
        self.set_group_permissions("user_id", parent, [RECARD_THEME_CHANGE_AREA])

        element_detail = self.create_element_detail(process_id=Process.CLOSED_DIRECTLY)

        record_card = self.create_record_card(previous_created_at=False, create_worflow=False,
                                              reassignment_not_allowed=False, responsible_profile=parent,
                                              record_state_id=record_state_id, element_detail=element_detail)

        new_element_detail = self.create_element_detail(process_id=Process.EVALUATION_RESOLUTION_RESPONSE,
                                                        autovalidate_records=True)
        DerivationDirect.objects.create(element_detail=new_element_detail, record_state_id=RecordState.IN_PLANING,
                                        group=noambit_parent)
        new_element_detail.register_theme_ambit()
        data = {
            "element_detail_id": new_element_detail.pk,
            "features": [],
            "special_features": [],
            "perform_derivation": perform_derivation
        }
        ser = RecordCardThemeChangeSerializer(instance=record_card, data=data, context={"request": request})
        assert ser.is_valid() is True, "RecordCard Theme Change serializer fails in autovalidation"
        assert isinstance(ser.errors, dict)
        record_card = ser.save()
        assert record_card.process_id == Process.EVALUATION_RESOLUTION_RESPONSE
        assert record_card.record_state_id == RecordState.IN_PLANING
        if perform_derivation:
            assert record_card.responsible_profile == noambit_parent
        else:
            assert record_card.responsible_profile == parent
        assert record_card.workflow

    def test_change_theme_ans_limits(self):
        load_missing_data_process()
        load_missing_data_reasons()
        _, parent, _, soon2, noambit_parent, _ = create_groups()
        _, request = self.set_group_request(group=parent)
        self.set_group_permissions("user_id", parent, [RECARD_THEME_CHANGE_AREA])

        element_detail = self.create_element_detail(process_id=Process.CLOSED_DIRECTLY, sla_hours=24)

        record_card = self.create_record_card(previous_created_at=False, create_worflow=False,
                                              reassignment_not_allowed=False, responsible_profile=parent,
                                              element_detail=element_detail)

        new_sla_hours = 48
        new_element_detail = self.create_element_detail(process_id=Process.EVALUATION_RESOLUTION_RESPONSE,
                                                        autovalidate_records=True, sla_hours=new_sla_hours)
        data = {
            "element_detail_id": new_element_detail.pk,
            "features": [],
            "special_features": [],
            "perform_derivation": False
        }
        ser = RecordCardThemeChangeSerializer(instance=record_card, data=data, context={"request": request})
        assert ser.is_valid() is True, "RecordCard Theme Change serializer fails"
        ser.save()

        record_card = RecordCard.objects.get(pk=record_card.pk)
        assert record_card.ans_limit_date.day == (record_card.created_at + timedelta(hours=new_sla_hours)).day

    @pytest.mark.parametrize("initial_state", (
        RecordState.PENDING_VALIDATE, RecordState.EXTERNAL_RETURNED
    ))
    def test_change_theme_update_detail_info(self, initial_state):
        load_missing_data_process()
        load_missing_data_reasons()
        _, parent, _, soon2, noambit_parent, _ = create_groups()
        _, request = self.set_group_request(group=parent)
        self.set_group_permissions("user_id", parent, [RECARD_THEME_CHANGE_AREA])

        element_detail = self.create_element_detail(process_id=Process.CLOSED_DIRECTLY, sla_hours=24)

        record_card = self.create_record_card(previous_created_at=False, create_worflow=False,
                                              reassignment_not_allowed=False, responsible_profile=parent,
                                              element_detail=element_detail, record_state_id=initial_state)

        new_sla_hours = 48
        record_type_id = mommy.make(RecordType, user_id="222").pk
        new_element_detail = self.create_element_detail(process_id=Process.EVALUATION_RESOLUTION_RESPONSE,
                                                        autovalidate_records=True, sla_hours=new_sla_hours,
                                                        record_type_id=record_type_id)
        data = {
            "element_detail_id": new_element_detail.pk,
            "features": [],
            "special_features": [],
            "perform_derivation": False
        }
        ser = RecordCardThemeChangeSerializer(instance=record_card, data=data, context={"request": request})
        assert ser.is_valid() is True, "RecordCard Theme Change serializer fails"
        ser.save()

        record_card = RecordCard.objects.get(pk=record_card.pk)
        assert record_card.record_type_id == record_type_id
        assert record_card.process_id == Process.EVALUATION_RESOLUTION_RESPONSE


@pytest.mark.django_db
class TestRecordCardListSerializer(CreateRecordCardMixin, FieldsTestSerializerMixin):
    serializer_class = RecordCardListSerializer
    data_keys = ("id", "user_id", "created_at", "updated_at", "description", "responsible_profile", "process",
                 "mayorship", "normalized_record_id", "alarm", "ans_limit_date", "urgent",
                 "element_detail", "record_state", "actions", "alarms", "full_detail", "ubication", "user_displayed",
                 "record_type")

    def get_instance(self):
        return self.create_record_card()


@pytest.mark.django_db
class TestRecordCardRestrictedListSerializer(CreateRecordCardMixin, FieldsTestSerializerMixin):
    serializer_class = RecordCardRestrictedListSerializer
    data_keys = ("id", "user_id", "created_at", "updated_at", "normalized_record_id", "record_type", "input_channel",
                 "element_detail", "record_state", "responsible_profile", "support", "description",
                 "full_detail")

    def get_instance(self):
        return self.create_record_card()


@pytest.mark.django_db
class TestRecordCardExportSerializer(CreateRecordCardMixin, FieldsTestSerializerMixin):
    serializer_class = RecordCardExportSerializer
    data_keys = ("identificador", "tipusfitxa", "data_alta", "data_tancament", "dies_oberta", "antiguitat",
                 "tipus_solicitant", "solicitant", "districte", "barri", "tipus_via", "carrer", "numero", "area",
                 "element", "detall", "carac_especial_desc", "carac_especial", "descripcio", "estat",
                 "perfil_responsable", "tipus_resposta", "resposta_feta", "comentari_qualitat")

    def get_instance(self):
        return self.create_record_card()


@pytest.mark.django_db
class TestRecordCardRestrictedSerializer(CreateRecordCardMixin, FieldsTestSerializerMixin):
    serializer_class = RecordCardRestrictedSerializer
    data_keys = ("id", "user_id", "created_at", "updated_at", "normalized_record_id", "record_type", "input_channel",
                 "element_detail", "record_state", "responsible_profile", "support", "registers", "full_detail")

    def get_instance(self):
        return self.create_record_card()


@pytest.mark.django_db
class TestRecordCardShortListSerializer(TestRecordCardListSerializer):
    serializer_class = RecordCardShortListSerializer
    data_keys = ("id", "description", "normalized_record_id", "applicant_document", "short_address")


@pytest.mark.django_db
class TestRecordCardFeaturesDetailSerializer(CreateRecordCardMixin):
    serializer_class = RecordCardFeaturesDetailSerializer

    @pytest.mark.parametrize("value", ("feature 1", "value 2"))
    def test_record_card_features_detail(self, value):
        load_missing_data()
        record_card = self.create_record_card()
        feature = mommy.make(Feature, user_id="222", values_type=None)
        record_card_feature = RecordCardFeatures.objects.create(record_card=record_card, feature=feature, value=value)
        record_card_feature.order = 100
        ser = self.serializer_class(instance=record_card_feature)
        assert ser.data
        assert ser.data["value"] == value


@pytest.mark.django_db
class TestRecordCardFeaturesSpecialDetailSerializer(TestRecordCardFeaturesDetailSerializer, CreateRecordCardMixin):
    serializer_class = RecordCardSpecialFeaturesDetailSerializer


class TestRecordManagementChildrenIndicatorsSerializer:
    @pytest.mark.parametrize("group_id,group_name,pending_validation,processing,expired,near_expire,valid", (
            (33, "1", 2, 3, 4, 5, True),
            (None, 1, "b", "c", "d", "e", False)
    ))
    def test_record_card_user_summary(self, group_id, group_name, pending_validation, processing, expired, near_expire,
                                      valid):
        ser = RecordManagementChildrenIndicatorsSerializer(data={
            "group_id": group_id,
            "group_name": group_name,
            "pending_validation": pending_validation,
            "processing": processing,
            "expired": expired,
            "near_expire": near_expire
        })
        assert ser.is_valid() is valid, "RecordCardUserSummary serializer fails"
        assert isinstance(ser.errors, dict)


class TestRecordCardManagementAmbitIndicatorsSerializer:
    @pytest.mark.parametrize("childrens,pending_validation,processing,expired,near_expire,valid", (
            ([{"group_id": 1, "group_name": "test", "pending_validation": 1, "processing": 1, "expired": 1,
               "near_expire": 1}],
             2, 3, 4, 5, True),
            ([], "b", "c", "d", "e", False),
            ([{"group_id": 3, "gro_name": "test", "processing": 1, "expired": 1, "near_expire": 1}], 2, 3, 4, 5, False)
    ))
    def test_record_card_user_summary(self, childrens, pending_validation, processing, expired, near_expire, valid):
        ser = RecordCardManagementAmbitIndicatorsSerializer(data={
            "childrens": childrens,
            "pending_validation": pending_validation,
            "processing": processing,
            "expired": expired,
            "near_expire": near_expire
        })
        assert ser.is_valid() is valid, "RecordCardUserSummary serializer fails"
        assert isinstance(ser.errors, dict)


class TestRecordCardManagementIndicatorsSerializer:
    @pytest.mark.parametrize("urgent,pending_validation,processing,expired,near_expire,valid", (
            (1, 2, 3, 4, 5, True),
            ("a", "b", "c", "d", "e", False)
    ))
    def test_record_card_user_summary(self, urgent, pending_validation, processing, expired, near_expire, valid):
        ser = RecordCardManagementIndicatorsSerializer(data={
            "urgent": urgent,
            "pending_validation": pending_validation,
            "processing": processing,
            "expired": expired,
            "near_expire": near_expire
        })
        assert ser.is_valid() is valid, "RecordCardUserSummary serializer fails"
        assert isinstance(ser.errors, dict)


class TestRecordCardMonthIndicatorsSerializer:
    @pytest.mark.parametrize("pend_validation,processing,closed,cancelled,external_processing,pending_records,"
                             "average_close_days,average_age_days,entries,valid",
                             ((1, 2, 3, 4, 5, 6, 7, 8, 9, True), ("a", "b", "c", "d", "e", "f", "g", "h", "i", False)))
    def test_record_card_user_summary(self, pend_validation, processing, closed, cancelled, external_processing,
                                      pending_records, average_close_days, average_age_days, entries, valid):
        ser = RecordCardMonthIndicatorsSerializer(data={
            "pending_validation": pend_validation,
            "processing": processing,
            "closed": closed,
            "cancelled": cancelled,
            "external_processing": external_processing,
            "pending_records": pending_records,
            "average_close_days": average_close_days,
            "average_age_days": average_age_days,
            "entries": entries
        })
        assert ser.is_valid() is valid, "RecordCardMonthIndicators serializer fails"
        assert isinstance(ser.errors, dict)


class TestRecordCardUrgencySerializer:

    @pytest.mark.parametrize("urgent,valid", (
            (True, True),
            (False, True),
            (None, False)
    ))
    def test_record_card_urgency(self, urgent, valid):
        ser = RecordCardUrgencySerializer(data={
            "urgent": urgent,
        })
        assert ser.is_valid() is valid, "RecordCardUrgency serializer fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestRecordCardFeaturesSerializer:
    serializer_class = RecordCardFeaturesSerializer
    fail_message = "RecordCard Features serializer fails"

    @pytest.mark.parametrize("feature,value,valid", (
            (1, "feature 1", True),
            (2, "value 2", True),
            (3, None, False),
            (None, False, False)
    ))
    def test_elementdetail_feature_serializer(self, feature, value, valid):
        data = {"value": value}
        if feature:
            data["feature"] = mommy.make(Feature, user_id="222").pk
        ser = self.serializer_class(data=data)
        assert ser.is_valid() is valid, self.fail_message
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestRecordCardSpecialFeaturesSerializer(TestRecordCardFeaturesSerializer):
    serializer_class = RecordCardSpecialFeaturesSerializer
    fail_message = "RecordCard Special Features serializer fails"


@pytest.mark.django_db
class TestCommentSerializer(CreateRecordCardMixin):

    @pytest.mark.parametrize("is_reason,is_record_card,comment,valid", (
            (True, True, "test comment", True),
            (False, True, "test comment", True),
            (False, False, "test comment", False),
            (True, False, "test comment", False),
            (True, True, "", False),
    ))
    def test_comment_serializer(self, is_reason, is_record_card, comment, valid):
        load_missing_data_reasons()
        reason = Reason.objects.first().pk if is_reason else None
        record_card = self.create_record_card().pk if is_record_card else None

        data = {
            "reason": reason,
            "record_card": record_card,
            "comment": comment
        }
        ser = CommentSerializer(data=data)
        assert ser.is_valid() is valid, "Comment serializer fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestRecordCardResponseSerializer(CreateRecordCardMixin, SetGroupRequestMixin, SetPermissionMixin):
    theme_response_channels = [ResponseChannel.EMAIL, ResponseChannel.SMS, ResponseChannel.LETTER,
                               ResponseChannel.NONE, ResponseChannel.IMMEDIATE, ResponseChannel.TELEPHONE]

    @pytest.mark.parametrize(
        "address_mobile_email,number,postal_code,immediate_response,create_record_card,language,valid", (
                ("test", "111", "08009", True, True, "gl", True),
                ("test", "111", "08009", False, True, "gl", True),
                ("test", "111", "08009", True, False, "gl", False),
                ("test", "111", "08009", True, True, "", False),
        ))
    def test_record_card_response_serializer_by_none(self, address_mobile_email, number, postal_code,
                                                     immediate_response, create_record_card, language, valid):
        # TODO: readd case when front is ready. Take care of the deleted argument themes _ response _ channels
        # TODO: ("test", "111", "08009", "", True, [ResponseChannel.EMAIL], True, False),
        load_missing_data_reasons()
        data = {
            "response_channel": ResponseChannel.NONE,
            "address_mobile_email": address_mobile_email,
            "number": number,
            "postal_code": postal_code,
            "via_type": "",
            "language": language
        }
        context = {"record_card_check": True}
        if create_record_card:
            record_card = self.create_record_card(immediate_response=immediate_response,
                                                  theme_response_channels=self.theme_response_channels)
            data["record_card"] = record_card.pk

        ser = RecordCardResponseSerializer(data=data, context=context)
        assert ser.is_valid() is valid, "Record Card Response serializer fails"
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize("response_channel,address_mobile_email,immediate_response,language,valid", (
            (ResponseChannel.SMS, "987654321", False, "gl", True),
            (ResponseChannel.SMS, "987654321", True, "gl", False),
            (ResponseChannel.SMS, "", False, "gl", False),
            (ResponseChannel.TELEPHONE, "987654321", False, "gl", True),
            (ResponseChannel.TELEPHONE, "", False, "gl", False),
            (ResponseChannel.TELEPHONE, "987654321", True, "gl", False),
            (ResponseChannel.SMS, "987654321", False, "", False),
    ))
    def test_record_card_response_serializer_by_phone(self, response_channel, address_mobile_email, immediate_response,
                                                      language, valid):
        data = {
            "response_channel": response_channel,
            "address_mobile_email": address_mobile_email,
            "number": "",
            "postal_code": "",
            "via_type": "",
            "language": language
        }

        record_card = self.create_record_card(immediate_response=immediate_response,
                                              theme_response_channels=self.theme_response_channels)
        data["record_card"] = record_card.pk
        context = {"record_card_check": True, "record_card": record_card}

        ser = RecordCardResponseSerializer(data=data, context=context)
        assert ser.is_valid() is valid, "Record Card Response serializer fails"
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize("address_mobile_email,immediate_response,language,valid", (
            ("test@test.com", True, "gl", True),
            ("test@test.com", False, "gl", True),
            ("", True, "gl", False),
            ("test@test.com", True, "", False),
    ))
    def test_record_card_response_serializer_by_email(self, address_mobile_email, immediate_response, language, valid):
        load_missing_data_reasons()
        data = {
            "response_channel": ResponseChannel.EMAIL,
            "address_mobile_email": address_mobile_email,
            "number": "",
            "postal_code": "",
            "via_type": "",
            "language": language
        }

        record_card = self.create_record_card(immediate_response=immediate_response,
                                              theme_response_channels=self.theme_response_channels)
        data["record_card"] = record_card.pk
        context = {"record_card_check": True, "record_card": record_card}

        ser = RecordCardResponseSerializer(data=data, context=context)
        assert ser.is_valid() is valid, "Record Card Response serializer fails"
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize(
        "address_mobile_email,number,postal_code,via_type,stair,floor,door,municipality,province,language,valid", (
                ("test", "111", "08009", "carrer", "A", "1", "B", "Barcelona", "Barcelona", "gl", True),
                ("", "111", "08009", "carrer", "A", "1", "B", "Barcelona", "Barcelona", "gl", False),
                ("test", "", "08009", "carrer", "A", "1", "B", "Barcelona", "Barcelona", "gl", True),
                ("test", "111", "", "carrer", "A", "1", "B", "Barcelona", "Barcelona", "gl", False),
                ("test", "111", "08009", "", "A", "1", "B", "Barcelona", "Barcelona", "gl", True),
                ("test", "111", "08009", "carrer", "", "1", "B", "Barcelona", "Barcelona", "gl", True),
                ("test", "111", "08009", "carrer", "A", "", "B", "Barcelona", "Barcelona", "gl", True),
                ("test", "111", "08009", "carrer", "A", "1", "", "Barcelona", "Barcelona", "gl", True),
                ("test", "111", "08009", "carrer", "A", "1", "B", "", "Barcelona", "gl", False),
                ("test", "111", "08009", "carrer", "A", "1", "B", "Barcelona", "", "gl", False),
                ("test", "111", "08009", "carrer", "A", "1", "B", "Barcelona", "Barcelona", "", False),
        ))
    def test_record_card_response_serializer_by_letter(self, address_mobile_email, number, postal_code, via_type, stair,
                                                       floor, door, municipality, province, language, valid):
        load_missing_data_reasons()
        data = {
            "response_channel": ResponseChannel.LETTER,
            "address_mobile_email": address_mobile_email,
            "number": number,
            "postal_code": postal_code,
            "stair": stair,
            "floor": floor,
            "door": door,
            "municipality": municipality,
            "province": province,
            "via_type": via_type,
            "language": language
        }

        record_card = self.create_record_card(theme_response_channels=self.theme_response_channels)
        data["record_card"] = record_card.pk
        context = {"record_card_check": True, "record_card": record_card}

        ser = RecordCardResponseSerializer(data=data, context=context)
        assert ser.is_valid() is valid, "Record Card Response serializer fails"
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize("response_channel,applicant_nd,none_response_channel,valid", (
            (ResponseChannel.LETTER, settings.CITIZEN_ND, True, True),
            (ResponseChannel.LETTER, settings.CITIZEN_ND, False, True),
            (ResponseChannel.LETTER, settings.CITIZEN_NDD, True, True),
            (ResponseChannel.LETTER, settings.CITIZEN_NDD, False, True),
            (ResponseChannel.LETTER, '', True, True),
            (ResponseChannel.LETTER, '', False, True),
            (ResponseChannel.NONE, settings.CITIZEN_ND, True, True),
            (ResponseChannel.NONE, settings.CITIZEN_ND, False, True),
            (ResponseChannel.NONE, settings.CITIZEN_NDD, True, True),
            (ResponseChannel.NONE, settings.CITIZEN_NDD, False, False),
            (ResponseChannel.NONE, '', True, True),
            (ResponseChannel.NONE, '', False, False),
    ))
    def test_applicant_nd(self, response_channel, applicant_nd, none_response_channel, valid):
        load_missing_data_reasons()
        data = {
            "response_channel": response_channel,
            "address_mobile_email": "street",
            "number": "number",
            "postal_code": "07800",
            "stair": "stair",
            "floor": "floor",
            "door": "door",
            "municipality": "municipality",
            "province": "province",
            "via_type": "via_type",
            "language": "gl"
        }

        if applicant_nd:
            citizen = mommy.make(Citizen, user_id="2222", dni=applicant_nd)
        else:
            citizen = mommy.make(Citizen, user_id="2222")
        applicant = mommy.make(Applicant, citizen=citizen, user_id="222")

        theme_response_channels = [ResponseChannel.EMAIL, ResponseChannel.SMS, ResponseChannel.LETTER,
                                   ResponseChannel.IMMEDIATE, ResponseChannel.TELEPHONE]
        if none_response_channel:
            theme_response_channels.append(ResponseChannel.NONE)

        record_card = self.create_record_card(theme_response_channels=theme_response_channels, applicant=applicant)
        data["record_card"] = record_card.pk
        context = {"record_card_check": True, "record_card": record_card}

        ser = RecordCardResponseSerializer(data=data, context=context)
        assert ser.is_valid() is valid, "Record Card Response serializer fails: {}".format(ser.errors)
        assert isinstance(ser.errors, dict)
        if valid:
            response = ser.save()
            if applicant_nd == settings.CITIZEN_ND or response_channel == ResponseChannel.NONE:
                assert response.response_channel_id == ResponseChannel.NONE
            else:
                assert response.response_channel_id == ResponseChannel.LETTER

    @pytest.mark.parametrize("initial_response_channel,send_response,none_response_channel,valid", (
            (ResponseChannel.LETTER, True, True, True),
            (ResponseChannel.LETTER, False, True, True),
            (ResponseChannel.NONE, True, True, False),
            (ResponseChannel.NONE, True, False, False),
            (ResponseChannel.NONE, False, True, True),
            (ResponseChannel.NONE, False, False, True),
    ))
    def test_response_internal_operator(self, initial_response_channel, send_response, none_response_channel, valid):
        load_missing_data_applicant()
        load_missing_data_reasons()
        load_missing_data_input()
        data = {
            "response_channel": initial_response_channel,
            "address_mobile_email": "street",
            "number": "number",
            "postal_code": "07800",
            "stair": "stair",
            "floor": "floor",
            "door": "door",
            "municipality": "municipality",
            "province": "province",
            "via_type": "via_type",
            "language": "gl"
        }

        input_channel = InputChannel.objects.get(pk=InputChannel.ALTRES_CANALS)
        applicant_type = mommy.make(ApplicantType, user_id="2222", send_response=send_response)
        citizen = mommy.make(Citizen, user_id="2222")
        applicant = mommy.make(Applicant, citizen=citizen, user_id="222")

        InternalOperator.objects.create(document=citizen.dni, input_channel=input_channel,
                                        applicant_type=applicant_type)

        theme_response_channels = [ResponseChannel.EMAIL, ResponseChannel.SMS, ResponseChannel.LETTER,
                                   ResponseChannel.IMMEDIATE, ResponseChannel.TELEPHONE]
        if none_response_channel:
            theme_response_channels.append(ResponseChannel.NONE)

        record_card = self.create_record_card(theme_response_channels=theme_response_channels, applicant=applicant,
                                              input_channel=input_channel, applicant_type=applicant_type)
        data["record_card"] = record_card.pk
        context = {"record_card_check": True, "record_card": record_card}

        ser = RecordCardResponseSerializer(data=data, context=context)
        assert ser.is_valid() is valid, "Record Card Response serializer fails"
        assert isinstance(ser.errors, dict)
        if valid and not send_response:
            response = ser.save()
            assert response.response_channel_id == ResponseChannel.NONE

    @pytest.mark.parametrize("language,allow_english_lang,valid", (
            ("gl", True, True),
            ("en", True, True),
            ("gl", False, True),
            ("en", False, False),
    ))
    def test_record_card_response_serializer_language(self, language, allow_english_lang, valid):
        load_missing_data_reasons()
        data = {
            "response_channel": ResponseChannel.EMAIL, "address_mobile_email": "test@test.com", "number": "",
            "postal_code": "", "stair": "", "floor": "", "door": "", "municipality": "", "province": "",
            "via_type": "", "language": language
        }

        element_detail = self.create_element_detail()
        ElementDetailResponseChannel.objects.create(elementdetail=element_detail,
                                                    responsechannel_id=ResponseChannel.EMAIL)
        element_detail.allow_english_lang = allow_english_lang
        element_detail.save()

        record_card = self.create_record_card(element_detail=element_detail)
        data["record_card"] = record_card.pk
        context = {"record_card_check": True, "record_card": record_card}

        ser = RecordCardResponseSerializer(data=data, context=context)
        assert ser.is_valid() is valid, "Record Card Response serializer fails with language"
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize("resp_channel,add_multi_respchannel,valid", (
            (ResponseChannel.LETTER, True, True),
            (ResponseChannel.LETTER, False, False),
            (ResponseChannel.TELEPHONE, True, True),
            (ResponseChannel.TELEPHONE, False, True),
    ))
    def test_record_card_response_serializer_multirecord_respchannel(self, resp_channel, add_multi_respchannel, valid):
        load_missing_data_reasons()
        data = {
            "response_channel": resp_channel,
            "address_mobile_email": "street",
            "number": "number",
            "postal_code": "07800",
            "stair": "stair",
            "floor": "floor",
            "door": "door",
            "municipality": "municipality",
            "province": "province",
            "via_type": "via_type",
            "language": "gl"
        }

        theme_response_channels = [ResponseChannel.NONE, ResponseChannel.IMMEDIATE, ResponseChannel.TELEPHONE]

        record_card = self.create_record_card(immediate_response=False,
                                              theme_response_channels=theme_response_channels)
        data["record_card"] = record_card.pk
        context = {"record_card_check": True, "record_card": record_card}
        multirecord_response_channel = ResponseChannel.LETTER if add_multi_respchannel else None
        ser = RecordCardResponseSerializer(data=data, context=context,
                                           multirecord_response_channel=multirecord_response_channel)
        assert ser.is_valid() is valid, "Record Card Response serializer fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestRecordCardCancelSerializer(CreateRecordCardMixin):

    @pytest.mark.parametrize("reason,comment,valid", (
            (Reason.FALSE_ERRONEOUS_DATA, "Comentari de prova", True),
            ("", "Comentari de prova", False),
            (None, "Comentari de prova", False),
            (Reason.FALSE_ERRONEOUS_DATA, "Com de prova", False),
    ))
    def test_record_card_cancel_serializer(self, reason, comment, valid):
        load_missing_data_reasons()

        data = {
            "reason": reason,
            "comment": comment
        }
        groups = dict_groups()
        first_key = list(groups.keys())[0]
        parent = groups[first_key + 2]

        record_card = self.create_record_card(responsible_profile=parent)
        ser = RecordCardCancelSerializer(data=data, context={"record_card": record_card, "group": parent})
        assert ser.is_valid() is valid, "Record Card Cancel serializer fails"
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize("responsible_profile,cancel_profile,record_state_id,valid", (
            (2, 2, RecordState.PENDING_VALIDATE, False),
            (2, 2, RecordState.EXTERNAL_RETURNED, False),
            (2, 2, RecordState.PENDING_ANSWER, True),
            (2, 2, RecordState.IN_RESOLUTION, True),
            (1, 2, RecordState.IN_RESOLUTION, False),
            (2, 1, RecordState.IN_RESOLUTION, True),
            (6, 1, RecordState.IN_RESOLUTION, True),
            (6, 3, RecordState.IN_RESOLUTION, False),
    ))
    def test_record_card_cancel_serializer_validation_error(self, responsible_profile, cancel_profile, record_state_id,
                                                            valid):
        load_missing_data_reasons()

        data = {
            "reason": Reason.VALIDATION_BY_ERROR,
            "comment": "Comentari de prova"
        }
        responsible_profile -= 1
        cancel_profile -= 1
        cancel_groups = dict_groups()
        first_key = list(cancel_groups.keys())[0]
        record_card = self.create_record_card(record_state_id=record_state_id,
                                              responsible_profile=cancel_groups[first_key + responsible_profile])
        ser = RecordCardCancelSerializer(data=data, context={"record_card": record_card,
                                                             "group": cancel_groups[first_key + cancel_profile]})
        assert ser.is_valid() is valid, "Record Card Cancel by validation by error serializer fails"
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize("responsible_profile,cancel_profile,record_state_id,previous_created_at,valid", (
            (2, 2, RecordState.PENDING_VALIDATE, True, True),
            (2, 2, RecordState.PENDING_VALIDATE, False, False),
            (2, 2, RecordState.PENDING_ANSWER, False, False),
    ))
    def test_record_card_cancel_serializer_expiration(self, responsible_profile, cancel_profile, record_state_id,
                                                      previous_created_at, valid):
        load_missing_data_reasons()

        data = {
            "reason": Reason.EXPIRATION,
            "comment": "Comentari de prova"
        }

        responsible_profile -= 1
        cancel_profile -= 1
        cancel_groups = dict_groups()
        first_key = list(cancel_groups.keys())[0]

        if previous_created_at:
            element_detail = self.create_element_detail(validation_place_days=2)
        else:
            element_detail = self.create_element_detail()

        record_card = self.create_record_card(record_state_id=record_state_id, element_detail=element_detail,
                                              responsible_profile=cancel_groups[first_key + responsible_profile],
                                              previous_created_at=previous_created_at)
        if previous_created_at:
            record_card.created_at = timezone.now() - timedelta(days=12)
            record_card.save()
        ser = RecordCardCancelSerializer(data=data, context={"record_card": record_card,
                                                             "group": cancel_groups[first_key + cancel_profile]})
        assert ser.is_valid() is valid, "Record Card Cancel by expiration serializer fails"
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize("duplicate,repeat,diff_applicant,duplicate_state_id,valid", (
            (False, False, False, None, False),
            (True, False, True, RecordState.IN_RESOLUTION, False),
            (True, False, False, RecordState.IN_RESOLUTION, True),
            (True, False, False, RecordState.CANCELLED, False),
            (False, True, False, RecordState.CANCELLED, False)
    ))
    def test_record_card_cancel_serializer_duplicity_repetition(self, duplicate, repeat, diff_applicant,
                                                                duplicate_state_id, valid):
        load_missing_data_reasons()

        data = {
            "reason": int(Parameter.get_parameter_by_key("DEMANAR_FITXA", 1)),
            "comment": "Comentari de prova"
        }

        groups = dict_groups()
        first_key = list(groups.keys())[0]
        parent = groups[first_key + 1]

        record_card = self.create_record_card(record_state_id=RecordState.IN_RESOLUTION, responsible_profile=parent)
        if not duplicate:
            if repeat:
                data["duplicated_record_card"] = record_card.normalized_record_id
            else:
                data["duplicated_record_card"] = set_reference(RecordCard, "normalized_record_id")
        elif duplicate:
            if diff_applicant:
                citizen = mommy.make(Citizen, user_id="2222")
                applicant = mommy.make(Applicant, user_id="2222", citizen=citizen)
            else:
                applicant = record_card.request.applicant
            duplicate_record_card = self.create_record_card(
                record_state_id=duplicate_state_id, applicant=applicant)
            data["duplicated_record_card"] = duplicate_record_card.normalized_record_id

        ser = RecordCardCancelSerializer(data=data, context={"record_card": record_card, "group": parent})
        assert ser.is_valid() is valid, "Record Card Cancel serializer fails"
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize("reason,duplicated_record_card,valid", (
            (Reason.DUPLICITY_REPETITION, None, False),
            (Reason.VALIDATION_BY_ERROR, "", True),
    ))
    def test_cancel_serializer_duplicity(self, reason, duplicated_record_card, valid):
        load_missing_data_reasons()

        data = {
            "reason": reason,
            "comment": "Comentari de prova",
        }
        if duplicated_record_card is not None:
            data["duplicated_record_card"] = duplicated_record_card

        _, parent, _, _, _, _ = create_groups()
        record_card = self.create_record_card(record_state_id=RecordState.IN_RESOLUTION, responsible_profile=parent)

        ser = RecordCardCancelSerializer(data=data, context={"record_card": record_card, "group": parent})
        assert ser.is_valid() is valid, "Record Card Cancel serializer fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestRecordCardTextResponseSerializer(CreateRecordCardMixin, CreateRecordFileMixin, SetGroupRequestMixin,
                                           SetPermissionMixin):

    @pytest.mark.parametrize("response,send_date,valid", (
            ("Text response test", "2019-05-02", True),
            ("", "2019-05-02", False),
            ("Text response test", "", False),
            ("Text response test", "2019-0502", False),
    ))
    def test_record_card_resolution_serializer(self, response, send_date, valid):
        data = {
            "response": response,
            "send_date": send_date,
            "worked": "t"
        }
        record_card = self.create_record_card(create_record_card_response=True)

        ser = RecordCardTextResponseSerializer(data=data, context={"record_card": record_card})
        assert ser.is_valid() is valid, "RecordCard Text Response serializer fails"
        assert isinstance(ser.errors, dict)

    @pytest.mark.parametrize("response_worked_permission,worked,valid", (
            (True, "t", True),
            (True, "", True),
            (True, "e", False),
            (False, "p", False),
            (False, "", True),
    ))
    def test_response_worked(self, response_worked_permission, worked, valid):
        group, request = self.set_group_request()
        if response_worked_permission:
            self.set_permission(RESP_WORKED, group=group)

        record_card = self.create_record_card(create_record_card_response=True)
        context = {"record_card": record_card, "request": request}

        data = {
            "response": "Text response test",
            "send_date": "2019-05-02",
            "worked": worked
        }

        serializer = RecordCardTextResponseSerializer(data=data, context=context)
        assert serializer.is_valid() is valid
        assert isinstance(serializer.errors, dict)

    @pytest.mark.parametrize("different_record,num_files,valid", ((False, 3, True), (True, 3, False)))
    def test_response_files(self, tmpdir_factory, different_record, num_files, valid):
        group, request = self.set_group_request()
        self.set_permission(RESP_WORKED, group=group)

        record_card = self.create_record_card(create_record_card_response=True, create_worflow=True)
        context = {"record_card": record_card, "request": request}
        data = {"response": "Text response test", "send_date": "2019-05-02", "worked": "t", "record_files": []}

        for num_file in range(num_files):
            if different_record:
                record_card = self.create_record_card(create_record_card_response=True)
            data["record_files"].append({"record_file": self.create_file(tmpdir_factory, record_card, num_file).pk})

        serializer = RecordCardTextResponseSerializer(data=data, context=context)
        assert serializer.is_valid() is valid
        assert isinstance(serializer.errors, dict)
        if valid is True:
            response_text = serializer.save()
            assert response_text.recordcardtextresponsefiles_set.filter(enabled=True).count() == num_files

    @pytest.mark.parametrize("response_channel_id,valid", (
            (ResponseChannel.EMAIL, True), (ResponseChannel.SMS, False)
    ))
    def test_response_files_response_channel(self, tmpdir_factory, response_channel_id, valid):
        group, request = self.set_group_request()
        self.set_permission(RESP_WORKED, group=group)

        record_card = self.create_record_card(create_record_card_response=True, create_worflow=True)
        record_card.recordcardresponse.response_channel_id = response_channel_id
        record_card.recordcardresponse.save()
        context = {"record_card": record_card, "request": request}
        data = {"response": "Text response test", "send_date": "2019-05-02", "worked": "t", "record_files": []}
        data["record_files"].append({"record_file": self.create_file(tmpdir_factory, record_card, 0).pk})

        serializer = RecordCardTextResponseSerializer(data=data, context=context)
        assert serializer.is_valid() is valid
        assert isinstance(serializer.errors, dict)


@pytest.mark.django_db
class TestRecordCardBlockSerializer(FieldsTestSerializerMixin, CreateRecordCardMixin):
    serializer_class = RecordCardBlockSerializer
    data_keys = ["user_id", "record_card", "expire_time"]

    def get_instance(self):
        record_card = self.create_record_card()
        return mommy.make(RecordCardBlock, user_id="22222", record_card=record_card)


class TestRecordCardTraceabilitySerializer:

    @pytest.mark.parametrize(
        "record_comment_error,state_history_error,worflow_comment_error,reasignation_error,valid", (
                (False, False, False, False, True),
                (True, False, False, False, False),
                (False, True, False, False, False),
                (False, False, True, False, False),
                (False, False, False, True, False)
        ))
    def test_record_card_traceability_serializer(self, record_comment_error, state_history_error,
                                                 worflow_comment_error, reasignation_error, valid):
        record_comment = {
            "type": "record_comment",
            "created_at": datetime.now(),
            "user_id": "aaaaaaaaaaaaa",
            "group_name": None,
            "reason": 200,
            "comment": "" if record_comment_error else "aaaaaaaaaaaaaaaaaaaaaa"
        }

        state_history = {
            "type": "state_history",
            "created_at": datetime.now(),
            "user_id": "test",
            "group_name": None,
            "previous_state": 4,
            "next_state": None if state_history_error else 7,
            "automatic": False
        }

        worflow_comment = {
            "type": "worflow_comment",
            "created_at": datetime.now(),
            "user_id": "test",
            "group_name": None,
            "comment": "Test comment resolution",
            "task": "" if worflow_comment_error else "Resolution"
        }

        reasignation = {
            "type": "worflow_comment",
            "created_at": datetime.now(),
            "user_id": "test",
            "group_name": None,
            "reason": 200,
            "comment": "Test comment resolution",
            "previous_responsible": "" if reasignation_error else "GRP1",
            "next_responsible": "GRP2"
        }

        data_list = [record_comment, state_history, worflow_comment, reasignation]

        ser = RecordCardTraceabilitySerializer(data=data_list, many=True)
        assert ser.is_valid() is valid
        for object_error in ser.errors:
            assert isinstance(object_error, dict)


@pytest.mark.django_db
class TestRecordCardReasignationSerializer(SetGroupRequestMixin, CreateRecordCardMixin):

    @pytest.mark.parametrize("record_card,next_responsible,reason_id,comment,valid", (
            (True, True, Reason.COORDINATOR_EVALUATION, "test", True),
            (False, True, Reason.COORDINATOR_EVALUATION, "test", False),
            (False, True, Reason.COORDINATOR_EVALUATION, "test", False),
            (True, False, Reason.COORDINATOR_EVALUATION, "test", False),
            (True, True, None, "test", False),
            (True, True, Reason.COORDINATOR_EVALUATION, "", False),

    ))
    def test_record_card_reasignation_serializer(self, record_card, next_responsible, reason_id, comment, valid):
        load_missing_data_reasons()
        _, parent, first_soon, _, _, _ = create_groups()
        conversation_number = 3
        if record_card:
            db_record_card = self.create_record_card(validated_reassignable=True, responsible_profile=parent)
            record_card_pk = db_record_card.pk
            for _ in range(conversation_number):
                mommy.make(Conversation, user_id="2222", record_card=db_record_card, is_opened=True)
        else:
            db_record_card = None
            record_card_pk = None

        next_responsible_pk = first_soon.pk if next_responsible else None
        data = {
            "record_card": record_card_pk,
            "next_responsible_profile": next_responsible_pk,
            "reason": reason_id,
            "comment": comment

        }
        _, request = self.set_group_request(group=parent)
        ser = RecordCardReasignationSerializer(data=data, context={"request": request})
        assert ser.is_valid() is valid
        assert isinstance(ser.errors, dict)
        if valid is True:
            with patch("profiles.tasks.send_allocated_notification.delay") as mock_delay:
                ser.save()
                self.assert_reasignation_created(db_record_card, db_record_card.responsible_profile.pk,
                                                 next_responsible_pk, reason_id, comment)
                assert Conversation.objects.filter(record_card=db_record_card).count() == conversation_number
                assert Conversation.objects.filter(
                    record_card=db_record_card, is_opened=False).count() == conversation_number
                mock_delay.assert_called_once()

    @pytest.mark.parametrize("same_responsibles,set_allowed_reassignations,validated_reassignable,valid", (
            (False, True, True, True),
            (True, True, True, False),
            (False, False, True, False),
            (False, True, False, True),
    ))
    def test_validate_serializer(self, same_responsibles, set_allowed_reassignations, validated_reassignable, valid):
        load_missing_data_reasons()
        _, parent, first_soon, _, _, noambit_soon = create_groups()
        record_card = self.create_record_card(validated_reassignable=validated_reassignable, responsible_profile=parent)
        group = record_card.responsible_profile

        if same_responsibles:
            next_responsible = group
        else:
            next_responsible = first_soon if set_allowed_reassignations else noambit_soon

        data = {
            "record_card": record_card.pk,
            "next_responsible_profile": next_responsible.pk,
            "reason": Reason.COORDINATOR_EVALUATION,
            "comment": "test"
        }

        _, request = self.set_group_request(group=group)
        ser = RecordCardReasignationSerializer(data=data, context={"request": request})
        assert ser.is_valid() is valid
        assert isinstance(ser.errors, dict)
        if valid is True:
            with patch("profiles.tasks.send_allocated_notification.delay") as mock_delay:
                ser.save()
                self.assert_reasignation_created(record_card, group.pk, next_responsible.pk,
                                                 Reason.COORDINATOR_EVALUATION, "test")
                mock_delay.assert_called_once()

    @staticmethod
    def assert_reasignation_created(record_card, previous_responsible_pk, next_responsible_pk, reason_id, comment):
        record_card = RecordCard.objects.get(pk=record_card.pk)
        assert record_card.reasigned is True
        assert record_card.alarm is True
        assert not record_card.user_displayed
        assert record_card.responsible_profile_id == next_responsible_pk
        assert RecordCardReasignation.objects.get(record_card=record_card, reason_id=reason_id, comment=comment,
                                                  previous_responsible_profile_id=previous_responsible_pk,
                                                  next_responsible_profile_id=next_responsible_pk)

    @pytest.mark.parametrize("allow_derivation,theme_allow_derivation,valid", (
            (True, True, True),
            (False, True, True),
            (True, False, False),
            (False, False, True),
    ))
    def test_reasignation_serializer_allow_multiderivation(self, allow_derivation, theme_allow_derivation, valid):
        load_missing_data_reasons()
        _, parent, first_soon, _, _, _ = create_groups()
        element_detail = self.create_element_detail(allow_multiderivation_on_reassignment=theme_allow_derivation)
        record_card = self.create_record_card(validated_reassignable=True, responsible_profile=parent,
                                              element_detail=element_detail)

        data = {
            "record_card": record_card.pk,
            "next_responsible_profile": first_soon.pk,
            "reason": Reason.COORDINATOR_EVALUATION,
            "comment": "test comment",
            "allow_multiderivation": allow_derivation
        }
        _, request = self.set_group_request(group=parent)
        ser = RecordCardReasignationSerializer(data=data, context={"request": request})
        assert ser.is_valid() is valid
        assert isinstance(ser.errors, dict)
        if valid is True:
            ser.save()
            record_card = RecordCard.objects.get(pk=record_card.pk)
            assert record_card.allow_multiderivation is allow_derivation


@pytest.mark.django_db
class TestRecordCardReasignableSerializer(CreateRecordCardMixin):

    @pytest.mark.parametrize("reassignment_not_allowed", (True, False,))
    def test_recordcard_reasignable_serializer(self, reassignment_not_allowed):
        load_missing_data_process()
        record_card = self.create_record_card(record_state_id=RecordState.PENDING_VALIDATE,
                                              process_pk=Process.EXTERNAL_PROCESSING)
        ser = RecordCardReasignableSerializer(data={"id": record_card.pk,
                                                    "reassignment_not_allowed": reassignment_not_allowed})
        assert ser.is_valid() is True, "RecordCard Reasignable serializer fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestRecordCardMultiComplaintListSerializer(FieldsTestSerializerMixin, CreateRecordCardMixin):
    serializer_class = RecordCardMultiRecordstListSerializer
    data_keys = ["id", "normalized_record_id", "multirecord_from", "created_at", "element_detail", "record_state",
                 "description"]

    def get_instance(self):
        return self.create_record_card()


@pytest.mark.django_db
class TestRecordCardCheckSerializer(FieldsTestSerializerMixin, CreateRecordCardMixin):
    serializer_class = RecordCardCheckSerializer
    data_keys = ["can_confirm", "reason", "next_state", "next_group", "different_ambit"]

    def get_instance(self):
        return {
            "can_confirm": True,
            "reason": "Test reason",
            "next_state": RecordState.objects.get(pk=RecordState.IN_PLANING),
            "next_group": mommy.make(Group, user_id="2222", profile_ctrl_user_id="2222"),
            "different_ambit": False
        }


@pytest.mark.django_db
class TestRecordCardValidateCheckSerializer(FieldsTestSerializerMixin, CreateRecordCardMixin):
    serializer_class = RecordCardValidateCheckSerializer
    data_keys = [
        "can_confirm", "reason", "next_state", "next_group", "different_ambit", "possible_similar",
        "send_external"
    ]

    def get_instance(self):
        return {
            "can_confirm": True,
            "reason": "Test reason",
            "next_state": RecordState.objects.get(pk=RecordState.IN_PLANING),
            "next_group": mommy.make(Group, user_id="2222", profile_ctrl_user_id="2222"),
            "different_ambit": False,
            "possible_similar": [self.create_record_card()]
        }


@pytest.mark.django_db
class TestRecordCardClaimCheckSerializer(FieldsTestSerializerMixin, CreateRecordCardMixin):
    serializer_class = RecordCardClaimCheckSerializer
    data_keys = ["can_confirm", "reason", "next_state", "next_group", "different_ambit", "claim_type",
                 "reason_comment_id"]

    def get_instance(self):
        return {
            "can_confirm": True,
            "reason": "Test reason",
            "next_state": RecordState.objects.get(pk=RecordState.IN_PLANING),
            "next_group": mommy.make(Group, user_id="2222", profile_ctrl_user_id="2222"),
            "different_ambit": False,
            "claim_type": "comment",
            "reason_comment_id": Reason.CLAIM_CITIZEN_REQUEST
        }


@pytest.mark.django_db
class TestRecordChunkedFileSerializer(SetGroupRequestMixin, CreateRecordFileMixin, CreateRecordCardMixin):

    @pytest.mark.parametrize(
        "create_record,responsible_group,group_manage,creation_group,record_state_id,filename,valid", (
                (True, 2, 2, 3, RecordState.PENDING_VALIDATE, "img.png", True),
                (True, 2, 5, 5, RecordState.PENDING_VALIDATE, "img.png", True),
                (True, 2, 5, 5, RecordState.IN_PLANING, "img.png", False),
                (True, 2, 1, 3, RecordState.PENDING_VALIDATE, "img.png", True),
                (True, 2, 1, 3, RecordState.IN_RESOLUTION, "img.png", True),
                (True, 2, 2, 3, RecordState.PENDING_VALIDATE, "", False),
                (False, 2, 2, 3, RecordState.PENDING_VALIDATE, "img.png", False),
        ))
    def test_record_chunkedfile_serializer(self, image_file, create_record, responsible_group, group_manage,
                                           creation_group, record_state_id, filename, valid):
        load_missing_data()
        groups = dict_groups()
        responsible_group -= 1
        creation_group -= 1
        group_manage -= 1
        first_key = list(groups.keys())[0]
        if create_record:
            record_card = self.create_record_card(record_state_id=record_state_id,
                                                  responsible_profile=groups[first_key + responsible_group],
                                                  creation_group=groups[first_key + creation_group])
        else:
            record_card = None
        group = groups[first_key + group_manage]
        _, request = self.set_group_request(group=group)
        if group == Group.get_dair_group():
            self.set_group_permissions('AAA', group, [ADMIN])

        image_base64 = base64.b64encode(image_file.tobytes())
        chunk_size = 64 * 2 ** 10  # 65536 bytes
        data = {
            "record_card_id": record_card.pk if record_card else None,
            "filename": filename,
            "file": ContentFile(image_base64[:chunk_size], name=filename),
            "file_type": RecordFile.CREATE
        }
        ser = RecordChunkedFileSerializer(data=data, context={"request": request})
        assert ser.is_valid() is valid

    @pytest.mark.parametrize("files_number,valid", ((0, True), (3, True), (5, False), (10, False)))
    def test_record_number_files(self, image_file, tmpdir_factory, files_number, valid):
        dair, _, _, _, _, _ = create_groups()
        record_card = self.create_record_card(responsible_profile=dair, creation_group=dair)
        _, request = self.set_group_request(group=dair)
        image_base64 = base64.b64encode(image_file.tobytes())
        chunk_size = 64 * 2 ** 10  # 65536 bytes
        data = {
            "record_card_id": record_card.pk,
            "filename": "img.png",
            "file": ContentFile(image_base64[:chunk_size], name="img.png"),
            "file_type": RecordFile.CREATE
        }
        [self.create_file(tmpdir_factory, record_card, file_number) for file_number in range(files_number)]

        ser = RecordChunkedFileSerializer(data=data, context={"request": request})
        assert ser.is_valid() is valid

    @pytest.mark.parametrize("file_type,valid", (
            (RecordFile.CREATE, True),
            (RecordFile.DETAIL, True),
            (RecordFile.COMMUNICATIONS, True),
            (RecordFile.WEB, True),
            (10, False)
    ))
    def test_file_type(self, image_file, file_type, valid):
        dair, _, _, _, _, _ = create_groups()
        record_card = self.create_record_card(responsible_profile=dair, creation_group=dair)
        _, request = self.set_group_request(group=dair)
        image_base64 = base64.b64encode(image_file.tobytes())
        chunk_size = 64 * 2 ** 10  # 65536 bytes
        data = {
            "record_card_id": record_card.pk,
            "filename": "img.png",
            "file": ContentFile(image_base64[:chunk_size], name="img.png"),
            "file_type": file_type
        }

        ser = RecordChunkedFileSerializer(data=data, context={"request": request})
        assert ser.is_valid() is valid

    @pytest.mark.parametrize("remove_png_from_allowed_extensions,valid", ((True, False), (False, True)))
    def test_file_extension(self, image_file, remove_png_from_allowed_extensions, valid):
        if remove_png_from_allowed_extensions:
            if not Parameter.objects.filter(parameter="EXTENSIONS_PERMESES_FITXERS"):
                parameter = Parameter(parameter="EXTENSIONS_PERMESES_FITXERS")
            else:
                parameter = Parameter.objects.get(parameter="EXTENSIONS_PERMESES_FITXERS")
            parameter.valor = "jpg,jpeg,pdf,docx,xls,odt,xlsx"
            parameter.save()

        dair, _, _, _, _, _ = create_groups()
        record_card = self.create_record_card(responsible_profile=dair, creation_group=dair)
        _, request = self.set_group_request(group=dair)
        image_base64 = base64.b64encode(image_file.tobytes())
        chunk_size = 64 * 2 ** 10  # 65536 bytes
        data = {
            "record_card_id": record_card.pk,
            "filename": "img.png",
            "file": ContentFile(image_base64[:chunk_size], name="img.png"),
            "file_type": RecordFile.CREATE
        }

        ser = RecordChunkedFileSerializer(data=data, context={"request": request})
        assert ser.is_valid() is valid


@pytest.mark.django_db
class TestWorkflowSerializer(CreateRecordCardMixin):

    def test_worklow_serializer(self):
        load_missing_data_process()
        record_card = self.create_record_card(record_state_id=RecordState.PENDING_VALIDATE,
                                              process_pk=Process.EXTERNAL_PROCESSING)
        next_state_code = record_card.next_step_code
        workflow = Workflow.objects.create(main_record_card=record_card, state_id=next_state_code)
        record_card.workflow = workflow

        record_card.record_state_id = next_state_code
        record_card.save()

        data = {
            "id": workflow.pk,
            "main_record_card": record_card.pk,
            "state": workflow.state.pk,
            "close_date": workflow.close_date,
            "visual_user": workflow.visual_user,
            "element_detail_modified": workflow.element_detail_modified,
            "record_cards": [],
            "comments": []
        }
        for rec in workflow.recordcard_set.all():
            data["record_cards"].append(RecordCardShortListSerializer(instance=rec).data)

        ser = WorkflowSerializer(data=data)
        assert ser.is_valid() is True, "Workflow serializer fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestWorkflowPlanSerializer(CreateRecordCardMixin):

    @pytest.mark.parametrize("responsible_profile,start_date_process,comment,action_required,valid", (
            ("test", "2019-05-09", "Comentari de prova", False, True),
            ("test", "2019-05-09", "test test", False, True),
            ("test", "2019-05-09", "test test", True, True),
            ("", "2019-05-09", "Comentari de prova", False, True),

            ("test", "", "test test", True, False),
            ("test", None, "test test", True, True),

            ("test", "2019-05-09", "test", True, False),
            ("test", "2019-05-09", "tes test", True, False),
            ("test", "2019-05-09", "tes tes", True, False),
            ("test", "2019-05-09", "", True, False),
    ))
    def test_workflow_plan_serializer(self, responsible_profile, start_date_process, comment, action_required, valid):
        data = {
            "comment": comment
        }

        if responsible_profile:
            data["responsible_profile"] = responsible_profile
        if start_date_process or isinstance(start_date_process, str):
            data["start_date_process"] = start_date_process

        if action_required:
            data["action_required"] = action_required

        record_card = self.create_record_card()
        ser = WorkflowPlanSerializer(data=data, context={"record_card": record_card})
        assert ser.is_valid() is valid, "Workflow Plan serializer fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestWorkflowPlanReadSerializer(CreateRecordCardMixin, FieldsTestSerializerMixin):
    serializer_class = WorkflowPlanReadSerializer
    data_keys = ["responsible_profile", "start_date_process", "action_required"]

    def get_instance(self):
        record_card = self.create_record_card()
        workflow = Workflow.objects.create(main_record_card=record_card, state_id=record_card.record_state_id,
                                           user_id="222")
        record_card.workflow = workflow
        record_card.save()
        return mommy.make(WorkflowPlan, workflow=workflow)


@pytest.mark.django_db
class TestWorkflowResoluteSerializer(CreateRecordCardMixin):

    @pytest.mark.parametrize(
        "service_person_incharge,resolution_type,resolution_date,requires_appointment,"
        "resolution_comment,valid", (
                ("test", 1, "2019-02-02 00:00", False, "test comment", True),
                ("test", 1, "2019-02-02 00:00", False, "tes commen", False),
                ("test", 2, "2019-02-02", False, "test come", False),
                ("test", 7, None, False, "test comment", True),
                ("", None, "2019-02-02 00:00", False, "test come", False),
                ("", 4, "2019-02-02 18:00", False, "test come", True),
                ("test", 5, "2019-02-02 18:00", True, "test comment", True),
                ("Test", 6, "2019-02-02", True, "test comment", False),
                ("", 6, "2019-02-02 18:00", True, "test comment", False),
                ("test", 1, None, True, "test comment", False),
                ("", 2, None, True, "test comment", False),
        )
    )
    def test_workflow_resolution_serializer(self, service_person_incharge, resolution_type, resolution_date,
                                            requires_appointment, resolution_comment, valid):
        if resolution_type:
            mommy.make(ResolutionType, id=resolution_type, user_id="2222")
        data = {
            "service_person_incharge": service_person_incharge,
            "resolution_type": resolution_type,
            "resolution_date": resolution_date,
            "resolution_comment": resolution_comment,
        }
        record_card = self.create_record_card(requires_appointment=requires_appointment)

        ser = WorkflowResoluteSerializer(data=data, context={"record_card": record_card})
        assert ser.is_valid() is valid, "Workflow Resolution serializer fails"
        assert isinstance(ser.errors, dict)


@pytest.mark.django_db
class TestWorkflowResolutionSerializer(CreateRecordCardMixin, FieldsTestSerializerMixin):
    serializer_class = WorkflowResolutionSerializer
    data_keys = ["service_person_incharge", "resolution_type", "resolution_date", "is_appointment", "can_delete"]

    def get_instance(self):
        record_card = self.create_record_card()
        workflow = Workflow.objects.create(main_record_card=record_card, state_id=record_card.record_state_id,
                                           user_id="222")
        record_card.workflow = workflow
        record_card.save()
        resolution_type = mommy.make(ResolutionType, user_id="2222")
        return mommy.make(WorkflowResolution, workflow=workflow, resolution_type=resolution_type)


@pytest.mark.django_db
class TestRecordCardShortNotificationsSerializer(CreateRecordCardMixin, FieldsTestSerializerMixin):
    serializer_class = RecordCardShortNotificationsSerializer
    data_keys = ["id", "description", "normalized_record_id"]

    def get_instance(self):
        return self.create_record_card()


@pytest.mark.django_db
class TestRecordCardApplicantListSerializer(CreateRecordCardMixin, FieldsTestSerializerMixin):
    serializer_class = RecordCardApplicantListSerializer
    data_keys = ["id", "created_at", "normalized_record_id", "element_detail", "description"]

    def get_instance(self):
        return self.create_record_card()


@pytest.mark.django_db
class TestClaimShortSerializer(CreateRecordCardMixin, FieldsTestSerializerMixin):
    serializer_class = ClaimShortSerializer
    data_keys = ["id", "user_id", "created_at", "updated_at", "normalized_record_id"]

    def get_instance(self):
        return self.create_record_card()


class TestClaimDescriptionSerializer:

    @pytest.mark.parametrize("description,valid", (
            ("description", True),
            ("", False),
            (None, False),
    ))
    def test_claim_description_serializer(self, description, valid):
        data = {}
        if description or description == "":
            data["description"] = description
        ser = ClaimDescriptionSerializer(data=data)
        assert ser.is_valid() is valid
        assert isinstance(ser.errors, dict)


class TestInternalOperatorSerializer(UniqueValidityTest):
    serializer_class = InternalOperatorSerializer
    unique_field = "document"

    def given_fields(self):
        return ["document"]

    def get_extra_data(self):
        return {"applicant_type_id": ApplicantType.CIUTADA, "input_channel_id": InputChannel.ALTRES_CANALS}

    @pytest.mark.parametrize("applicant_type_id,input_channel_id,document,valid", (
            (ApplicantType.CIUTADA, InputChannel.ALTRES_CANALS, "45877412I", True),
            (None, InputChannel.ALTRES_CANALS, "45877412I", False),
            (ApplicantType.CIUTADA, None, "45877412I", False),
            (ApplicantType.CIUTADA, InputChannel.ALTRES_CANALS, None, False),
    ))
    def test_serializer(self, applicant_type_id, input_channel_id, document, valid):
        load_missing_data_input()
        load_missing_data_applicant()
        data = {
            "applicant_type_id": applicant_type_id,
            "input_channel_id": input_channel_id,
        }
        if document:
            data["document"] = document

        ser = InternalOperatorSerializer(data=data)
        assert ser.is_valid() is valid
        assert isinstance(ser.errors, dict)

    def should_have_all_fields_as_errors(self, ser, fields):
        if "non_field_errors" not in ser.errors:
            for field in fields:
                assert field in ser.errors, "All fields should be invalid"

    @pytest.mark.parametrize("description,existent,valid", (
        ("Aaaa", None, True),
        ("Aaaa", "Aaaa", False),
        ("Aaaa", "AaaA", False),
        ("Aaaa", "AaaAaaa", True),
    ))
    def test_serializer_unique_description(self, description, existent, valid):
        load_missing_data_input()
        load_missing_data_applicant()
        super().test_serializer_unique_description(description, existent, valid)


@pytest.mark.django_db
class TestRecordCardTextResponseFilesSerializer(CreateRecordCardMixin, CreateRecordFileMixin):

    @pytest.mark.parametrize("add_file,valid", ((True, True), (False, False)))
    def test_record_card_text_response_files_serializer(self, tmpdir_factory, add_file, valid):
        data = {}
        if add_file:
            record_card = self.create_record_card()
            data["record_file"] = self.create_file(tmpdir_factory, record_card, 1).pk

        ser = RecordCardTextResponseFilesSerializer(data=data)
        assert ser.is_valid() is valid, "RecordCard Text Response files serializer fails"
        assert isinstance(ser.errors, dict)
