import base64
import random
import string
import uuid
from copy import deepcopy
from datetime import timedelta, datetime
import pytest

from django.conf import settings
from django.core import mail
from django.core.files.base import ContentFile
from django.dispatch import Signal
from django.http import HttpRequest
from django.utils import timezone
from django.utils.functional import cached_property
from mock import Mock, patch, PropertyMock

from model_mommy import mommy
from rest_framework.status import (HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST,
                                   HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT)

from ariadna.models import Ariadna, AriadnaRecord
from communications.models import Conversation, ConversationGroup, Message
from features.models import Feature
from iris_masters.models import (ResponseChannel, InputChannel, MediaType, ApplicantType, Application, ResolutionType,
                                 CommunicationMedia, RecordState, Process, Reason, District, Support, Parameter)
from main.open_api.tests.base import (OpenAPIResourceListMixin, BaseOpenAPITest, BaseOpenAPICRUResourceTest,
                                      DictListGetMixin, UpdatePatchMixin, OpenAPIResourceCreateMixin,
                                      OpenAPIRetrieveMixin, PostOperationMixin, OpenAPIResoureceDeleteMixin,
                                      SoftDeleteCheckMixin, BaseOpenAPIResourceTest, CreateOperationMixin,
                                      OpenAPIResourceExcelExportMixin, PreparePathIDMixin, RemovePermissionCheckerMixin,
                                      PutOperation)
from main.test.mixins import AdminUserMixin
from main.utils import GALICIAN, get_user_traceability_id
from profiles.models import Group, UserGroup, Profile, Permission, ProfilePermissions, GroupProfiles, GroupReassignation
from profiles.permission_registry import ADMIN_GROUP
from profiles.tests.utils import create_groups, dict_groups
from record_cards.models import (Ubication, Citizen, Applicant, RecordCard, Comment, Workflow,
                                 WorkflowComment, RecordCardTextResponse, RecordCardBlock, RecordCardStateHistory,
                                 RecordCardReasignation, WorkflowPlan, WorkflowResolution, RecordCardFeatures,
                                 RecordFile, ApplicantResponse, MonthIndicator, InternalOperator, RecordCardAudit)
from record_cards.permissions import (CREATE, NO_REASIGNABLE, RESP_CHANNEL_UPDATE, MAYORSHIP, THEME_CHANGE, RESP_WORKED,
                                      RECARD_PENDVALIDATE, RECARD_MYTASKS, RECARD_SEARCH_NOFILTERS, RECARD_REASIGN,
                                      RECARD_CLAIM, RECARD_PLAN_RESOL, RECARD_ANSWER, RECARD_SAVE_ANSWER,
                                      RECARD_CLOSED_FILES, RECARD_THEME_CHANGE_AREA, CITIZENS_CREATE,
                                      CITIZENS_DELETE, RECARD_VALIDATE_OUTAMBIT, RECARD_MULTIRECORD, RECARD_CHARTS,
                                      RECARD_REASSIGN_OUTSIDE)
from record_cards.record_actions.alarms import RecordCardAlarms
from record_cards.record_actions.external_validators import DummyExternalValidator
from record_cards.record_actions.normalized_reference import set_reference
from record_cards.serializers import RecordCardSerializer
from record_cards.tests.utils import (CreateRecordCardMixin, CreateDerivationsMixin, FeaturesMixin, SetUserGroupMixin,
                                      CreateRecordFileMixin, SetPermissionMixin, RecordUpdateMixin,
                                      SetRecordCardCreateThemeNoVisiblePermissonMixin)
from record_cards.views import COPY_FILES_FROM_PARAM
from themes.models import (ElementDetailFeature, DerivationDirect, ElementDetailResponseChannel,
                           GroupProfileElementDetail, Area, Element, DerivationDistrict)
from iris_masters.tests.utils import load_missing_data_districts


class TestUbicationList(OpenAPIResourceListMixin, BaseOpenAPITest):
    path = "/record_cards/ubications/"
    base_api_path = "/services/iris/api"

    def given_an_object(self):
        return mommy.make(Ubication, enabled=True, user_id="222")


class CitizenAdminPermissionMixin(SetUserGroupMixin, SetPermissionMixin):

    def add_citizen_permission(self, permission, citizen_nd=False):
        if not hasattr(self.user, "usergroup"):
            group = mommy.make(Group, user_id="222", profile_ctrl_user_id="22222", citizen_nd=citizen_nd)
            self.set_usergroup(group)
        else:
            group = self.user.usergroup.group
        self.set_permission(permission, group)

    def add_citizen_create_permission(self, citizen_nd=False):
        self.add_citizen_permission(CITIZENS_CREATE, citizen_nd=citizen_nd)

    def add_citizen_delete_permission(self, citizen_nd=False):
        self.add_citizen_permission(CITIZENS_DELETE, citizen_nd=citizen_nd)

    @pytest.mark.parametrize("object_number", (0, 1, 10))
    def test_list(self, object_number):
        self.add_citizen_create_permission()
        return super().test_list(object_number)

    def test_create_valid(self):
        self.add_citizen_create_permission()
        super().test_create_valid()

    def test_create_invalid(self):
        self.add_citizen_create_permission()
        super().test_create_invalid()

    def test_retrieve(self):
        self.add_citizen_create_permission()
        super().test_retrieve()

    def test_update_put(self):
        self.add_citizen_create_permission()
        super().test_update_put()

    def test_update_patch(self):
        self.add_citizen_create_permission()
        super().test_update_patch()

    def test_delete(self):
        self.add_citizen_create_permission()
        self.add_citizen_delete_permission()
        obj = self.given_an_object()
        url_params = {self.path_pk_param_name: obj[self.lookup_field]}
        response = self.delete(force_params=url_params)
        self.should_delete(response, url_params)

    @pytest.mark.parametrize("has_permission,expected_response", (
        (True, HTTP_201_CREATED), (False, HTTP_403_FORBIDDEN)
    ))
    def test_create_permission(self, has_permission, expected_response):
        if has_permission:
            self.add_citizen_create_permission()
        rq_data = self.given_create_rq_data()
        self.when_is_authenticated()
        response = self.create(rq_data)
        assert response.status_code == expected_response

    @pytest.mark.parametrize("has_permission,expected_response", (
        (True, HTTP_204_NO_CONTENT), (False, HTTP_403_FORBIDDEN)
    ))
    def test_delete_permission(self, has_permission, expected_response):
        self.add_citizen_create_permission()
        if has_permission:
            self.add_citizen_delete_permission()
        obj = self.given_an_object()
        url_params = {self.path_pk_param_name: obj[self.lookup_field]}
        response = self.delete(force_params=url_params)
        assert response.status_code == expected_response


class TestCitizen(CitizenAdminPermissionMixin, BaseOpenAPIResourceTest):
    path = "/record_cards/citizens/"
    base_api_path = "/services/iris/api"

    def given_an_object(self):
        load_missing_data_districts()
        self.add_citizen_create_permission()
        return super().given_an_object()

    def get_default_data(self):
        load_missing_data_districts()
        return {
            "name": "Test name",
            "first_surname": "Test surname",
            "dni": self.generate_random_dni(),
            "birth_year": 1950,
            "mib_code": 5478,
            "district": District.CIUTAT_VELLA,
            "language": GALICIAN,
            "sex": Citizen.MALE
        }

    def given_create_rq_data(self):
        load_missing_data_districts()
        return {
            "name": "Test name",
            "first_surname": "Test surname",
            "dni": self.generate_random_dni(),
            "birth_year": 1950,
            "mib_code": 5478,
            "district": District.CIUTAT_VELLA,
            "language": GALICIAN,
            "sex": Citizen.MALE
        }

    def when_data_is_invalid(self, data):
        data["birt_year"] = 1550
        data["dni"] = ""

    def given_a_complete_update(self, obj):
        """
        :param obj: Object that will be updated.
        :return: Dictionary with attrs for creating a partial update on a given obj
        """
        obj["dni"] = self.generate_random_dni()
        return obj

    @staticmethod
    def generate_random_dni():
        return "{}{}".format(random.randint(40000000, 50000000), random.choice(string.ascii_uppercase))

    @pytest.mark.parametrize("dni,citizen_nd,expected_response", (
        ("43968167X", True, HTTP_201_CREATED),
        ("43968167X", False, HTTP_201_CREATED),
        ("ND", True, HTTP_201_CREATED),
        ("ND", False, HTTP_400_BAD_REQUEST),
    ))
    def test_create_citizen_nd(self, dni, citizen_nd, expected_response):
        rq_data = self.given_create_rq_data()
        rq_data["dni"] = dni
        self.add_citizen_create_permission(citizen_nd=citizen_nd)
        self.when_is_authenticated()
        response = self.create(rq_data)
        assert response.status_code == expected_response


class TestSocialEntity(CitizenAdminPermissionMixin, BaseOpenAPIResourceTest):
    path = "/record_cards/social_entities/"
    base_api_path = "/services/iris/api"

    def get_default_data(self):
        load_missing_data_districts()
        return {
            "social_reason": "Ajuntament",
            "contact": "Ajuntament",
            "cif": self.generate_cif(),
            "mib_code": 54784,
            "district": District.CIUTAT_VELLA,
            "language": GALICIAN
        }

    def given_create_rq_data(self):
        load_missing_data_districts()
        return {
            "social_reason": "Ajuntament",
            "contact": "Ajuntament",
            "cif": self.generate_cif(),
            "mib_code": 54784,
            "district": District.CIUTAT_VELLA,
            "language": GALICIAN
        }

    def given_a_complete_update(self, obj):
        """
        :param obj: Object that will be updated.
        :return: Dictionary with attrs for creating a partial update on a given obj
        """
        obj["cif"] = self.generate_cif()
        return obj

    def when_data_is_invalid(self, data):
        data["cif"] = ""

    @staticmethod
    def generate_cif():
        return "{}{}".format(random.choice(string.ascii_uppercase), random.randint(0, 100000000))


class TestApplicant(CitizenAdminPermissionMixin, OpenAPIResourceExcelExportMixin, BaseOpenAPIResourceTest):
    path = "/record_cards/applicants/"
    base_api_path = "/services/iris/api"

    def given_an_object(self):
        self.add_citizen_create_permission()
        return super().given_an_object()

    def get_default_data(self):
        return {
            "flag_ca": True,
            "user_id": "2222",
            "citizen": self.get_citizen()
        }

    def given_create_rq_data(self):
        return {
            "flag_ca": True,
            "user_id": "2222",
            "citizen": self.get_citizen()
        }

    def when_data_is_invalid(self, data):
        load_missing_data_districts()
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
            "language": GALICIAN
        }

    def given_a_complete_update(self, obj):
        """
        :param obj: Object that will be updated.
        :return: Dictionary with attrs for creating a partial update on a given obj
        """
        obj["citizen"]["name"] = "BbbB"
        return obj

    def test_update_put(self):
        self.add_citizen_create_permission()
        obj = self.given_an_object()
        dni = obj["citizen"]["dni"]
        obj.update({self.path_pk_param_name: obj["id"]})
        rq_data = self.given_a_complete_update(obj)
        response = self.put(force_params=rq_data)
        assert response.status_code == HTTP_200_OK
        self.should_complete_update(response, obj)
        # Test that the dni can not be updated and the name can be updated
        assert Citizen.objects.get(dni=dni)
        assert Citizen.objects.get(name=rq_data["citizen"]["name"])

    @staticmethod
    def get_citizen():
        load_missing_data_districts()
        return {
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
            "dni": "{}X".format(random.randint(10000000, 99999999)),
            "birth_year": 1951,
            "response": False,
            "doc_type": Citizen.NIF,
            "mib_code": 957759,
            "blocked": False,
            "district": District.CIUTAT_VELLA,
            "language": GALICIAN,
            "sex": Citizen.FEMALE
        }

    @pytest.mark.parametrize("dni,citizen_nd,expected_response", (
        ("43968167X", True, HTTP_201_CREATED),
        ("43968167X", False, HTTP_201_CREATED),
        ("ND", True, HTTP_201_CREATED),
        ("ND", False, HTTP_400_BAD_REQUEST),
    ))
    def test_create_citizen_nd(self, dni, citizen_nd, expected_response):
        self.add_citizen_create_permission(citizen_nd=citizen_nd)
        rq_data = self.given_create_rq_data()
        rq_data["citizen"]["dni"] = dni
        self.when_is_authenticated()
        response = self.create(rq_data)
        assert response.status_code == expected_response

    @pytest.mark.parametrize("has_permissions,expected_response", ((True, HTTP_200_OK), (False, HTTP_403_FORBIDDEN)))
    def test_permissions(self, has_permissions, expected_response):
        self.add_citizen_create_permission()
        return super().test_permissions(has_permissions, expected_response)

    @pytest.mark.parametrize("object_number", (0, 1, 5))
    def test_excel_export(self, object_number):
        self.add_citizen_create_permission()
        return super().test_excel_export(object_number)


class TestApplicantResponse(OpenAPIRetrieveMixin, BaseOpenAPITest):
    detail_path = "/record_cards/applicant_response/{applicant_id}/"
    base_api_path = "/services/iris/api"

    lookup_field = "applicant_id"
    path_pk_param_name = "applicant_id"

    use_extra_get_params = True

    def given_an_object(self):
        citizen = mommy.make(Citizen, user_id="22222")
        applicant = mommy.make(Applicant, user_id="22222", citizen=citizen)
        mommy.make(ApplicantResponse, user_id="2222", applicant=applicant, response_channel_id=ResponseChannel.EMAIL)
        return {self.lookup_field: applicant.pk}

    def should_retrieve_object(self, response, obj):
        """
        Performs the checks on retrieve response.
        :param response: Response received.
        :param obj: Obj retrieved
        """
        assert response.json()["send_response"] is True

    @pytest.mark.parametrize("send_response", (True, False))
    def test_internal_operator(self, send_response):
        obj = self.given_an_object()
        applicant_response = ApplicantResponse.objects.get(applicant_id=obj["applicant_id"])
        applicant_type = mommy.make(ApplicantType, user_id="112231", send_response=send_response)
        InternalOperator.objects.create(document=applicant_response.applicant.citizen.dni,
                                        applicant_type=applicant_type, input_channel_id=InputChannel.ALTRES_CANALS)
        response = self.retrieve(force_params={self.path_pk_param_name: obj[self.lookup_field],
                                               "applicant_type_id": applicant_type.pk,
                                               "input_channel_id": InputChannel.ALTRES_CANALS})
        assert response.status_code == HTTP_200_OK
        assert response.json()["send_response"] is send_response
        assert response.json()["language"] is None
        assert response.json()["street"] == ""


class TestRecordCardViewSet(OpenAPIResourceExcelExportMixin, CreateRecordCardMixin, SetUserGroupMixin,
                            CreateDerivationsMixin, FeaturesMixin, CreateRecordFileMixin, SetPermissionMixin,
                            RecordUpdateMixin, SetRecordCardCreateThemeNoVisiblePermissonMixin,
                            BaseOpenAPICRUResourceTest):
    path = "/record_cards/record_cards/"
    base_api_path = "/services/iris/api"
    path_pk_param_name = "reference"
    lookup_field = "normalized_record_id"

    @pytest.mark.parametrize("object_number", (0, 1, 10))
    def test_list(self, object_number):
        [self.given_an_object() for _ in range(0, object_number)]
        self.add_permission()
        response = self.list(force_params={'page_size': self.paginate_by})
        assert response.status_code == HTTP_200_OK
        self.should_return_list(object_number, self.paginate_by, response)

    def add_permission(self):
        if not hasattr(self.user, "usergroup"):
            self.set_usergroup()
        self.set_group_permissions("22222", self.user.usergroup.group, [RECARD_SEARCH_NOFILTERS, RECARD_MULTIRECORD,
                                                                        CREATE])
        self.remove_permission_checker()

    @pytest.mark.parametrize("has_permissions,expected_response", (
        (True, HTTP_200_OK),
        (False, HTTP_403_FORBIDDEN),
    ))
    def test_permissions(self, has_permissions, expected_response):
        self.set_usergroup()
        group = self.user.usergroup.group
        if has_permissions:
            self.set_group_permissions("22222", group, [RECARD_SEARCH_NOFILTERS])
        [self.create_record_card(responsible_profile=group) for _ in range(10)]
        response = self.list(force_params={"page_size": self.paginate_by})
        assert response.status_code == expected_response

    def test_retrieve(self):
        obj = self.given_an_object()
        response = self.retrieve(force_params={self.path_pk_param_name: obj[self.lookup_field]})
        assert response.status_code == HTTP_200_OK
        self.should_retrieve_object(response, obj)

    def test_update_put_rec(self):
        obj = self.given_an_object()
        obj.update({self.path_pk_param_name: obj[self.lookup_field]})
        rq_data = self.given_a_complete_update(obj)
        with patch("record_cards.tasks.register_possible_similar_records.delay") as mock_delay:
            with patch("record_cards.tasks.geocode_ubication.delay") as geocode_ubication_delay:
                response = self.put(force_params=rq_data)
                assert response.status_code == HTTP_200_OK
                self.should_complete_update(response, obj)
                mock_delay.assert_called_once()
                geocode_ubication_delay.assert_called_once()

    def test_update_patch_rec(self):
        obj = self.given_an_object()
        obj.update({self.path_pk_param_name: obj[self.lookup_field]})
        rq_data = self.given_a_partial_update(obj)
        with patch("record_cards.tasks.register_possible_similar_records.delay") as mock_delay:
            with patch("record_cards.tasks.geocode_ubication.delay") as geocode_ubication_delay:
                response = self.patch(force_params=rq_data)
                assert response.status_code == HTTP_200_OK
                self.should_partial_update(response, obj)
                mock_delay.assert_called_once()
                geocode_ubication_delay.assert_called_once()

    def get_default_data(self):
        return self.get_record_card_data(add_update_permissions=True)

    def given_create_rq_data(self, create_group=True, is_anonymous=False, district_id=None):
        return self.get_record_card_data(create_group=create_group, is_anonymous=is_anonymous, district_id=district_id)

    def when_data_is_invalid(self, data):
        feature = mommy.make(Feature, user_id="22")
        data["features"] = [{"feature": feature.pk, "value": "test_value", "description": "new_description"}]
        data["special_features"] = []

    def given_a_partial_update(self, obj):
        """
        :param obj: Object that will be updated.
        :return: Dictionary with attrs for creating a partial update on a given obj
        """
        obj.pop("responsible_profile", None)
        return obj

    def given_a_complete_update(self, obj):
        """
        :param obj: Object that will be updated.
        :return: Dictionary with attrs for creating a partial update on a given obj
        """
        obj.pop("responsible_profile", None)
        return obj

    @pytest.mark.parametrize("num_comments", (0, 1, 3))
    def test_comments(self, num_comments):
        obj = self.given_an_object()

        for _ in range(num_comments):
            mommy.make(Comment, record_card_id=obj["id"], user_id="222")

        response = self.retrieve(force_params={self.path_pk_param_name: obj[self.lookup_field]})
        assert response.status_code == HTTP_200_OK
        assert len(response.data["comments"]) == num_comments

    def test_create_record_card_nouser_group(self):
        rq_data = self.given_create_rq_data(create_group=False)
        self.when_is_authenticated()
        response = self.create(rq_data)
        assert response.status_code == HTTP_403_FORBIDDEN

    def test_create_record_card_anonymous_group(self):
        rq_data = self.given_create_rq_data(is_anonymous=True)
        self.when_is_authenticated()
        response = self.create(rq_data)
        assert response.status_code == HTTP_400_BAD_REQUEST

    def test_record_card_autovalidate(self):
        record_card = self.get_record_card_data(autovalidate_records=True,
                                                process_id=Process.PLANING_RESOLUTION_RESPONSE)
        self.when_is_authenticated()
        response = self.create(record_card)
        assert response.status_code == HTTP_201_CREATED
        record_card_id = response.json()["id"]
        assert RecordCard.objects.get(pk=record_card_id).record_state_id == RecordState.IN_PLANING
        assert Workflow.objects.get(main_record_card_id=record_card_id).state_id == RecordState.IN_PLANING

        assert RecordCardStateHistory.objects.get(record_card_id=record_card_id,
                                                  next_state_id=RecordState.IN_PLANING, automatic=True)

    def test_record_card_autovalidate_close_directly(self):
        record_card_data = self.get_record_card_data(autovalidate_records=True, process_id=Process.CLOSED_DIRECTLY)
        self.when_is_authenticated()
        response = self.create(record_card_data)
        assert response.status_code == HTTP_201_CREATED
        record_card = RecordCard.objects.get(pk=response.json()["id"])
        assert record_card.record_state_id == RecordState.CLOSED
        assert record_card.closing_date
        assert Workflow.objects.get(main_record_card=record_card).state_id == RecordState.CLOSED
        assert RecordCardStateHistory.objects.get(record_card=record_card,
                                                  next_state_id=RecordState.CLOSED, automatic=True)

    @pytest.mark.parametrize("multi_record,copy_responsechannel", (
        (True, False),
        (True, True),
        (False, False)
    ))
    def test_record_card_multirecord_from(self, multi_record, copy_responsechannel):
        self.add_permission()
        if multi_record:
            multirecord_record_card = self.create_record_card(create_record_card_response=True)
            record_card = self.get_record_card_data(multirecord_from=multirecord_record_card.pk,
                                                    group=self.user.usergroup.group,
                                                    copy_responsechannel=copy_responsechannel)
        else:
            record_card = self.get_record_card_data(group=self.user.usergroup.group)
        self.when_is_authenticated()
        response = self.create(record_card)
        assert response.status_code == HTTP_201_CREATED
        record_card_id = response.json()["id"]
        record_card_created = RecordCard.objects.get(pk=record_card_id)
        assert record_card_created.is_multirecord is multi_record
        if multi_record:
            assert record_card_created.multirecord_from_id == multirecord_record_card.pk
            multirecord_record_card = RecordCard.objects.get(pk=multirecord_record_card.pk)
            assert multirecord_record_card.is_multirecord is multi_record
            assert record_card_created.input_channel_id == multirecord_record_card.input_channel_id
            response_channel_id = record_card_created.recordcardresponse.response_channel_id
            assert response_channel_id == multirecord_record_card.recordcardresponse.response_channel_id
        else:
            assert record_card_created.multirecord_from_id is None

    @pytest.mark.parametrize("initial_state", (RecordState.CLOSED, RecordState.CANCELLED))
    def test_record_card_multirecord_closed_states(self, initial_state):
        self.add_permission()
        multirecord_record_card = self.create_record_card(record_state_id=initial_state,
                                                          create_record_card_response=True)
        record_card = self.get_record_card_data(multirecord_from=multirecord_record_card.pk,
                                                group=self.user.usergroup.group)
        self.when_is_authenticated()
        response = self.create(record_card)
        assert response.status_code == HTTP_409_CONFLICT

    @pytest.mark.parametrize(
        "create_direct_derivation,create_district_derivation,district_id,derivation_state_id", (
            (True, False, District.CIUTAT_VELLA, RecordState.PENDING_VALIDATE),
            (False, False, District.CIUTAT_VELLA, RecordState.IN_PLANING),
            (False, True, District.CIUTAT_VELLA, RecordState.IN_PLANING),
            (False, True, None, RecordState.PENDING_VALIDATE)
        ))
    def test_create_record_card_derivation(self, create_direct_derivation, create_district_derivation, district_id,
                                           derivation_state_id):
        rq_data = self.given_create_rq_data(district_id=district_id)
        element_detail_id = rq_data["element_detail_id"]
        _, parent, _, _, _, _ = create_groups()
        if create_direct_derivation:
            responsible_profile = self.create_direct_derivation(element_detail_id=element_detail_id,
                                                                record_state_id=derivation_state_id, group=parent)
        elif create_district_derivation:
            district_group = self.create_district_derivation(element_detail_id=element_detail_id,
                                                             record_state_id=derivation_state_id)
            if district_id and derivation_state_id == RecordState.PENDING_VALIDATE:
                responsible_profile = district_group
            else:
                responsible_profile = self.user.usergroup.group
        else:
            responsible_profile = self.user.usergroup.group

        self.when_is_authenticated()
        response = self.create(rq_data)
        assert response.status_code == HTTP_201_CREATED
        record_card_id = response.json()["id"]
        record_card_created = RecordCard.objects.get(pk=record_card_id)
        assert record_card_created.responsible_profile == responsible_profile

    def test_create_signal(self):
        signal = Mock(spec=Signal)
        with patch("record_cards.models.record_card_created", signal):
            rq_data = self.given_create_rq_data()
            self.when_is_authenticated()
            response = self.create(rq_data)
            assert response.status_code == HTTP_201_CREATED
            self.should_create_object(response, rq_data)
            record_card = RecordCard.objects.get(pk=response.json()["id"])
            signal.send_robust.assert_called_with(record_card=record_card, sender=RecordCard)

    def test_create_tasks(self):
        with patch("record_cards.tasks.register_possible_similar_records.delay") as mock_similar_delay:
            with patch("record_cards.tasks.save_last_applicant_response.delay") as mock_response_delay:
                rq_data = self.given_create_rq_data()
                self.when_is_authenticated()
                response = self.create(rq_data)
                assert response.status_code == HTTP_201_CREATED
                self.should_create_object(response, rq_data)
                mock_similar_delay.assert_called_once()
                mock_response_delay.assert_called_once()

    @pytest.mark.parametrize("similar_records", (0, 1, 3))
    def test_record_card_call_register_similar(self, similar_records):
        _, _, _, second_soon, _, _ = create_groups()
        element_detail = self.create_element_detail(similarity_hours=1, similarity_meters=50)
        input_channel = mommy.make(InputChannel, user_id="22222")
        ubication = Ubication.objects.create(via_type="carrer", street="test", xetrs89a=427236.69, yetrs89a=4582247.42)
        for _ in range(similar_records):
            self.create_record_card(responsible_profile=second_soon, element_detail=element_detail,
                                    ubication=ubication, record_state_id=RecordState.IN_PLANING,
                                    input_channel=input_channel)
        record_card = self.get_record_card_data(element_detail=element_detail, ubication=ubication,
                                                input_channel=input_channel, group=second_soon)

        with patch("record_cards.tasks.register_possible_similar_records.delay") as mock_delay:
            self.when_is_authenticated()
            response = self.create(record_card)
            assert response.status_code == HTTP_201_CREATED
            record_card_id = response.json()["id"]
            record_card = RecordCard.objects.get(pk=record_card_id)
            assert record_card.record_state_id == RecordState.PENDING_VALIDATE
            mock_delay.assert_called_once()

    @pytest.mark.parametrize("citizen_dni,support_nd,group_nd,expected_response", (
        ("43199353O", False, False, HTTP_201_CREATED),
        (settings.CITIZEN_ND, False, False, HTTP_400_BAD_REQUEST),
        (settings.CITIZEN_ND, False, True, HTTP_400_BAD_REQUEST),
        (settings.CITIZEN_ND, True, False, HTTP_400_BAD_REQUEST),
        (settings.CITIZEN_ND, True, True, HTTP_201_CREATED),
        ("43569353O", True, True, HTTP_201_CREATED),
    ))
    def test_record_card_citizen_nd(self, citizen_dni, support_nd, group_nd, expected_response):
        group = mommy.make(Group, user_id="22222", profile_ctrl_user_id="2222", citizen_nd=group_nd)
        record_card_data = self.get_record_card_data(citizen_dni=citizen_dni, support_nd=support_nd, group=group)
        response = self.create(record_card_data)
        assert response.status_code == expected_response

    @pytest.mark.parametrize("add_communication_media,add_date,expected_response", (
        (True, True, HTTP_201_CREATED),
        (False, True, HTTP_400_BAD_REQUEST),
        (True, False, HTTP_400_BAD_REQUEST),
        (False, False, HTTP_400_BAD_REQUEST),
    ))
    def test_record_card_communication_media(self, add_communication_media, add_date, expected_response):
        support = Support.objects.get(pk=Support.COMMUNICATION_MEDIA)
        record_card_data = self.get_record_card_data(autovalidate_records=True, support=support,
                                                     process_id=Process.PLANING_RESOLUTION_RESPONSE)

        input_channel = mommy.make(InputChannel, user_id="222")
        media_type = mommy.make(MediaType, user_id="222")

        if add_communication_media:
            record_card_data["communication_media_id"] = mommy.make(
                CommunicationMedia, user_id="222", input_channel=input_channel, media_type=media_type).pk
        else:
            record_card_data.pop("communication_media_id")
        record_card_data["communication_media_date"] = timezone.now().strftime("%Y-%m-%d") if add_date else None

        self.when_is_authenticated()
        response = self.create(record_card_data)
        assert response.status_code == expected_response

    @pytest.mark.parametrize("object_number", (0, 1, 5))
    def test_record_files(self, tmpdir_factory, object_number):
        record_card = self.create_record_card()

        [self.create_file(tmpdir_factory, record_card, file_number) for file_number in range(object_number)]

        response = self.retrieve(force_params={self.path_pk_param_name: record_card.normalized_record_id})
        assert response.status_code == HTTP_200_OK
        response_data = response.json()
        assert "files" in response_data
        for file_data in response_data["files"]:
            assert "file" in file_data
            assert "filename" in file_data
            assert "delete_url" in file_data
            assert "id" in file_data

    @pytest.mark.parametrize("register_code,register_required,create_ariadna,expected_response", (
        ("2019/029292", True, True, HTTP_201_CREATED),
        ("2019/029292", False, True, HTTP_201_CREATED),
        ("2019/029292", True, False, HTTP_400_BAD_REQUEST),
        ("2019/029292", False, False, HTTP_400_BAD_REQUEST),
        ("2019/02a292", True, True, HTTP_400_BAD_REQUEST),
        ("9/025292", True, True, HTTP_400_BAD_REQUEST),
        ("9/0292", True, True, HTTP_400_BAD_REQUEST),
        (None, True, False, HTTP_400_BAD_REQUEST),
    ))
    def test_record_card_ariadna(self, register_code, register_required, create_ariadna, expected_response):
        support = mommy.make(Support, user_id="2222", register_required=register_required)
        if create_ariadna:
            ariadna = mommy.make(Ariadna, user_id="2222", used=False)
            ariadna.code = register_code
            ariadna.save()

        record_card_data = self.get_record_card_data(support=support)
        record_card_data["register_code"] = register_code
        response = self.create(record_card_data)
        assert response.status_code == expected_response
        if expected_response == HTTP_201_CREATED:
            record_card_id = response.json()["id"]
            assert AriadnaRecord.objects.get(record_card_id=record_card_id)
            ariadna = Ariadna.objects.get(pk=ariadna.pk)
            assert ariadna.used is True

    @pytest.mark.parametrize("mayorship,mayorship_permission,involve_conversation,expected_full_detail", (
        (False, False, False, False),
        (False, True, False, False),
        (False, False, True, True),
        (False, True, True, True),
        (True, False, False, False),
        (True, True, False, True),
        (True, False, True, True),
        (True, True, True, True),
    ))
    def test_retrieve_mayorship_records(self, mayorship, mayorship_permission, involve_conversation,
                                        expected_full_detail):
        dair, parent, soon, _, _, noambit_soon = create_groups()
        self.set_usergroup(parent)

        if mayorship_permission:
            self.set_permission(MAYORSHIP, group=parent)
        element_detail = self.create_element_detail()
        GroupProfileElementDetail.objects.create(group=noambit_soon, element_detail=element_detail)
        record_card = self.create_record_card(responsible_profile=dair, mayorship=mayorship,
                                              element_detail=element_detail)
        if involve_conversation:
            conv = Conversation.objects.create(type=Conversation.INTERNAL,
                                               creation_group=record_card.responsible_profile,
                                               record_card=record_card, is_opened=True)
            ConversationGroup.objects.create(conversation=conv, group=parent)
            mommy.make(Message, user_id='22222', conversation=conv, group=dair,
                       record_state_id=record_card.record_state_id)

        response = self.retrieve(force_params={self.path_pk_param_name: record_card.normalized_record_id})
        assert response.status_code == HTTP_200_OK
        response_json = response.json()
        assert response_json["full_detail"] is expected_full_detail

    @pytest.mark.parametrize("user_group,responsible_profile,pending_message,expected_full_detail", (
        (2, 2, True, True),
        (2, 2, False, True),
        (2, 3, True, True),
        (2, 3, False, True),
        (3, 2, True, True),
        (3, 2, False, False),
        (1, 2, True, True),
        (1, 2, False, True),
    ))
    def test_retrieve_restricted_records(self, user_group, responsible_profile, pending_message, expected_full_detail):
        groups = dict_groups()
        request_group = groups[user_group]
        self.set_usergroup(request_group)

        element_detail = self.create_element_detail()
        noambit_soon = groups[6]
        GroupProfileElementDetail.objects.create(group=noambit_soon, element_detail=element_detail)
        record_card = self.create_record_card(responsible_profile=groups[responsible_profile],
                                              element_detail=element_detail)
        if pending_message:
            conv = Conversation.objects.create(type=Conversation.INTERNAL,
                                               creation_group=record_card.responsible_profile,
                                               record_card=record_card, is_opened=True)
            ConversationGroup.objects.create(conversation=conv, group=request_group)
            mommy.make(Message, user_id='22222', conversation=conv, group=groups[responsible_profile],
                       record_state_id=record_card.record_state_id)

        response = self.retrieve(force_params={self.path_pk_param_name: record_card.normalized_record_id})
        assert response.status_code == HTTP_200_OK
        response_json = response.json()
        assert response_json["full_detail"] is expected_full_detail

    @pytest.mark.parametrize("add_create_user,expected_full_detail", (
        (True, True), (False, False)
    ))
    def test_retrieve_user_allowed(self, add_create_user, expected_full_detail):
        dair, parent, soon, _, noambit_parent, noambit_soon = create_groups()
        self.set_usergroup(noambit_soon)

        kwargs = {"responsible_profile": parent}
        if add_create_user:
            kwargs["user_id"] = get_user_traceability_id(self.user)

        element_detail = self.create_element_detail()
        GroupProfileElementDetail.objects.create(group=noambit_parent, element_detail=element_detail)
        kwargs["element_detail"] = element_detail
        record_card = self.create_record_card(**kwargs)

        response = self.retrieve(force_params={self.path_pk_param_name: record_card.normalized_record_id})
        assert response.status_code == HTTP_200_OK
        response_json = response.json()
        assert response_json["full_detail"] is expected_full_detail

    def test_retrieve_detail_no_groupsprofiles(self):
        dair, parent, soon, _, noambit_parent, noambit_soon = create_groups()
        self.set_usergroup(noambit_parent)
        record_card = self.create_record_card(responsible_profile=parent)
        response = self.retrieve(force_params={self.path_pk_param_name: record_card.normalized_record_id})
        assert response.status_code == HTTP_200_OK
        response_json = response.json()
        assert response_json["full_detail"] is True

    def test_retrieve_detail_group_can_see_own(self):
        dair, parent, soon, _, noambit_parent, noambit_soon = create_groups()
        self.set_usergroup(parent)
        element_detail = self.create_element_detail()
        GroupProfileElementDetail.objects.create(group=parent, element_detail=element_detail)
        record_card = self.create_record_card(responsible_profile=parent, element_detail=element_detail)
        response = self.retrieve(force_params={self.path_pk_param_name: record_card.normalized_record_id})
        assert response.status_code == HTTP_200_OK
        response_json = response.json()
        assert response_json["full_detail"] is True

    def test_retrieve_detail_group_can_see_ancestor(self):
        dair, parent, soon, _, noambit_parent, noambit_soon = create_groups()
        self.set_usergroup(dair)
        element_detail = self.create_element_detail()
        GroupProfileElementDetail.objects.create(group=parent, element_detail=element_detail)
        record_card = self.create_record_card(responsible_profile=parent, element_detail=element_detail)
        response = self.retrieve(force_params={self.path_pk_param_name: record_card.normalized_record_id})
        assert response.status_code == HTTP_200_OK
        response_json = response.json()
        assert response_json["full_detail"] is True

    def test_retrieve_detail_group_descendant(self):
        dair, parent, soon, _, noambit_parent, noambit_soon = create_groups()
        self.set_usergroup(soon)
        element_detail = self.create_element_detail()
        GroupProfileElementDetail.objects.create(group=parent, element_detail=element_detail)
        record_card = self.create_record_card(responsible_profile=parent, element_detail=element_detail)
        response = self.retrieve(force_params={self.path_pk_param_name: record_card.normalized_record_id})
        assert response.status_code == HTTP_200_OK
        response_json = response.json()
        assert response_json["full_detail"] is False

    def test_retrieve_detail_group_can_see_other_ambit(self):
        dair, parent, soon, _, noambit_parent, noambit_soon = create_groups()
        self.set_usergroup(noambit_parent)
        element_detail = self.create_element_detail()
        GroupProfileElementDetail.objects.create(group=parent, element_detail=element_detail)
        record_card = self.create_record_card(responsible_profile=parent, element_detail=element_detail)
        response = self.retrieve(force_params={self.path_pk_param_name: record_card.normalized_record_id})
        assert response.status_code == HTTP_200_OK
        response_json = response.json()
        assert response_json["full_detail"] is False

    @pytest.mark.parametrize(
        "initial_state,description,change_features,update_mayorship,update_ubication,"
        "update_response_channel,permissions,expected_response", (
            (RecordState.PENDING_VALIDATE, "description", True, True, True, True,
             [MAYORSHIP, RESP_CHANNEL_UPDATE], HTTP_200_OK),
            (RecordState.PENDING_VALIDATE, "", True, False, True, True,
             [RESP_CHANNEL_UPDATE], HTTP_400_BAD_REQUEST),
            (RecordState.PENDING_VALIDATE, "description", False, False, True, True,
             [RESP_CHANNEL_UPDATE], HTTP_200_OK),
            (RecordState.PENDING_VALIDATE, "description", True, False, True, True, [], HTTP_400_BAD_REQUEST),
            (RecordState.PENDING_VALIDATE, "description", False, True, True, True,
             [MAYORSHIP, RESP_CHANNEL_UPDATE], HTTP_200_OK),
            (RecordState.PENDING_VALIDATE, "description", False, True, False, True,
             [MAYORSHIP, RESP_CHANNEL_UPDATE], HTTP_200_OK),
            (RecordState.PENDING_VALIDATE, "description", True, True, True, True, [], HTTP_400_BAD_REQUEST),
            (RecordState.PENDING_VALIDATE, "description", True, True, True, False,
             [MAYORSHIP, RESP_CHANNEL_UPDATE], HTTP_200_OK),
            (RecordState.PENDING_VALIDATE, "description", True, True, True, False, [MAYORSHIP], HTTP_200_OK),
        ))
    def test_record_card_update(self, initial_state, description, change_features, update_mayorship,
                                update_ubication, update_response_channel, permissions, expected_response):
        _, parent, _, _, _, _ = create_groups()
        self.set_group_permissions("222222", parent, permissions)

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

        response = self.put(force_params=data)
        assert response.status_code == expected_response
        if expected_response == HTTP_200_OK:
            record_card = RecordCard.objects.get(pk=record_card.pk)
            self.update_expected_data(expected_data, update_data)
            assert Comment.objects.get(record_card=record_card, reason_id=Reason.RECORDCARD_UPDATED)

        assert record_card.description == expected_data["expected_description"]
        assert record_card.mayorship == expected_data["expected_mayorship"]
        assert record_card.ubication_id == expected_data["expected_ubication"]
        assert record_card.recordcardresponse.response_channel_id == expected_data["expected_response_channel"]

    @pytest.mark.parametrize("initial_state", (RecordState.CLOSED, RecordState.CANCELLED))
    def test_update_closed_cancelled_records(self, initial_state):
        _, parent, _, _, _, _ = create_groups()
        self.set_group_permissions("222222", parent, [RESP_CHANNEL_UPDATE])
        input_channel = mommy.make(InputChannel, user_id="2222", can_be_mayorship=True)
        record_card = self.create_record_card(record_state_id=initial_state, responsible_profile=parent,
                                              create_record_card_response=True,
                                              communication_media_date=timezone.now().date(),
                                              communication_media_detail="testtesttest", input_channel=input_channel)
        reference_param = {self.path_pk_param_name: getattr(record_card, self.lookup_field)}
        response = self.retrieve(force_params=reference_param)
        update_data = response.json()
        update_data.update(reference_param)
        response = self.put(force_params=update_data)

        assert response.status_code == HTTP_409_CONFLICT

    @pytest.mark.parametrize(
        "active,future_activate_date,visible,future_visible_date,theme_novisible_permission,expected_response", (
            (True, False, True, False, True, HTTP_201_CREATED),
            (True, False, True, False, False, HTTP_201_CREATED),
            (True, True, True, False, True, HTTP_400_BAD_REQUEST),
            (True, False, True, True, True, HTTP_201_CREATED),
            (True, False, True, True, False, HTTP_201_CREATED),
            (True, False, False, False, True, HTTP_201_CREATED),
            (True, False, False, False, False, HTTP_201_CREATED),
            (False, False, True, False, True, HTTP_400_BAD_REQUEST),
        ))
    def test_record_card_theme_active_visible(self, active, future_activate_date, visible, future_visible_date,
                                              theme_novisible_permission, expected_response):
        self.set_usergroup()
        if theme_novisible_permission:
            self.set_recard_create_themenovisible_permission(self.user.usergroup.group)
        else:
            profile = mommy.make(Profile, user_id="2222")
            create_recard_permission = Permission.objects.get(codename=CREATE)
            ProfilePermissions.objects.create(profile=profile, permission=create_recard_permission)
            GroupProfiles.objects.create(group=self.user.usergroup.group, profile=profile)

        element_detail = self.create_element_detail(active=active,
                                                    fill_active_mandatory_fields=active,
                                                    set_future_activation_date=future_activate_date,
                                                    visible=visible,
                                                    set_future_visible_date=future_visible_date)
        record_card = self.get_record_card_data(element_detail=element_detail, group=self.user.usergroup.group)
        self.when_is_authenticated()
        response = self.create(record_card)
        assert response.status_code == expected_response

    @pytest.mark.parametrize("can_be_mayorship,mayorship,create_param,expected_response", (
        (True, True, True, HTTP_201_CREATED),
        (True, True, False, HTTP_201_CREATED),
        (True, False, True, HTTP_201_CREATED),
        (True, False, False, HTTP_201_CREATED),
        (False, True, True, HTTP_400_BAD_REQUEST),
        (False, True, False, HTTP_400_BAD_REQUEST),
        (False, False, True, HTTP_201_CREATED),
        (False, False, False, HTTP_201_CREATED),
    ))
    def test_record_card_mayorship(self, can_be_mayorship, mayorship, create_param, expected_response):
        dair_group, parent, soon, _, _, mayorship_group = create_groups()
        self.set_usergroup(group=parent)
        self.set_group_permissions("2222222", parent, [MAYORSHIP])
        input_channel = mommy.make(InputChannel, user_id="22222", can_be_mayorship=can_be_mayorship)
        element_detail = self.create_element_detail()
        DerivationDirect.objects.create(element_detail=element_detail, group=soon,
                                        record_state_id=RecordState.PENDING_VALIDATE)

        if create_param:
            param, _ = Parameter.objects.get_or_create(parameter="PERFIL_DERIVACIO_ALCALDIA")
            param.valor = mayorship_group.pk
            param.save()

        record_card = self.get_record_card_data(input_channel=input_channel, mayorship=mayorship, group=parent,
                                                element_detail=element_detail)
        self.when_is_authenticated()
        response = self.create(record_card)
        assert response.status_code == expected_response
        if expected_response == HTTP_201_CREATED:
            record_card = RecordCard.objects.get(pk=response.json()["id"])
            if can_be_mayorship and mayorship:
                if create_param:
                    assert record_card.responsible_profile_id == mayorship_group.pk
                else:
                    assert record_card.responsible_profile_id == dair_group.pk
                assert record_card.mayorship is True
                assert RecordCardAlarms(record_card, parent).mayorship_alarm is True
            else:
                assert record_card.responsible_profile_id == soon.pk
                assert record_card.mayorship is False
                assert RecordCardAlarms(record_card, parent).mayorship_alarm is False

    def test_create_creation_department(self):
        rq_data = self.given_create_rq_data()
        user = self.when_is_authenticated()
        response = self.create(rq_data)
        assert response.status_code == HTTP_201_CREATED
        record_card = RecordCard.objects.get(pk=response.json()["id"])
        assert record_card.creation_department == user.imi_data['dptcuser']

    @pytest.mark.parametrize(
        "via_type,street,street2,district,requires_ubication,requires_ubication_district,expected_response", (
            ("street", "street name", "street name2", None, True, False, HTTP_201_CREATED),
            ("", "", "", District.CIUTAT_VELLA, False, True, HTTP_201_CREATED),
            ("", "street name", "street name2", None, True, False, HTTP_400_BAD_REQUEST),
            ("street", "", "street name2", None, True, False, HTTP_400_BAD_REQUEST),
            ("street", "street name", "", None, True, False, HTTP_400_BAD_REQUEST),
            ("", "", "", None, False, True, HTTP_400_BAD_REQUEST),
            ("street", "street name", "street name2", District.EIXAMPLE, True, True, HTTP_201_CREATED),
            ("street", "street name", "street name2", District.EIXAMPLE, False, False, HTTP_201_CREATED),
        ))
    def test_ubication_record_card(self, via_type, street, street2, district, requires_ubication,
                                   requires_ubication_district, expected_response):
        ubication = mommy.make(Ubication, user_id="22222", via_type=via_type, street=street, street2=street2,
                               district_id=district)
        element_detail = self.create_element_detail(
            requires_ubication=requires_ubication, requires_ubication_district=requires_ubication_district)
        rq_data = self.get_record_card_data(element_detail=element_detail, ubication=ubication)
        self.when_is_authenticated()
        response = self.create(rq_data)
        assert response.status_code == expected_response

    def test_update_user_displayed(self):
        obj = self.given_an_object()
        response = self.retrieve(force_params={self.path_pk_param_name: obj[self.lookup_field]})
        assert response.status_code == HTTP_200_OK
        self.should_retrieve_object(response, obj)
        record_card = RecordCard.objects.get(pk=response.json()["id"])
        assert record_card.user_displayed == get_user_traceability_id(self.user)

    @pytest.mark.parametrize("initial_response_channel,send_response,expected_response", (
        (ResponseChannel.LETTER, True, HTTP_201_CREATED),
        (ResponseChannel.NONE, True, HTTP_400_BAD_REQUEST),
        (ResponseChannel.LETTER, False, HTTP_201_CREATED),
        (ResponseChannel.NONE, False, HTTP_201_CREATED),
    ))
    def test_record_card_internal_operator(self, initial_response_channel, send_response, expected_response):

        input_channel = InputChannel.objects.get(pk=InputChannel.ALTRES_CANALS)
        applicant_type = mommy.make(ApplicantType, user_id="2222", send_response=send_response)
        citizen = mommy.make(Citizen, user_id="2222")
        applicant = mommy.make(Applicant, citizen=citizen, user_id="222")

        InternalOperator.objects.create(document=citizen.dni, input_channel=input_channel,
                                        applicant_type=applicant_type)
        element_detail = self.create_element_detail()
        ElementDetailResponseChannel.objects.create(elementdetail=element_detail,
                                                    responsechannel_id=initial_response_channel)
        record_card_data = self.get_record_card_data(input_channel=input_channel, applicant_type=applicant_type,
                                                     applicant=applicant, element_detail=element_detail)
        record_card_data["recordcardresponse"]["response_channel"] = initial_response_channel

        self.when_is_authenticated()
        response = self.create(record_card_data)
        assert response.status_code == expected_response


class TestRecordCardUpdateCheckView(CreateRecordCardMixin, UpdatePatchMixin, PutOperation, BaseOpenAPITest):
    detail_path = "/record_cards/record_cards/{normalized_record_id}/update/check/"
    base_api_path = "/services/iris/api"

    def prepare_path(self, path, path_spec, force_params=None):
        """
        :param path: Relative URI of the operation.
        :param path_spec: OpenAPI spec as dict for part.
        :param force_params: Explicitly force params.
        :return: Path for performing a request to the given OpenAPI path.
        """
        path = path.format(normalized_record_id=force_params["normalized_record_id"])
        return "{}{}".format(self.base_api_path, path)

    def test_update_check_no_changes(self):
        record_card = self.create_record_card(create_record_card_response=True, district_id=District.LES_CORTS)
        request = HttpRequest()
        request.user = self.user
        rq_data = RecordCardSerializer(instance=record_card, context={"request": request}).data
        self.when_is_authenticated()

        response = self.put(rq_data)
        assert response.status_code == HTTP_200_OK
        response_data = response.json()
        assert response_data["__action__"]["can_confirm"] is True
        assert response_data["__action__"]["reason"] is None
        assert response_data["__action__"]["next_group"]["id"] == record_card.responsible_profile_id
        assert response_data["__action__"]["next_state"] == record_card.record_state_id
        assert response_data["__action__"]["different_ambit"] is False

    def test_update_check_changes(self):
        record_card = self.create_record_card(create_record_card_response=True, district_id=District.LES_CORTS)
        request = HttpRequest()
        request.user = self.user
        rq_data = RecordCardSerializer(instance=record_card, context={"request": request}).data
        rq_data["description"] = "description description description description description"
        self.when_is_authenticated()
        response = self.patch(rq_data)
        assert response.status_code == HTTP_200_OK
        response_data = response.json()
        assert response_data["__action__"]["can_confirm"] is True
        assert response_data["__action__"]["reason"] is None
        assert response_data["__action__"]["next_group"]["id"] == record_card.responsible_profile_id
        assert response_data["__action__"]["next_state"] == record_card.record_state_id
        assert response_data["__action__"]["different_ambit"] is False

    def test_update_with_derivations_change_ambit(self):
        _, parent, _, _, noambit_parent, _ = create_groups()
        element_detail = self.create_element_detail()
        for district in District.objects.filter(allow_derivation=True):
            DerivationDistrict.objects.create(element_detail=element_detail, district=district, group=noambit_parent,
                                              record_state_id=RecordState.PENDING_VALIDATE)
        record_card = self.create_record_card(create_record_card_response=True, district_id=District.LES_CORTS,
                                              responsible_profile=parent, element_detail=element_detail)
        request = HttpRequest()
        request.user = self.user
        rq_data = RecordCardSerializer(instance=record_card, context={"request": request}).data
        rq_data["ubication"]["district_id"] = District.CIUTAT_VELLA
        rq_data["ubication"]["district"] = District.CIUTAT_VELLA
        self.when_is_authenticated()
        response = self.put(rq_data)
        assert response.status_code == HTTP_200_OK
        response_data = response.json()
        assert response_data["__action__"]["can_confirm"] is True
        assert response_data["__action__"]["reason"] is None
        assert response_data["__action__"]["next_group"]["id"] == noambit_parent.pk
        assert response_data["__action__"]["next_state"] == record_card.record_state_id
        assert response_data["__action__"]["different_ambit"] is True

    def test_update_with_derivations_nochange_ambit(self):
        _, parent, _, _, noambit_parent, _ = create_groups()
        element_detail = self.create_element_detail()
        for district in District.objects.filter(allow_derivation=True):
            DerivationDistrict.objects.create(element_detail=element_detail, district=district, group=parent,
                                              record_state_id=RecordState.PENDING_VALIDATE)
        record_card = self.create_record_card(create_record_card_response=True, district_id=District.LES_CORTS,
                                              responsible_profile=parent, element_detail=element_detail)
        request = HttpRequest()
        request.user = self.user
        rq_data = RecordCardSerializer(instance=record_card, context={"request": request}).data
        rq_data["ubication"]["district_id"] = District.CIUTAT_VELLA
        self.when_is_authenticated()
        response = self.patch(rq_data)
        assert response.status_code == HTTP_200_OK
        response_data = response.json()
        assert response_data["__action__"]["can_confirm"] is True
        assert response_data["__action__"]["reason"] is None
        assert response_data["__action__"]["next_group"]["id"] == parent.pk
        assert response_data["__action__"]["next_state"] == record_card.record_state_id
        assert response_data["__action__"]["different_ambit"] is False


class TestRecordCreateCopyFiles(CreateRecordCardMixin, CreateOperationMixin, BaseOpenAPITest):
    path = "/record_cards/record_cards/"
    base_api_path = "/services/iris/api"
    use_extra_get_params = True

    def test_copy_files(self, test_file):
        record_card = self.create_record_card()
        RecordFile.objects.create(record_card=record_card, file=test_file.name, filename=test_file.name)
        rq_data = self.get_record_card_data(group=record_card.responsible_profile,
                                            input_channel=record_card.input_channel)
        rq_data[COPY_FILES_FROM_PARAM] = record_card.pk
        self.when_is_authenticated()
        with patch("record_cards.tasks.copy_record_files.delay") as mock_delay:
            response = self.create(rq_data)
            assert response.status_code == HTTP_201_CREATED
            mock_delay.assert_called_once()


class TestRecordCardPkRetrieveView(CreateRecordCardMixin, OpenAPIRetrieveMixin, BaseOpenAPITest):
    detail_path = "/record_cards/record_cards/retrieve/{id}/"
    base_api_path = "/services/iris/api"

    def given_an_object(self):
        record_card = self.create_record_card(create_record_card_response=True)
        return {self.path_pk_param_name: getattr(record_card, self.lookup_field)}


class TestRecordFileDelete(CreateRecordFileMixin, CreateRecordCardMixin, OpenAPIResoureceDeleteMixin, BaseOpenAPITest):
    detail_path = "/record_cards/record_files/{id}/delete/"
    base_api_path = "/services/iris/api"
    check_retrieve = False

    @pytest.mark.parametrize("different_group_action,expected_response", (
        (False, HTTP_204_NO_CONTENT),
        (True, HTTP_400_BAD_REQUEST),
    ))
    def test_delete(self, tmpdir_factory, different_group_action, expected_response):
        dair, parent, soon, _, _, _ = create_groups()
        record_card = self.create_record_card(responsible_profile=parent)
        obj = self.given_an_object(tmpdir_factory, record_card)
        url_params = {self.path_pk_param_name: obj[self.lookup_field]}
        record_file = RecordFile.objects.get(pk=obj[self.lookup_field])

        if different_group_action:
            UserGroup.objects.filter(user=self.user).delete()
            UserGroup.objects.create(user=self.user, group=soon)

        response = self.delete(force_params=url_params)
        assert response.status_code == expected_response
        if expected_response == HTTP_204_NO_CONTENT:
            comment = Comment.objects.get(record_card=record_card, reason_id=Reason.RECORDFILE_DELETED)
            assert record_file.filename in comment.comment

    def given_an_object(self, tmpdir_factory, record_card):
        return {"id": self.create_file(tmpdir_factory, record_card, 1).pk}


class TestRecordCardFilters(CreateRecordCardMixin, OpenAPIResourceListMixin, BaseOpenAPITest):
    path = "/record_cards/record_cards/"
    base_api_path = "/services/iris/api"
    use_extra_get_params = True

    @pytest.mark.parametrize("object_number", (0, 1, 3))
    def test_list(self, object_number):
        [self.create_record_card() for _ in range(0, object_number)]
        response = self.list(force_params={"page_size": self.paginate_by, "state": RecordState.PENDING_VALIDATE})
        self.should_return_list(object_number, self.paginate_by, response)

    @pytest.mark.parametrize("citizen_dni,social_entity_cif,record_card_id,count_retrieve", (
        ("", "", True, 1),
        ("48755987P", "", False, 1),
        ("", "G78459862", False, 1),
        ("", "G78459862", True, 1),
    ))
    def test_identifier_filter(self, citizen_dni, social_entity_cif, record_card_id, count_retrieve):
        record_card = self.create_record_card(citizen_dni=citizen_dni, social_entity_cif=social_entity_cif)
        self.set_group_permissions("user_id", record_card.responsible_profile, [RECARD_SEARCH_NOFILTERS])
        params = {"page_size": self.paginate_by}
        if record_card_id:
            params.update({"normalized_record_id": record_card.normalized_record_id,
                           "normalized_record_id_lookup": "iexact"})
        if citizen_dni:
            params.update({"applicant_dni": record_card.request.applicant.citizen.dni,
                           "applicant_dni_lookup": "exact"})
        response = self.list(force_params=params)
        self.should_return_list(count_retrieve, self.paginate_by, response)


class TestRequest(BaseOpenAPICRUResourceTest):
    path = "/record_cards/requests/"
    base_api_path = "/services/iris/api"

    def get_default_data(self):
        input_channel = mommy.make(InputChannel, user_id="222")
        media_type = mommy.make(MediaType, user_id="222")
        citizen = mommy.make(Citizen, user_id="2222")
        return {
            "applicant_id": mommy.make(Applicant, user_id="222", citizen=citizen).pk,
            "applicant_type": ApplicantType.CIUTADA,
            "application": mommy.make(Application, user_id="222").pk,
            "input_channel": input_channel.pk,
            "communication_media": mommy.make(CommunicationMedia, user_id="222", input_channel=input_channel,
                                              media_type=media_type).pk,
            "user_id": "22222"
        }

    def given_create_rq_data(self):
        input_channel = mommy.make(InputChannel, user_id="222")
        media_type = mommy.make(MediaType, user_id="222")
        citizen = mommy.make(Citizen, user_id="2222")
        return {
            "applicant_id": mommy.make(Applicant, user_id="222", citizen=citizen).pk,
            "applicant_type": ApplicantType.CIUTADA,
            "application": mommy.make(Application, user_id="222").pk,
            "input_channel": input_channel.pk,
            "communication_media": mommy.make(CommunicationMedia, user_id="222", input_channel=input_channel,
                                              media_type=media_type).pk,
            "user_id": "22222"
        }

    def when_data_is_invalid(self, data):
        data["applicant_id"] = None


class TestRecordCardGroupManagementIndicatorsView(DictListGetMixin, CreateRecordCardMixin, BaseOpenAPITest):
    path = "/record_cards/record_cards/summary/"
    base_api_path = "/services/iris/api"

    def test_get_summary(self):
        _, parent, _, _, _, _ = create_groups()
        self.set_group_permissions("user_id", parent, [RECARD_CHARTS])
        today = timezone.now() + timedelta(hours=3)
        previous_date = today - timedelta(days=1)
        next_date = today + timedelta(days=1)
        next_week_date = today + timedelta(days=8)

        urgent = [True, False, True, False, True, False, True, False, True, False]
        ans_limit_dates = [today, previous_date, next_date, next_week_date, today, next_date, previous_date, next_date,
                           today, next_week_date]
        record_states = [RecordState.PENDING_VALIDATE, RecordState.IN_RESOLUTION, RecordState.CLOSED,
                         RecordState.EXTERNAL_RETURNED, RecordState.IN_PLANING, RecordState.CLOSED,
                         RecordState.PENDING_VALIDATE, RecordState.IN_RESOLUTION, RecordState.CLOSED,
                         RecordState.PENDING_VALIDATE]

        for index, record_state in enumerate(record_states):
            nearexpire = ans_limit_dates[index] - timedelta(days=2)
            self.create_record_card(record_state_id=record_state, urgent=urgent[index], responsible_profile=parent,
                                    ans_limit_date=ans_limit_dates[index], ans_limit_nearexpire=nearexpire)
        response = self.dict_list_retrieve()
        assert response.status_code == HTTP_200_OK
        summary = response.json()
        assert summary["urgent"] == 3
        assert summary["expired"] == 2
        assert summary["near_expire"] == 3
        assert summary["pending_validation"] == 4
        assert summary["processing"] == 3

    def prepare_path(self, path, path_spec, force_params=None):
        """
        :param path: Relative URI of the operation.
        :param path_spec: OpenAPI spec as dict for part.
        :param force_params: Explicitly force params.
        :return: Path for performing a request to the given OpenAPI path.
        """
        return "{}{}".format(self.base_api_path, path)


class TestRecordCardAmbitManagementIndicatorsView(DictListGetMixin, CreateRecordCardMixin, BaseOpenAPITest):
    path = "/record_cards/record_cards/summary/ambit/{group_id}/"
    base_api_path = "/services/iris/api"

    def test_get_ambit_summary(self):
        _, parent, soon, soon2, noambit_parent, _ = create_groups()
        self.set_group_permissions("user_id", parent, [RECARD_CHARTS])
        today = timezone.now() + timedelta(hours=3)
        previous_date = today - timedelta(days=1)
        next_date = today + timedelta(days=1)
        next_week_date = today + timedelta(days=8)

        ans_limit_dates = [today, previous_date, next_date, next_week_date, today, next_date, previous_date, next_date,
                           today, next_week_date]
        record_states = [RecordState.PENDING_VALIDATE, RecordState.IN_RESOLUTION, RecordState.CLOSED,
                         RecordState.EXTERNAL_RETURNED, RecordState.IN_PLANING, RecordState.CLOSED,
                         RecordState.PENDING_VALIDATE, RecordState.IN_RESOLUTION, RecordState.CLOSED,
                         RecordState.PENDING_VALIDATE]
        responsibles = [parent, soon, soon2, noambit_parent, parent, soon, soon2, noambit_parent, soon, noambit_parent]

        for index, record_state in enumerate(record_states):
            nearexpire = ans_limit_dates[index] - timedelta(days=2)
            self.create_record_card(record_state_id=record_state, ans_limit_date=ans_limit_dates[index],
                                    responsible_profile=responsibles[index], ans_limit_nearexpire=nearexpire)

        response = self.dict_list_retrieve(force_params={"group_id": parent.pk})

        assert response.status_code == HTTP_200_OK
        summary = response.json()
        assert summary["expired"] == 2
        assert summary["near_expire"] == 2
        assert summary["pending_validation"] == 2
        assert summary["processing"] == 2
        assert len(summary["childrens"]) == 2
        for children in summary["childrens"]:
            assert children["group_name"]
            if children["group_id"] == soon.pk:
                assert children["expired"] == 1
                assert children["near_expire"] == 0
                assert children["pending_validation"] == 0
                assert children["processing"] == 1
            elif children["group_id"] == soon2.pk:
                assert children["expired"] == 1
                assert children["near_expire"] == 0
                assert children["pending_validation"] == 1
                assert children["processing"] == 0


class TestRecordCardGroupMonthIndicatorsView(DictListGetMixin, CreateRecordCardMixin, SetUserGroupMixin,
                                             BaseOpenAPITest):
    path = "/record_cards/record_cards/month-summary/{year}/{month}/"
    base_api_path = "/services/iris/api"

    def test_current_month_summary(self):
        dair, parent, _, _, _, _ = create_groups()
        self.set_group_permissions("user_id", parent, [RECARD_CHARTS])
        urgent = [True, False, True, False, True, False, True, False, True, False]
        previous_created = [False, True, True, False, True, False, True, False, False, True]
        record_states = [RecordState.PENDING_VALIDATE, RecordState.IN_RESOLUTION, RecordState.CLOSED,
                         RecordState.EXTERNAL_RETURNED, RecordState.IN_PLANING, RecordState.CLOSED,
                         RecordState.PENDING_VALIDATE, RecordState.IN_RESOLUTION, RecordState.CLOSED,
                         RecordState.EXTERNAL_PROCESSING]

        for index, record_state in enumerate(record_states):
            record_card = self.create_record_card(record_state_id=record_state, urgent=urgent[index],
                                                  previous_created_at=previous_created[index],
                                                  responsible_profile=parent)
            RecordCardReasignation.objects.create(record_card=record_card, group=dair,
                                                  previous_responsible_profile=dair,
                                                  next_responsible_profile=parent,
                                                  reason_id=Reason.DERIVATE_RESIGNATION,
                                                  comment="Automatic reasignation by derivation")
            if record_states != RecordState.PENDING_VALIDATE:
                RecordCardStateHistory.objects.create(group=parent, record_card=record_card,
                                                      previous_state_id=RecordState.PENDING_VALIDATE,
                                                      next_state_id=record_state)
        average_close_days, average_age_days = 4, 5
        today = timezone.now()
        month_states_counts = Mock(return_value=(average_close_days, average_age_days))
        with patch("record_cards.views.RecordCardGroupMonthIndicatorsView.get_current_month_averages",
                   month_states_counts):
            response = self.dict_list_retrieve(force_params={"year": today.year, "month": today.month})

            assert response.status_code == HTTP_200_OK
            summary = response.json()

            assert summary["pending_validation"] == 3
            assert summary["processing"] == 3
            assert summary["closed"] == 3
            assert summary["cancelled"] == 0
            assert summary["external_processing"] == 1
            assert summary["pending_records"] == 6
            assert summary["average_close_days"] == average_close_days
            assert summary["average_age_days"] == average_age_days
            assert summary["entries"] == 10

    def test_previous_month_not_indicators(self):
        _, parent, _, _, _, _ = create_groups()
        self.set_usergroup(parent)
        self.set_group_permissions("user_id", parent, [RECARD_CHARTS])
        response = self.dict_list_retrieve(force_params={"year": 2019, "month": 1})
        assert response.status_code == HTTP_200_OK
        summary = response.json()

        indicators = ["pending_validation", "processing", "closed", "cancelled", "external_processing",
                      "pending_records", "average_close_days", "average_age_days", "entries"]
        for indicator in indicators:
            assert summary[indicator] == 0

    def test_previous_month_indicator(self):
        _, parent, _, _, _, _ = create_groups()
        self.set_usergroup(parent)
        self.set_group_permissions("user_id", parent, [RECARD_CHARTS])
        year = 2019
        month = 3

        indicators = {
            "pending_validation": 3, "processing": 4, "closed": 3, "cancelled": 1, "external_processing": 1,
            "pending_records": 8, "average_close_days": 23, "average_age_days": 10, "group": parent, "year": year,
            "month": month, "entries": 6}
        MonthIndicator.objects.create(**indicators)

        response = self.dict_list_retrieve(force_params={"year": year, "month": month})
        assert response.status_code == HTTP_200_OK
        summary = response.json()

        assert summary["pending_validation"] == indicators["pending_validation"]
        assert summary["processing"] == indicators["processing"]
        assert summary["closed"] == indicators["closed"]
        assert summary["cancelled"] == indicators["cancelled"]
        assert summary["external_processing"] == indicators["external_processing"]
        assert summary["pending_records"] == indicators["pending_records"]
        assert summary["average_close_days"] == indicators["average_close_days"]
        assert summary["average_age_days"] == indicators["average_age_days"]
        assert summary["entries"] == indicators["entries"]


class TestRecordCardAmbitMonthIndicatorsView(TestRecordCardGroupMonthIndicatorsView):
    path = "/record_cards/record_cards/month-summary/ambit/{year}/{month}/"
    base_api_path = "/services/iris/api"


class TestCalculateMonthIndicatorsView(PostOperationMixin, BaseOpenAPITest):
    path = "/record_cards/record_cards/calculate-month-indicators/{year}/{month}/"
    base_api_path = "/services/iris/api"

    def test_calculate_month_indicators(self):
        with patch("record_cards.tasks.calculate_month_indicators.delay") as mock_delay:
            response = self.post(force_params={"year": 2019, "month": 10})
            assert response.status_code == HTTP_204_NO_CONTENT
            mock_delay.assert_called_once()


class TestRecordCardPossibleSimilarTaskView(DictListGetMixin, CreateRecordCardMixin, BaseOpenAPITest):
    path = "/record_cards/record_cards/possible-similars-task/"
    base_api_path = "/services/iris/api"

    @pytest.mark.parametrize("object_number", (0, 1, 3))
    def test_ambit_task(self, object_number):
        [self.create_record_card() for _ in range(object_number)]

        delay = "record_cards.record_actions.record_set_possible_similar.register_possible_similar_records.delay"
        with patch(delay) as mock_delay:
            response = self.dict_list_retrieve()
            assert response.status_code == HTTP_200_OK
            assert mock_delay.call_count == object_number
            if object_number > 0:
                mock_delay.assert_called()


class RecordCardActionsMixin(PostOperationMixin, CreateRecordCardMixin, SetUserGroupMixin, PreparePathIDMixin):
    base_api_path = "/services/iris/api"


class RecordCardRestrictedTestMixin(CreateRecordCardMixin, SetUserGroupMixin, SetPermissionMixin):
    action_permission = None

    @pytest.mark.parametrize("can_tramit,mayorship_permission,mayorship,expected_response", (
        (False, True, True, HTTP_403_FORBIDDEN),
        (False, True, False, HTTP_403_FORBIDDEN),
        (False, False, True, HTTP_403_FORBIDDEN),
        (True, False, True, HTTP_204_NO_CONTENT),
        (True, False, False, HTTP_204_NO_CONTENT),
    ))
    def test_mayorship_action(self, can_tramit, mayorship_permission, mayorship, expected_response):
        record_kwargs = {
            "record_state_id": self.get_record_state_id(),
            "process_pk": Process.EXTERNAL_PROCESSING,
            "mayorship": mayorship
        }
        if mayorship_permission:
            record_kwargs["responsible_profile"] = self.set_permission(MAYORSHIP)
        else:
            record_kwargs["responsible_profile"] = mommy.make(
                Group,
                profile_ctrl_user_id="GRP102",
                user_id="2222",
                group_plate="YY",
            )

        if not can_tramit:
            self.set_usergroup(mommy.make(
                Group,
                parent=record_kwargs.get("responsible_profile") if mayorship_permission else None,
                profile_ctrl_user_id="GRP0002",
                user_id="2222",
                group_plate="XX_XX",
            ))
        record_card = self.create_record_card(**record_kwargs)
        self.add_action_permission()
        response = self.post(force_params=self.get_post_params(record_card))
        assert response.status_code == expected_response

    @cached_property
    def non_tramit_group(self):
        return mommy.make(Group, user_id='TEST', profile_ctrl_user_id='TEST', parent=None)

    @pytest.mark.parametrize("responsible_group,action_group,expected_response", (
        (2, 1, HTTP_204_NO_CONTENT),
        (2, 2, HTTP_204_NO_CONTENT),
        (2, 3, HTTP_403_FORBIDDEN),
    ))
    def test_can_tramit_action(self, responsible_group, action_group, expected_response):
        groups = dict_groups()
        record_kwargs = {
            "record_state_id": self.get_record_state_id(),
            "process_pk": Process.EXTERNAL_PROCESSING,
            "responsible_profile": groups[responsible_group]
        }
        self.set_usergroup(groups[action_group])
        self.set_group_permissions("user_id", groups[action_group])
        record_card = self.create_record_card(**record_kwargs)
        self.add_action_permission()
        response = self.post(force_params=self.get_post_params(record_card))
        assert response.status_code == expected_response

    def get_record_state_id(self):
        return RecordState.PENDING_VALIDATE

    def get_post_params(self, record_card):
        return {"id": record_card.pk}

    def add_action_permission(self):
        if self.action_permission:
            self.set_group_permissions("user_id", self.user.usergroup.group, [self.action_permission])


class TestToogleRecordCardUrgency(UpdatePatchMixin, RecordCardActionsMixin, SetPermissionMixin,
                                  BaseOpenAPITest):
    detail_path = "/record_cards/record_cards/{id}/toogle-urgency/"
    base_api_path = "/services/iris/api"

    @pytest.mark.parametrize("urgent,new_urgency", (
        (True, True),
        (True, False),
        (False, True),
        (False, False),
    ))
    def test_urgency_toogle_record_card(self, urgent, new_urgency):
        record_card = self.create_record_card(urgent)
        response = self.patch(force_params={"id": record_card.pk, "urgent": new_urgency})
        record_card = RecordCard.objects.get(pk=record_card.pk)
        assert response.status_code == HTTP_200_OK
        assert record_card.urgent is new_urgency
        assert record_card.alarm is new_urgency
        comment = Comment.objects.get(record_card=record_card, reason_id=Reason.RECORDCARD_URGENCY_CHANGE)
        if new_urgency:
            assert "NO" not in comment.comment
        else:
            assert "NO" in comment.comment

    @pytest.mark.parametrize("state_id", (RecordState.CLOSED, RecordState.CANCELLED))
    def test_urgency_toogle_closed_states(self, state_id):
        record_card = self.create_record_card(record_state_id=RecordState.CANCELLED)
        response = self.patch(force_params={"id": record_card.pk, "urgent": True})
        assert response.status_code == HTTP_409_CONFLICT

    @pytest.mark.parametrize("mayorship_permission,mayorship,expected_response", (
        (True, True, HTTP_200_OK),
        (True, False, HTTP_200_OK),
        (False, True, HTTP_200_OK),
        (False, False, HTTP_200_OK),
    ))
    def test_mayorship_action(self, mayorship_permission, mayorship, expected_response):
        record_kwargs = {
            "record_state_id": RecordState.PENDING_VALIDATE,
            "process_pk": Process.EXTERNAL_PROCESSING,
            "mayorship": mayorship
        }
        if mayorship_permission:
            record_kwargs["responsible_profile"] = self.set_permission(MAYORSHIP)

        record_card = self.create_record_card(**record_kwargs)
        response = self.patch(force_params={"id": record_card.pk, "urgent": True})
        assert response.status_code == expected_response

    @pytest.mark.parametrize("responsible_group,action_group,expected_response", (
        (2, 1, HTTP_200_OK),
        (2, 2, HTTP_200_OK),
        (2, 3, HTTP_403_FORBIDDEN),
    ))
    def test_can_tramit_action(self, responsible_group, action_group, expected_response):
        groups = dict_groups()
        record_kwargs = {
            "record_state_id": RecordState.PENDING_VALIDATE,
            "process_pk": Process.EXTERNAL_PROCESSING,
            "responsible_profile": groups[responsible_group]
        }
        self.set_usergroup(groups[action_group])
        record_card = self.create_record_card(**record_kwargs)
        response = self.patch(force_params={"id": record_card.pk, "urgent": True})
        assert response.status_code == expected_response


class TestRecordCardValidate(RecordCardActionsMixin, CreateDerivationsMixin, RecordCardRestrictedTestMixin,
                             BaseOpenAPITest):
    path = "/record_cards/record_cards/{id}/validate/"

    @pytest.mark.parametrize(
        "initial_record_state_id,process_id,new_record_state_id,can_be_validated,expected_response,delete_permissions",
        (
            (RecordState.PENDING_VALIDATE, Process.CLOSED_DIRECTLY, RecordState.CLOSED, True,
             HTTP_204_NO_CONTENT, False),
            (RecordState.PENDING_VALIDATE, Process.CLOSED_DIRECTLY, None, True, HTTP_403_FORBIDDEN, True),
            (RecordState.PENDING_VALIDATE, Process.EXTERNAL_PROCESSING, RecordState.EXTERNAL_PROCESSING,
             True, HTTP_204_NO_CONTENT, False),
            (RecordState.PENDING_VALIDATE, Process.EVALUATION_RESOLUTION_RESPONSE, RecordState.IN_PLANING,
             True, HTTP_204_NO_CONTENT, False),
            (RecordState.EXTERNAL_RETURNED, Process.EXTERNAL_PROCESSING, RecordState.EXTERNAL_PROCESSING,
             True, HTTP_204_NO_CONTENT, False),
            (RecordState.EXTERNAL_RETURNED, Process.EXTERNAL_PROCESSING, None, True, HTTP_403_FORBIDDEN, True),
            (RecordState.IN_PLANING, None, None, False, HTTP_404_NOT_FOUND, False)
        ))
    def test_validate_record_card(self, initial_record_state_id, process_id, new_record_state_id, can_be_validated,
                                  expected_response, delete_permissions):
        record_card = self.create_record_card(initial_record_state_id, process_pk=process_id)
        validated = PropertyMock(return_value=can_be_validated)
        user_department = "test"
        with patch("record_cards.models.RecordCard.can_be_validated", validated):
            if new_record_state_id:
                derivated_profile = self.create_direct_derivation(record_card.element_detail_id, new_record_state_id)
            else:
                derivated_profile = record_card.responsible_profile

            if delete_permissions:
                GroupProfiles.objects.all().delete()

            response = self.post(force_params={"id": record_card.pk})
            assert response.status_code == expected_response

            if new_record_state_id:
                record_card = RecordCard.objects.get(pk=record_card.pk)
                assert record_card.record_state_id == new_record_state_id
                assert Workflow.objects.get(main_record_card=record_card).state_id == new_record_state_id
                assert RecordCardStateHistory.objects.get(record_card=record_card, next_state_id=new_record_state_id,
                                                          automatic=False)
                if record_card.process_id == Process.CLOSED_DIRECTLY:
                    assert record_card.close_department == self.user.imi_data['dptcuser']
                    assert record_card.closing_date
            else:
                assert RecordCard.objects.get(pk=record_card.pk).record_state_id == initial_record_state_id
            assert record_card.responsible_profile == derivated_profile

    def test_with_external_validator(self):
        record_card = self.create_record_card(RecordState.PENDING_VALIDATE, process_pk=Process.EXTERNAL_PROCESSING)
        external_validator = DummyExternalValidator(record_card)
        get_external_validator = Mock(return_value=external_validator)
        with patch("record_cards.views.get_external_validator", get_external_validator):
            resp = self.post(force_params={"id": record_card.pk})
            assert resp.status_code == HTTP_204_NO_CONTENT
            assert external_validator.validated

    @pytest.mark.parametrize(
        "initial_record_state_id,process_id,create_similar,similar_enabled,expected_response", (
            (RecordState.PENDING_VALIDATE, Process.CLOSED_DIRECTLY, True, True, HTTP_409_CONFLICT),
            (RecordState.PENDING_VALIDATE, Process.CLOSED_DIRECTLY, True, False, HTTP_404_NOT_FOUND),
            (RecordState.PENDING_VALIDATE, Process.CLOSED_DIRECTLY, False, True, HTTP_409_CONFLICT),
            (RecordState.PENDING_VALIDATE, Process.EXTERNAL_PROCESSING, True, True, HTTP_409_CONFLICT),
            (RecordState.PENDING_VALIDATE, Process.EXTERNAL_PROCESSING, True, False, HTTP_404_NOT_FOUND),
            (RecordState.EXTERNAL_RETURNED, Process.EXTERNAL_PROCESSING, False, True, HTTP_409_CONFLICT),
            (RecordState.EXTERNAL_RETURNED, Process.EXTERNAL_PROCESSING, True, True, HTTP_409_CONFLICT),
            (RecordState.EXTERNAL_RETURNED, Process.EXTERNAL_PROCESSING, True, False, HTTP_404_NOT_FOUND),
            (RecordState.PENDING_VALIDATE, Process.EXTERNAL_PROCESSING, False, True, HTTP_409_CONFLICT),
            (RecordState.PENDING_VALIDATE, Process.EVALUATION_RESOLUTION_RESPONSE, True, True, HTTP_204_NO_CONTENT),
            (RecordState.PENDING_VALIDATE, Process.EVALUATION_RESOLUTION_RESPONSE, True, False, HTTP_404_NOT_FOUND),
            (RecordState.PENDING_VALIDATE, Process.EVALUATION_RESOLUTION_RESPONSE, False, True, HTTP_409_CONFLICT),
        ))
    def test_validate_record_card_similar(self, initial_record_state_id, process_id, create_similar, similar_enabled,
                                          expected_response):
        _, _, _, second_soon, _, _ = create_groups()
        element_detail = self.create_element_detail(similarity_hours=5, similarity_meters=5000, process_id=process_id)

        ubication = Ubication.objects.create(via_type="carrer", street="test", xetrs89a=427236.69, yetrs89a=4582247.42)
        record_card = self.create_record_card(initial_record_state_id, element_detail=element_detail,
                                              ubication=ubication, responsible_profile=second_soon)

        force_params = {
            "id": record_card.pk,
        }
        if create_similar:
            possible_similar = self.create_record_card(element_detail=record_card.element_detail,
                                                       enabled=similar_enabled, ubication=ubication,
                                                       record_state_id=record_card.next_step_code,
                                                       responsible_profile=record_card.responsible_profile)
        else:
            possible_similar = self.create_record_card()
        Workflow.objects.create(main_record_card=possible_similar, state_id=possible_similar.record_state_id)
        force_params["similar"] = possible_similar.pk

        validated = PropertyMock(return_value=True)
        with patch("record_cards.models.RecordCard.can_be_validated", validated):
            response = self.post(force_params=force_params)
            assert response.status_code == expected_response
            if expected_response == HTTP_204_NO_CONTENT:
                record_card = RecordCard.objects.get(pk=record_card.pk)
                if create_similar:
                    assert record_card.workflow_id == possible_similar.workflow_id
                    assert record_card.record_state_id == possible_similar.record_state_id
                else:
                    assert Workflow.objects.get(main_record_card=record_card).state_id == record_card.record_state_id

    @pytest.mark.parametrize("has_permission,same_ambit_responsible,expected_response", (
        (True, True, HTTP_204_NO_CONTENT),
        (True, False, HTTP_204_NO_CONTENT),
        (False, True, HTTP_204_NO_CONTENT),
        (False, False, HTTP_409_CONFLICT),
    ))
    def test_validate_record_card_similar_ambit_permission(self, has_permission, same_ambit_responsible,
                                                           expected_response):
        grand_parent, parent, first_soon, second_soon, noambit_parent, noambit_soon = create_groups()

        element_detail = self.create_element_detail(similarity_hours=5, similarity_meters=5000,
                                                    fill_active_mandatory_fields=False,
                                                    process_id=Process.EVALUATION_RESOLUTION_RESPONSE, )

        ubication = Ubication.objects.create(via_type="carrer", street="test", xetrs89a=427236.69, yetrs89a=4582247.42)
        record_card = self.create_record_card(responsible_profile=second_soon, element_detail=element_detail,
                                              ubication=ubication)

        if has_permission:
            self.set_group_permissions("user_id", second_soon, [RECARD_VALIDATE_OUTAMBIT])

        possible_similar_responsible = parent if same_ambit_responsible else noambit_parent
        possible_ubication = Ubication.objects.create(via_type="carrer", street="test", xetrs89a=426053.09,
                                                      yetrs89a=4583681.06)
        possible_similar = self.create_record_card(element_detail=record_card.element_detail,
                                                   responsible_profile=possible_similar_responsible,
                                                   record_state_id=RecordState.IN_RESOLUTION,
                                                   ubication=possible_ubication)
        force_params = {"id": record_card.pk, "similar": possible_similar.pk}
        validated = PropertyMock(return_value=True)
        with patch("record_cards.models.RecordCard.can_be_validated", validated):
            response = self.post(force_params=force_params)
            assert response.status_code == expected_response

    @pytest.mark.parametrize("possible_similar", (0, 1, 10))
    def test_validate_register_possible_similar(self, possible_similar):
        _, _, _, second_soon, _, _ = create_groups()
        ubication = Ubication.objects.create(via_type="carrer", street="test", xetrs89a=427236.69, yetrs89a=4582247.42)
        element_detail = self.create_element_detail(similarity_hours=5, similarity_meters=5000,
                                                    process_id=Process.EVALUATION_RESOLUTION_RESPONSE)
        record_card = self.create_record_card(element_detail=element_detail, ubication=ubication,
                                              responsible_profile=second_soon)

        [self.create_record_card(element_detail=record_card.element_detail,
                                 enabled=True, ubication=ubication,
                                 record_state_id=RecordState.PENDING_ANSWER,
                                 responsible_profile=record_card.responsible_profile) for _ in range(possible_similar)]
        record_card.set_similar_records()

        with patch("record_cards.tasks.register_possible_similar_records.delay") as mock_delay:
            response = self.post(force_params={"id": record_card.pk})
            assert response.status_code == HTTP_204_NO_CONTENT
            assert mock_delay.called

    def get_post_params(self, record_card):
        return super().get_post_params(record_card)

    def test_automatically_closed(self):
        record_card = self.create_record_card(RecordState.PENDING_VALIDATE, create_record_card_response=True,
                                              process_pk=Process.RESPONSE)
        record_card.recordcardresponse.response_channel_id = ResponseChannel.NONE
        record_card.recordcardresponse.save()

        response = self.post(force_params={"id": record_card.pk})

        assert response.status_code == HTTP_204_NO_CONTENT
        record_card = RecordCard.objects.get(pk=record_card.pk)
        assert record_card.record_state_id == RecordState.CLOSED
        assert Comment.objects.get(record_card=record_card, reason=Reason.RECORDCARD_AUTOMATICALLY_CLOSED)

    def test_validation_user_audit(self):
        record_card = self.create_record_card(RecordState.PENDING_VALIDATE, create_record_card_response=True,
                                              process_pk=Process.RESPONSE)
        response = self.post(force_params={"id": record_card.pk})

        assert response.status_code == HTTP_204_NO_CONTENT
        assert RecordCardAudit.objects.get(record_card=record_card).validation_user


class TestRecordCardValidateCheck(RecordCardActionsMixin, CreateDerivationsMixin, BaseOpenAPITest):
    path = "/record_cards/record_cards/{id}/validate/check/"

    @pytest.mark.parametrize(
        "initial_record_state_id,process_id,can_be_validated,create_derivation,similars,expected_response", (
            (RecordState.PENDING_VALIDATE, Process.CLOSED_DIRECTLY, True, True, 2, HTTP_200_OK),
            (RecordState.PENDING_VALIDATE, Process.CLOSED_DIRECTLY, True, False, 4, HTTP_200_OK),
            (RecordState.PENDING_VALIDATE, Process.CLOSED_DIRECTLY, False, True, 0, HTTP_200_OK),
            (RecordState.PENDING_VALIDATE, Process.CLOSED_DIRECTLY, False, False, 1, HTTP_200_OK),
            (RecordState.PENDING_VALIDATE, Process.EXTERNAL_PROCESSING, True, True, 3, HTTP_200_OK),
            (RecordState.PENDING_VALIDATE, Process.EXTERNAL_PROCESSING, True, False, 6, HTTP_200_OK),
            (RecordState.PENDING_VALIDATE, Process.EXTERNAL_PROCESSING, False, True, 2, HTTP_200_OK),
            (RecordState.PENDING_VALIDATE, Process.EXTERNAL_PROCESSING, False, False, 9, HTTP_200_OK),
            (RecordState.EXTERNAL_RETURNED, Process.EXTERNAL_PROCESSING, True, True, 3, HTTP_200_OK),
            (RecordState.EXTERNAL_RETURNED, Process.EXTERNAL_PROCESSING, True, False, 6, HTTP_200_OK),
            (RecordState.EXTERNAL_RETURNED, Process.EXTERNAL_PROCESSING, False, True, 2, HTTP_200_OK),
            (RecordState.EXTERNAL_RETURNED, Process.EXTERNAL_PROCESSING, False, False, 9, HTTP_200_OK),
            (RecordState.PENDING_VALIDATE, Process.EVALUATION_RESOLUTION_RESPONSE, True, True, 5, HTTP_200_OK),
            (RecordState.PENDING_VALIDATE, Process.EVALUATION_RESOLUTION_RESPONSE, True, False, 4, HTTP_200_OK),
            (RecordState.PENDING_VALIDATE, Process.EVALUATION_RESOLUTION_RESPONSE, False, True, 3, HTTP_200_OK),
            (RecordState.PENDING_VALIDATE, Process.EVALUATION_RESOLUTION_RESPONSE, False, False, 2, HTTP_200_OK),
            (RecordState.IN_RESOLUTION, None, False, True, 0, HTTP_404_NOT_FOUND),
        ))
    def test_check_validate_record_card(self, initial_record_state_id, process_id, can_be_validated, create_derivation,
                                        similars, expected_response):
        _, _, _, second_soon, _, _ = create_groups()
        element_detail = self.create_element_detail(similarity_hours=5, similarity_meters=5000, process_id=process_id,
                                                    validation_place_days=8)

        ubication = Ubication.objects.create(via_type="carrer", street="test", xetrs89a=427236.69, yetrs89a=4582247.42)
        record_card = self.create_record_card(initial_record_state_id, element_detail=element_detail,
                                              ubication=ubication)
        conversation_pk = mommy.make(Conversation, record_card=record_card, is_opened=True, user_id="2222").pk
        validated = PropertyMock(return_value=can_be_validated)

        if create_derivation and process_id:
            self.create_direct_derivation(record_card.element_detail_id, record_card.next_step_code)

        for _ in range(similars):
            record_card.possible_similar.add(self.create_record_card(
                element_detail=record_card.element_detail, record_state_id=RecordState.PENDING_ANSWER,
                ubication=ubication, responsible_profile=record_card.responsible_profile, create_worflow=True))

        with patch("record_cards.models.RecordCard.can_be_validated", validated):
            assert record_card.can_be_validated is can_be_validated
            response = self.post(force_params={"id": record_card.pk})
            assert response.status_code == expected_response
            if expected_response == HTTP_200_OK:
                json_response = response.json()
                record_card = RecordCard.objects.get(pk=record_card.pk)
                assert record_card.record_state_id == initial_record_state_id
                assert len(json_response.keys()) == 1
                assert json_response["__action__"]["can_confirm"] is can_be_validated
                assert json_response["__action__"]["different_ambit"] is False
                assert json_response["__action__"]["next_state"] == record_card.next_step_code
                if create_derivation and process_id:
                    derivate_group = record_card.derivate(record_card.user_id, is_check=True,
                                                          next_state_id=record_card.next_step_code)
                else:
                    derivate_group = None
                next_group_id = derivate_group.pk if derivate_group else record_card.responsible_profile_id
                assert json_response["__action__"]["next_group"]["id"] == next_group_id
                if can_be_validated:
                    assert json_response["__action__"]["reason"] is None
                else:
                    assert isinstance(json_response["__action__"]["reason"], str)
                assert len(json_response["__action__"]["possible_similar"]) == similars
                conversation = Conversation.objects.get(pk=conversation_pk)
                assert conversation.is_opened is True

    def test_posible_similars(self):
        _, _, _, second_soon, _, _ = create_groups()
        element_detail = self.create_element_detail(similarity_hours=5, similarity_meters=5000,
                                                    process_id=Process.EVALUATION_RESOLUTION_RESPONSE,
                                                    validation_place_days=8)

        ubication = Ubication.objects.create(via_type="carrer", street="test", xetrs89a=427236.69, yetrs89a=4582247.42)
        record_card = self.create_record_card(RecordState.PENDING_VALIDATE, element_detail=element_detail,
                                              ubication=ubication)
        validated = PropertyMock(return_value=True)

        main_record_card = self.create_record_card(
            element_detail=record_card.element_detail, record_state_id=RecordState.PENDING_ANSWER,
            ubication=ubication, responsible_profile=record_card.responsible_profile, create_worflow=True)
        record_card.possible_similar.add(main_record_card)
        for _ in range(3):
            rec = self.create_record_card(element_detail=record_card.element_detail,
                                          record_state_id=RecordState.PENDING_ANSWER, ubication=ubication,
                                          responsible_profile=record_card.responsible_profile)
            rec.worflow = main_record_card.workflow
            rec.save()
            record_card.possible_similar.add(rec)

        with patch("record_cards.models.RecordCard.can_be_validated", validated):
            response = self.post(force_params={"id": record_card.pk})
            possible_similar_records = response.json()["__action__"]["possible_similar"]
            assert len(possible_similar_records) == 1
            assert possible_similar_records[0]["normalized_record_id"] == main_record_card.normalized_record_id


class TestRecordCardThemeChangeView(RecordCardActionsMixin, CreateRecordCardMixin, FeaturesMixin,
                                    RemovePermissionCheckerMixin, BaseOpenAPITest):
    path = "/record_cards/record_cards/{id}/theme-change/"

    @pytest.mark.parametrize("change_theme_permission,expected_response", (
        (True, HTTP_204_NO_CONTENT),
        (False, HTTP_403_FORBIDDEN),
    ))
    def test_theme_change_permissions(self, change_theme_permission, expected_response):
        _, parent, _, soon2, noambit_parent, _ = create_groups()
        self.set_usergroup(parent)
        if change_theme_permission:
            self.set_group_permissions("22222", parent, [THEME_CHANGE])
        initial_features = self.create_features(3)
        record_card = self.create_record_card(features=initial_features, create_worflow=True,
                                              reassignment_not_allowed=False,
                                              responsible_profile=parent, claims_number=2,
                                              record_state_id=RecordState.PENDING_VALIDATE)
        element_detail = self.create_element_detail(element=record_card.element_detail.element)
        features = self.create_features(3)
        for feature in features:
            ElementDetailFeature.objects.create(element_detail=element_detail, feature=feature, is_mandatory=True)
        DerivationDirect.objects.create(element_detail=element_detail, record_state_id=RecordState.PENDING_VALIDATE,
                                        group=soon2)
        element_detail.register_theme_ambit()

        rq_data = {
            "id": record_card.pk,
            "element_detail_id": element_detail.pk,
            "features": [{"feature": f.pk, "value": str(random.randint(0, 99))} for f in features if not f.is_special],
            "special_features": [{"feature": f.pk, "value": str(random.randint(0, 99))}
                                 for f in features if f.is_special],
            "perform_derivation": True
        }
        self.remove_permission_checker()
        response = self.post(force_params=rq_data)
        assert response.status_code == expected_response

    def test_theme_no_change(self):
        _, parent, _, soon2, noambit_parent, _ = create_groups()
        self.set_usergroup(parent)
        self.set_group_permissions("22222", parent, [THEME_CHANGE])
        features = self.create_features(3)
        record_card = self.create_record_card(features=features, create_worflow=True,
                                              reassignment_not_allowed=False,
                                              responsible_profile=parent, claims_number=2,
                                              record_state_id=RecordState.PENDING_VALIDATE)
        DerivationDirect.objects.create(element_detail=record_card.element_detail,
                                        record_state_id=RecordState.PENDING_VALIDATE, group=soon2)
        rq_data = {
            "id": record_card.pk,
            "element_detail_id": record_card.element_detail_id,
            "features": [{"feature": f.pk, "value": str(random.randint(0, 99))} for f in features if not f.is_special],
            "special_features": [{"feature": f.pk, "value": str(random.randint(0, 99))}
                                 for f in features if f.is_special],
            "perform_derivation": True
        }
        self.remove_permission_checker()
        response = self.post(force_params=rq_data)
        assert response.status_code == HTTP_400_BAD_REQUEST

        record_card = RecordCard.objects.get(pk=record_card.pk)
        assert record_card.workflow.element_detail_modified is False
        assert RecordCardFeatures.objects.filter(
            record_card_id=record_card.pk, enabled=True).count() == len(features)
        assert RecordCardFeatures.objects.filter(
            record_card_id=record_card.pk, enabled=True, is_theme_feature=True).count() == len(features)
        assert RecordCardFeatures.objects.filter(
            record_card_id=record_card.pk, enabled=True, is_theme_feature=False).count() == 0

    @pytest.mark.parametrize("change_features,original_features,theme_features,expected_response", (
        (True, 3, 3, HTTP_204_NO_CONTENT),
        (True, 0, 3, HTTP_204_NO_CONTENT),
        (True, 3, 0, HTTP_204_NO_CONTENT),
        (True, 0, 0, HTTP_204_NO_CONTENT),
        (False, 3, 3, HTTP_400_BAD_REQUEST),
    ))
    def test_theme_change_features(self, change_features, original_features, theme_features, expected_response):
        _, parent, _, soon2, noambit_parent, _ = create_groups()
        self.set_usergroup(parent)
        self.set_group_permissions("22222", parent, [THEME_CHANGE])
        initial_features = self.create_features(original_features)
        record_card = self.create_record_card(features=initial_features, create_worflow=True,
                                              reassignment_not_allowed=False,
                                              responsible_profile=parent, claims_number=2,
                                              record_state_id=RecordState.PENDING_VALIDATE)
        element_detail = self.create_element_detail(element=record_card.element_detail.element)
        new_features = self.create_features(theme_features)
        for feature in new_features:
            ElementDetailFeature.objects.create(element_detail=element_detail, feature=feature, is_mandatory=True)
        DerivationDirect.objects.create(element_detail=element_detail, record_state_id=RecordState.PENDING_VALIDATE,
                                        group=soon2)
        element_detail.register_theme_ambit()

        if change_features:
            features = new_features
        else:
            features = initial_features

        rq_data = {
            "id": record_card.pk,
            "element_detail_id": element_detail.pk,
            "features": [{"feature": f.pk, "value": str(random.randint(0, 99))} for f in features if not f.is_special],
            "special_features": [{"feature": f.pk, "value": str(random.randint(0, 99))}
                                 for f in features if f.is_special],
            "perform_derivation": True
        }
        self.remove_permission_checker()
        response = self.post(force_params=rq_data)
        assert response.status_code == expected_response
        if expected_response == HTTP_204_NO_CONTENT:
            assert RecordCardFeatures.objects.filter(
                record_card_id=record_card.pk, enabled=True).count() == original_features + theme_features
            assert RecordCardFeatures.objects.filter(
                record_card_id=record_card.pk, enabled=True, is_theme_feature=True).count() == theme_features
            assert RecordCardFeatures.objects.filter(
                record_card_id=record_card.pk, enabled=True, is_theme_feature=False).count() == original_features

            if change_features and original_features:
                assert Comment.objects.filter(record_card_id=record_card.pk, reason=Reason.FEATURES_THEME_NO_VISIBLES)
            reason_theme_change_id = int(Parameter.get_parameter_by_key("CANVI_DETALL_MOTIU", 19))
            assert Comment.objects.filter(record_card_id=record_card.pk, reason=reason_theme_change_id)

    @pytest.mark.parametrize("perform_derivation,reassignment_not_allowed,claims_number,expected_response", (
        (True, False, 0, HTTP_204_NO_CONTENT),
        (False, False, 0, HTTP_204_NO_CONTENT),
        (None, False, 0, HTTP_204_NO_CONTENT),
        (True, True, 0, HTTP_204_NO_CONTENT),
        (True, False, 10, HTTP_204_NO_CONTENT),
    ))
    def test_record_card_theme_change(self, perform_derivation, reassignment_not_allowed, claims_number,
                                      expected_response):
        _, parent, _, soon2, noambit_parent, _ = create_groups()
        self.set_usergroup(parent)
        self.set_group_permissions("22222", parent, [THEME_CHANGE])

        initial_features = self.create_features(3)
        record_card = self.create_record_card(features=initial_features,
                                              reassignment_not_allowed=reassignment_not_allowed,
                                              responsible_profile=parent, claims_number=claims_number,
                                              record_state_id=RecordState.PENDING_VALIDATE,
                                              process_pk=None)
        element_detail = self.create_element_detail(element=record_card.element_detail.element)
        features = self.create_features(3)
        for feature in features:
            ElementDetailFeature.objects.create(element_detail=element_detail, feature=feature, is_mandatory=True)
        DerivationDirect.objects.create(element_detail=element_detail, record_state_id=RecordState.PENDING_VALIDATE,
                                        group=soon2)
        element_detail.register_theme_ambit()

        rq_data = {
            "id": record_card.pk,
            "element_detail_id": element_detail.pk,
            "features": [{"feature": f.pk, "value": str(random.randint(0, 99))} for f in features if not f.is_special],
            "special_features": [{"feature": f.pk, "value": str(random.randint(0, 99))}
                                 for f in features if f.is_special],
        }
        if isinstance(perform_derivation, bool):
            rq_data["perform_derivation"] = perform_derivation
        self.remove_permission_checker()
        with patch("record_cards.tasks.register_possible_similar_records.delay") as mock_delay:
            response = self.post(force_params=rq_data)
            assert response.status_code == expected_response
            assert mock_delay.called

    @pytest.mark.parametrize("has_permission,different_area,expected_response", (
        (True, True, HTTP_204_NO_CONTENT),
        (True, False, HTTP_204_NO_CONTENT),
        (False, True, HTTP_400_BAD_REQUEST),
        (False, False, HTTP_204_NO_CONTENT),
    ))
    def test_area_change_permission(self, has_permission, different_area, expected_response):
        _, parent, _, soon2, noambit_parent, _ = create_groups()
        self.set_group_permissions("22222", parent, [THEME_CHANGE])

        record_card = self.create_record_card(previous_created_at=True, create_worflow=True,
                                              reassignment_not_allowed=False, responsible_profile=parent,
                                              record_state_id=RecordState.PENDING_VALIDATE,
                                              process_pk=Process.EVALUATION_RESOLUTION_RESPONSE)
        if has_permission:
            self.set_group_permissions("user_id", parent, [RECARD_THEME_CHANGE_AREA])

        if different_area:
            area = mommy.make(Area, user_id="22222")
            element = mommy.make(Element, user_id="2222", area=area)
        else:
            element = record_card.element_detail.element
        element_detail = self.create_element_detail(element=element)
        DerivationDirect.objects.create(element_detail=element_detail, record_state_id=RecordState.PENDING_VALIDATE,
                                        group=soon2)
        element_detail.register_theme_ambit()

        rq_data = {
            "id": record_card.pk,
            "element_detail_id": element_detail.pk,
            "features": [],
            "special_features": [],
            "perform_derivation": True
        }

        self.remove_permission_checker()
        response = self.post(force_params=rq_data)
        assert response.status_code == expected_response

    @pytest.mark.parametrize("record_state_id,perform_derivation", (
        (RecordState.PENDING_VALIDATE, True),
        (RecordState.PENDING_VALIDATE, False),
        (RecordState.EXTERNAL_RETURNED, True),
        (RecordState.EXTERNAL_RETURNED, False),
    ))
    def test_change_theme_autovalidate(self, record_state_id, perform_derivation):
        _, parent, _, soon2, noambit_parent, _ = create_groups()
        self.set_group_permissions("user_id", parent, [THEME_CHANGE, RECARD_THEME_CHANGE_AREA])

        element_detail = self.create_element_detail(process_id=Process.CLOSED_DIRECTLY)

        record_card = self.create_record_card(previous_created_at=False, create_worflow=False,
                                              reassignment_not_allowed=False, responsible_profile=parent,
                                              record_state_id=record_state_id, element_detail=element_detail)

        new_element_detail = self.create_element_detail(process_id=Process.EVALUATION_RESOLUTION_RESPONSE,
                                                        autovalidate_records=True)
        DerivationDirect.objects.create(element_detail=new_element_detail, record_state_id=RecordState.IN_PLANING,
                                        group=noambit_parent)
        new_element_detail.register_theme_ambit()

        rq_data = {
            "id": record_card.pk,
            "element_detail_id": new_element_detail.pk,
            "features": [],
            "special_features": [],
            "perform_derivation": perform_derivation
        }
        self.remove_permission_checker()
        response = self.post(force_params=rq_data)
        assert response.status_code == HTTP_204_NO_CONTENT

    def test_change_theme_workflow(self):
        _, parent, _, soon2, noambit_parent, _ = create_groups()
        self.set_usergroup(parent)
        self.set_group_permissions("22222", parent, [THEME_CHANGE])

        initial_features = self.create_features(3)
        record_card = self.create_record_card(features=initial_features, create_worflow=True,
                                              responsible_profile=parent,
                                              record_state_id=RecordState.IN_RESOLUTION,
                                              process_pk=Process.EVALUATION_RESOLUTION_RESPONSE)

        for _ in range(3):
            record_copy = deepcopy(record_card)
            record_copy.pk = None
            record_copy.normalized_record_id = None
            record_copy.save()

        element_detail = self.create_element_detail(element=record_card.element_detail.element)
        features = self.create_features(3)
        for feature in features:
            ElementDetailFeature.objects.create(element_detail=element_detail, feature=feature, is_mandatory=True)
        DerivationDirect.objects.create(element_detail=element_detail, record_state_id=RecordState.PENDING_VALIDATE,
                                        group=soon2)
        element_detail.register_theme_ambit()

        rq_data = {
            "id": record_card.pk,
            "element_detail_id": element_detail.pk,
            "features": [{"feature": f.pk, "value": str(random.randint(0, 99))} for f in features if not f.is_special],
            "special_features": [{"feature": f.pk, "value": str(random.randint(0, 99))}
                                 for f in features if f.is_special],
            "perform_derivation": True
        }

        self.remove_permission_checker()
        response = self.post(force_params=rq_data)
        assert response.status_code == HTTP_204_NO_CONTENT

        record_card = RecordCard.objects.get(pk=record_card.pk)

        reason_theme_change_id = int(Parameter.get_parameter_by_key("CANVI_DETALL_MOTIU", 19))
        for rec in record_card.workflow.recordcard_set.exclude(pk=record_card.pk):
            assert rec.element_detail_id == element_detail.pk
            assert Comment.objects.filter(record_card=rec, reason_id=reason_theme_change_id).exists()


class TestRecordCardThemeChangeCheckView(RecordCardActionsMixin, CreateRecordCardMixin, FeaturesMixin,
                                         RemovePermissionCheckerMixin, BaseOpenAPITest):
    path = "/record_cards/record_cards/{id}/theme-change/check/"

    @pytest.mark.parametrize("change_theme_permission,expected_response", (
        (True, HTTP_200_OK),
        (False, HTTP_403_FORBIDDEN),
    ))
    def test_theme_change_permissions_check(self, change_theme_permission, expected_response):
        _, parent, _, soon2, noambit_parent, _ = create_groups()
        self.set_usergroup(parent)
        if change_theme_permission:
            self.set_group_permissions("22222", parent, [THEME_CHANGE])
        initial_features = self.create_features(3)
        record_card = self.create_record_card(features=initial_features, create_worflow=True,
                                              reassignment_not_allowed=False,
                                              responsible_profile=parent, claims_number=2,
                                              record_state_id=RecordState.PENDING_VALIDATE)
        element_detail = self.create_element_detail(element=record_card.element_detail.element)
        features = self.create_features(3)
        for feature in features:
            ElementDetailFeature.objects.create(element_detail=element_detail, feature=feature, is_mandatory=True)
        DerivationDirect.objects.create(element_detail=element_detail, record_state_id=RecordState.PENDING_VALIDATE,
                                        group=soon2)
        element_detail.register_theme_ambit()

        rq_data = {
            "id": record_card.pk,
            "element_detail_id": element_detail.pk,
            "features": [{"feature": f.pk, "value": str(random.randint(0, 99))} for f in features if not f.is_special],
            "special_features": [{"feature": f.pk, "value": str(random.randint(0, 99))}
                                 for f in features if f.is_special],
            "perform_derivation": True
        }
        self.remove_permission_checker()
        response = self.post(force_params=rq_data)
        assert response.status_code == expected_response
        if expected_response == HTTP_200_OK:
            assert response.json()["__action__"]["can_confirm"] is True

    def test_theme_no_change_check(self):
        _, parent, _, soon2, noambit_parent, _ = create_groups()
        self.set_usergroup(parent)
        self.set_group_permissions("22222", parent, [THEME_CHANGE])
        features = self.create_features(3)
        record_card = self.create_record_card(features=features, create_worflow=True,
                                              reassignment_not_allowed=False,
                                              responsible_profile=parent, claims_number=2,
                                              record_state_id=RecordState.PENDING_VALIDATE)
        DerivationDirect.objects.create(element_detail=record_card.element_detail,
                                        record_state_id=RecordState.PENDING_VALIDATE, group=soon2)
        rq_data = {
            "id": record_card.pk,
            "element_detail_id": record_card.element_detail_id,
            "features": [{"feature": f.pk, "value": str(random.randint(0, 99))} for f in features if not f.is_special],
            "special_features": [{"feature": f.pk, "value": str(random.randint(0, 99))}
                                 for f in features if f.is_special],
            "perform_derivation": True
        }
        self.remove_permission_checker()
        response = self.post(force_params=rq_data)
        assert response.status_code == HTTP_200_OK
        response_data = response.json()
        assert response_data["__action__"]["can_confirm"] is False
        assert response_data["__action__"]["reason"]
        assert response_data["__action__"]["next_state"] == record_card.record_state_id

    @pytest.mark.parametrize("change_features,original_features,theme_features,can_confirm", (
        (True, 3, 3, True),
        (True, 0, 3, True),
        (True, 3, 0, True),
        (True, 0, 0, True),
        (False, 3, 3, False),
    ))
    def test_theme_change_features_check(self, change_features, original_features, theme_features, can_confirm):
        _, parent, _, soon2, noambit_parent, _ = create_groups()
        self.set_usergroup(parent)
        self.set_group_permissions("22222", parent, [THEME_CHANGE])
        initial_features = self.create_features(original_features)
        record_card = self.create_record_card(features=initial_features, create_worflow=True,
                                              reassignment_not_allowed=False,
                                              responsible_profile=parent, claims_number=2,
                                              record_state_id=RecordState.PENDING_VALIDATE)
        element_detail = self.create_element_detail(element=record_card.element_detail.element)
        new_features = self.create_features(theme_features)
        for feature in new_features:
            ElementDetailFeature.objects.create(element_detail=element_detail, feature=feature, is_mandatory=True)
        DerivationDirect.objects.create(element_detail=element_detail, record_state_id=RecordState.PENDING_VALIDATE,
                                        group=soon2)
        element_detail.register_theme_ambit()

        if change_features:
            features = new_features
        else:
            features = initial_features

        rq_data = {
            "id": record_card.pk,
            "element_detail_id": element_detail.pk,
            "features": [{"feature": f.pk, "value": str(random.randint(0, 99))} for f in features if not f.is_special],
            "special_features": [{"feature": f.pk, "value": str(random.randint(0, 99))}
                                 for f in features if f.is_special],
            "perform_derivation": True
        }

        self.remove_permission_checker()
        response = self.post(force_params=rq_data)
        assert response.status_code == HTTP_200_OK
        response_data = response.json()
        assert response_data["__action__"]["can_confirm"] is can_confirm
        assert response_data["__action__"]["next_state"] == record_card.record_state_id

    @pytest.mark.parametrize(
        "reassignment_not_allowed,create_ambit_derivation,claims_number,create_noambit_derivation,can_confirm", (
            (False, True, 0, False, True),
            (True, True, 0, False, True),
            (True, False, 0, False, True),
            (True, False, 0, True, True),
            (False, True, 10, False, True),
        ))
    def test_record_card_theme_change_check(self, reassignment_not_allowed, create_ambit_derivation, claims_number,
                                            create_noambit_derivation, can_confirm):
        _, parent, _, soon2, noambit_parent, _ = create_groups()
        self.set_usergroup(parent)
        self.set_group_permissions("22222", parent, [THEME_CHANGE])
        initial_features = self.create_features(3)
        record_card = self.create_record_card(features=initial_features, create_worflow=True,
                                              reassignment_not_allowed=reassignment_not_allowed,
                                              responsible_profile=parent, claims_number=claims_number,
                                              record_state_id=RecordState.PENDING_VALIDATE,
                                              process_pk=Process.EVALUATION_RESOLUTION_RESPONSE)
        element_detail = self.create_element_detail(allow_multiderivation_on_reassignment=True,
                                                    element=record_card.element_detail.element)
        features = self.create_features(3)
        for feature in features:
            ElementDetailFeature.objects.create(element_detail=element_detail, feature=feature, is_mandatory=True)
        if create_ambit_derivation:
            DerivationDirect.objects.create(element_detail=element_detail,
                                            record_state_id=RecordState.PENDING_VALIDATE, group=soon2)
        elif create_noambit_derivation:
            DerivationDirect.objects.create(element_detail=element_detail,
                                            record_state_id=RecordState.PENDING_VALIDATE, group=noambit_parent)
        element_detail.register_theme_ambit()

        rq_data = {
            "id": record_card.pk,
            "element_detail_id": element_detail.pk,
            "features": [{"feature": f.pk, "value": str(random.randint(0, 99))} for f in features if not f.is_special],
            "special_features": [{"feature": f.pk, "value": str(random.randint(0, 99))}
                                 for f in features if f.is_special],
        }

        self.remove_permission_checker()
        response = self.post(force_params=rq_data)
        assert response.status_code == HTTP_200_OK
        response_data = response.json()
        assert response_data["__action__"]["can_confirm"] is can_confirm
        if can_confirm:
            assert response_data["__action__"]["reason"] is None
        else:
            assert response_data["__action__"]["reason"]

        if create_ambit_derivation:
            assert response_data["__action__"]["next_group"]["id"] == soon2.pk
            assert response_data["__action__"]["different_ambit"] is False
        elif create_noambit_derivation:
            assert response_data["__action__"]["next_group"]["id"] == noambit_parent.pk
            assert response_data["__action__"]["different_ambit"] is True
        else:
            assert response_data["__action__"]["next_group"]["id"] == parent.pk
            assert response_data["__action__"]["different_ambit"] is False
        assert response_data["__action__"]["next_state"] == record_card.record_state_id

    @pytest.mark.parametrize("record_state_id,can_confirm", (
        (RecordState.PENDING_VALIDATE, True),
        (RecordState.EXTERNAL_RETURNED, False),
        (RecordState.IN_RESOLUTION, False),
        (RecordState.PENDING_ANSWER, False),
    ))
    def test_validated_record_check(self, record_state_id, can_confirm):
        dair, _, _, _, _, _ = create_groups()
        self.set_group_permissions("22222", dair, [THEME_CHANGE])

        initial_features = self.create_features()
        record_card = self.create_record_card(features=initial_features, previous_created_at=True, create_worflow=True,
                                              reassignment_not_allowed=False, responsible_profile=dair,
                                              record_state_id=record_state_id,
                                              process_pk=Process.EVALUATION_RESOLUTION_RESPONSE)
        element_detail = self.create_element_detail(element=record_card.element_detail.element)
        features = self.create_features()

        for feature in features:
            ElementDetailFeature.objects.create(element_detail=element_detail, feature=feature, is_mandatory=True)
        DerivationDirect.objects.create(element_detail=element_detail, record_state_id=record_state_id, group=dair)
        element_detail.register_theme_ambit()

        rq_data = {
            "id": record_card.pk,
            "element_detail_id": element_detail.pk,
            "features": [{"feature": f.pk, "value": str(random.randint(0, 99))} for f in features if not f.is_special],
            "special_features": [{"feature": f.pk, "value": str(random.randint(0, 99))}
                                 for f in features if f.is_special],
            "perform_derivation": True
        }
        self.remove_permission_checker()
        response = self.post(force_params=rq_data)
        assert response.status_code == HTTP_200_OK
        response_data = response.json()
        assert response_data["__action__"]["can_confirm"] is can_confirm
        if can_confirm:
            assert response_data["__action__"]["reason"] is None
        else:
            assert response_data["__action__"]["reason"]

    @pytest.mark.parametrize("has_permission,different_area,can_confirm", (
        (True, True, True),
        (True, False, True),
        (False, True, False),
        (False, False, True),
    ))
    def test_area_change_permission(self, has_permission, different_area, can_confirm):
        _, parent, _, soon2, noambit_parent, _ = create_groups()
        self.set_group_permissions("22222", parent, [THEME_CHANGE])

        record_card = self.create_record_card(previous_created_at=True, create_worflow=True,
                                              reassignment_not_allowed=False, responsible_profile=parent,
                                              record_state_id=RecordState.PENDING_VALIDATE,
                                              process_pk=Process.EVALUATION_RESOLUTION_RESPONSE)
        if has_permission:
            self.set_group_permissions("user_id", parent, [RECARD_THEME_CHANGE_AREA])

        if different_area:
            area = mommy.make(Area, user_id="22222")
            element = mommy.make(Element, user_id="2222", area=area)
        else:
            element = record_card.element_detail.element
        element_detail = self.create_element_detail(element=element)
        DerivationDirect.objects.create(element_detail=element_detail, record_state_id=RecordState.PENDING_VALIDATE,
                                        group=soon2)
        element_detail.register_theme_ambit()

        rq_data = {
            "id": record_card.pk,
            "element_detail_id": element_detail.pk,
            "features": [],
            "special_features": [],
            "perform_derivation": True
        }

        self.remove_permission_checker()
        response = self.post(force_params=rq_data)
        assert response.status_code == HTTP_200_OK
        response_data = response.json()
        assert response_data["__action__"]["can_confirm"] is can_confirm
        if can_confirm:
            assert response_data["__action__"]["reason"] is None
        else:
            assert response_data["__action__"]["reason"]

    @pytest.mark.parametrize("record_state_id", (RecordState.PENDING_VALIDATE, RecordState.EXTERNAL_RETURNED))
    def test_change_theme_autovalidate_check(self, record_state_id):
        _, parent, _, soon2, noambit_parent, _ = create_groups()
        self.set_group_permissions("user_id", parent, [THEME_CHANGE, RECARD_THEME_CHANGE_AREA])

        element_detail = self.create_element_detail(process_id=Process.CLOSED_DIRECTLY)

        record_card = self.create_record_card(previous_created_at=False, create_worflow=False,
                                              reassignment_not_allowed=False, responsible_profile=parent,
                                              record_state_id=record_state_id, element_detail=element_detail)

        new_element_detail = self.create_element_detail(process_id=Process.EVALUATION_RESOLUTION_RESPONSE,
                                                        autovalidate_records=True)
        DerivationDirect.objects.create(element_detail=new_element_detail, record_state_id=RecordState.IN_PLANING,
                                        group=noambit_parent)
        new_element_detail.register_theme_ambit()

        rq_data = {
            "id": record_card.pk,
            "element_detail_id": new_element_detail.pk,
            "features": [],
            "special_features": [],
        }
        self.remove_permission_checker()
        response = self.post(force_params=rq_data)
        assert response.status_code == HTTP_200_OK
        response_data = response.json()
        assert response_data["__action__"]["can_confirm"] is True
        assert response_data["__action__"]["reason"] is None
        assert response_data["__action__"]["next_group"]["id"] == noambit_parent.pk
        assert response_data["__action__"]["next_state"] == RecordState.IN_PLANING


class VisibilityTestMixin(OpenAPIResourceExcelExportMixin, CreateRecordCardMixin, SetUserGroupMixin):
    record_state_id = RecordState.PENDING_VALIDATE
    permission = None

    @pytest.mark.parametrize("case", (1, 2, 3, 4, 5, 6))
    def test_visibility(self, case):
        grand_parent, parent, first_soon, second_soon, noambit_parent, noambit_soon = create_groups(
            create_reasignations=False)

        cases = {
            1: {"group": grand_parent, "expected_records": 10},
            2: {"group": parent, "expected_records": 8},
            3: {"group": first_soon, "expected_records": 2},
            4: {"group": second_soon, "expected_records": 2},
            5: {"group": noambit_parent, "expected_records": 2},
            6: {"group": noambit_soon, "expected_records": 1},

        }

        responsibles = [parent, first_soon, second_soon, noambit_parent, parent, parent, first_soon, noambit_soon,
                        second_soon, parent]
        self.set_usergroup(group=cases[case]["group"])
        [self.create_record_card(responsible_profile=responsible, process_pk=Process.EVALUATION_RESOLUTION_RESPONSE,
                                 record_state_id=self.record_state_id) for responsible in responsibles]

        response = self.list(force_params={"page_size": self.paginate_by})
        self.should_return_list(cases[case]["expected_records"], self.paginate_by, response)

    @pytest.mark.parametrize("has_permissions,expected_response", ((True, HTTP_200_OK), (False, HTTP_403_FORBIDDEN)))
    def test_permissions(self, has_permissions, expected_response):
        object_number = 4
        self.set_usergroup()
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


class TestRecordCardPendingValidationList(VisibilityTestMixin, SetPermissionMixin, BaseOpenAPITest):
    path = "/record_cards/record_cards/pending-validation/"
    base_api_path = "/services/iris/api"

    paginate_by = 10

    record_state_id = RecordState.PENDING_VALIDATE
    permission = RECARD_PENDVALIDATE

    def test_list(self):
        urgency = [True, False, False, True, True, False, False, False, True, False]
        ans_limit_delta = [3, 2, None, 6, 8, 3, 5, 6, 1, None]

        num_objects = len(urgency)
        self.set_usergroup()
        self.set_group_permissions("22222", self.user.usergroup.group, [RECARD_PENDVALIDATE])
        for index in range(num_objects):
            self.create_record_card(urgent=urgency[index], responsible_profile=self.user.usergroup.group,
                                    ans_limit_delta=ans_limit_delta[index], fill_active_mandatory_fields=False)

        response = self.list(force_params={"page_size": self.paginate_by})
        self.should_return_list(num_objects, self.paginate_by, response)

        for index, record_card in enumerate(response.data["results"]):
            if index < 4:
                assert record_card["urgent"] is True
            else:
                assert record_card["urgent"] is False

    def given_an_object(self):
        return self.create_record_card()


class TestMyTasks(VisibilityTestMixin, OpenAPIResourceExcelExportMixin, SetPermissionMixin, BaseOpenAPITest):
    path = "/record_cards/record_cards/my-tasks/"
    base_api_path = "/services/iris/api"

    paginate_by = 10

    record_state_id = RecordState.IN_RESOLUTION
    permission = RECARD_MYTASKS

    def test_list(self):
        states = [RecordState.PENDING_ANSWER, RecordState.CANCELLED, RecordState.PENDING_ANSWER,
                  RecordState.PENDING_VALIDATE, RecordState.IN_RESOLUTION, RecordState.PENDING_VALIDATE,
                  RecordState.CLOSED, RecordState.IN_RESOLUTION, RecordState.IN_PLANING, RecordState.PENDING_VALIDATE]

        self.set_usergroup()
        self.set_group_permissions("22222", self.user.usergroup.group, [RECARD_MYTASKS])
        for index, state in enumerate(states):
            self.create_record_card(state, process_pk=Process.EVALUATION_RESOLUTION_RESPONSE,
                                    responsible_profile=self.user.usergroup.group)

        response = self.list(force_params={"page_size": self.paginate_by})
        self.should_return_list(5, self.paginate_by, response)

    def given_an_object(self):
        return self.create_record_card()


class TestRecordCardCancel(CreateRecordFileMixin, RecordCardActionsMixin, RecordCardRestrictedTestMixin,
                           CreateDerivationsMixin, BaseOpenAPITest):
    path = "/record_cards/record_cards/{id}/cancel/"

    @pytest.mark.parametrize(
        "reason,responsible_profile,cancel_profile,comment,initial_state_pk,previous_created_at,"
        "expected_response,set_pemissions", (
            (Reason.VALIDATION_BY_ERROR, 2, 2, "Comentari de prova", RecordState.PENDING_VALIDATE,
             False, HTTP_400_BAD_REQUEST, True),
            (Reason.VALIDATION_BY_ERROR, 2, 2, "Comentari de prova", RecordState.PENDING_ANSWER,
             False, HTTP_201_CREATED, True),
            (Reason.VALIDATION_BY_ERROR, 2, 1, "Comentari de prova", RecordState.PENDING_ANSWER,
             False, HTTP_201_CREATED, True),
            (Reason.VALIDATION_BY_ERROR, 6, 3, "Comentari de prova", RecordState.PENDING_ANSWER,
             False, HTTP_403_FORBIDDEN, True),

            (Reason.EXPIRATION, 2, 2, "Comentari de prova", RecordState.PENDING_VALIDATE,
             True, HTTP_201_CREATED, True),
            (Reason.EXPIRATION, 2, 2, "Comentari de prova", RecordState.PENDING_VALIDATE,
             False, HTTP_400_BAD_REQUEST, True),
            (Reason.EXPIRATION, 2, 2, "Comentari de prova", RecordState.PENDING_VALIDATE,
             False, HTTP_403_FORBIDDEN, False),
        ))
    def test_cancel_internalclaim(self, tmpdir_factory, reason, responsible_profile, cancel_profile, comment,
                                  initial_state_pk, previous_created_at, expected_response, set_pemissions):
        cancel_groups = {gr.pk: gr for gr in create_groups()}
        if previous_created_at:
            element_detail = self.create_element_detail(validation_place_days=2)
        else:
            element_detail = self.create_element_detail()
        record_card = self.create_record_card(initial_state_pk, Process.EXTERNAL_PROCESSING,
                                              create_record_card_response=True,
                                              responsible_profile=cancel_groups[responsible_profile],
                                              previous_created_at=previous_created_at, element_detail=element_detail)
        self.create_file(tmpdir_factory, record_card, 1)
        if previous_created_at:
            record_card.created_at = timezone.now() - timedelta(days=6)
            record_card.save()

        derivated_profile = record_card.responsible_profile

        params = {"id": record_card.pk, "reason": reason, "comment": comment}

        self.user.usergroup.group = cancel_groups[cancel_profile]
        self.user.usergroup.save()
        if set_pemissions:
            self.set_group_permissions("user_id", self.user.usergroup.group)
        else:
            GroupProfiles.objects.all().delete()

        with patch("record_cards.tasks.copy_record_files.delay") as mock_delay:
            response = self.post(force_params=params)

            assert response.status_code == expected_response
            record_card = RecordCard.objects.get(pk=record_card.pk)
            assert record_card.responsible_profile == derivated_profile
            if expected_response == HTTP_201_CREATED:
                mock_delay.assert_called_once()
                self.assert_cancel_updated_response(record_card, comment)
                assert RecordCard.objects.filter(
                    normalized_record_id__startswith=record_card.normalized_record_id).count() > 1
                assert len(mail.outbox) == 1

    def test_cancel_internalclaim_autovalidate(self):
        cancel_groups = {gr.pk: gr for gr in create_groups()}
        element_detail = self.create_element_detail(autovalidate_records=True, process_id=Process.EXTERNAL_PROCESSING)
        record_card = self.create_record_card(RecordState.PENDING_ANSWER, create_record_card_response=True,
                                              responsible_profile=cancel_groups[2], element_detail=element_detail)

        params = {"id": record_card.pk, "reason": Reason.VALIDATION_BY_ERROR, "comment": "Comentari de prova"}

        self.user.usergroup.group = cancel_groups[1]
        self.user.usergroup.save()
        self.set_group_permissions("user_id", self.user.usergroup.group)

        response = self.post(force_params=params)

        assert response.status_code == HTTP_201_CREATED
        record_card = RecordCard.objects.get(pk=record_card.pk)
        assert RecordCard.objects.filter(
            normalized_record_id__startswith=record_card.normalized_record_id).count() > 1
        new_code = f"{record_card.normalized_record_id}-02"
        assert RecordCard.objects.get(normalized_record_id=new_code).record_state_id == RecordState.EXTERNAL_PROCESSING

    @pytest.mark.parametrize(
        "responsible_profile,cancel_profile,comment,initial_state_pk,expected_response,extra_duplicate_info,"
        "set_pemissions", (
            (2, 2, "Comentari de prova", RecordState.PENDING_ANSWER, HTTP_400_BAD_REQUEST, {}, True),
            (2, 2, "Comentari de prova", RecordState.PENDING_ANSWER, HTTP_204_NO_CONTENT,
             {"duplicate": True, "repeat_record_card": False, "duplicate_state_id": RecordState.PENDING_VALIDATE},
             True),
            (2, 2, "Comentari de prova", RecordState.PENDING_ANSWER, HTTP_403_FORBIDDEN,
             {"duplicate": True, "repeat_record_card": False, "duplicate_state_id": RecordState.PENDING_VALIDATE},
             False)
        ))
    def test_cancel_duplicity_repetition(self, responsible_profile, cancel_profile, comment, initial_state_pk,
                                         expected_response, extra_duplicate_info, set_pemissions):
        cancel_groups = {gr.pk: gr for gr in create_groups()}

        record_card = self.create_record_card(initial_state_pk, process_pk=Process.EXTERNAL_PROCESSING,
                                              create_record_card_response=True,
                                              responsible_profile=cancel_groups[responsible_profile])
        if expected_response == HTTP_204_NO_CONTENT:
            derivated_profile = self.create_direct_derivation(record_card.element_detail_id, RecordState.CANCELLED)
        else:
            derivated_profile = record_card.responsible_profile

        if extra_duplicate_info.get("duplicate"):
            if extra_duplicate_info.get("new_applicant"):
                citizen = mommy.make(Citizen, user_id="2222")
                applicant = mommy.make(Applicant, user_id="2222", citizen=citizen)
                state_id = initial_state_pk
            else:
                applicant = record_card.request.applicant
                state_id = extra_duplicate_info.get("duplicate_state_id")

            duplicated_record_card = self.create_record_card(state_id, Process.EXTERNAL_PROCESSING,
                                                             applicant=applicant)

        duplicity_repetition_reason_id = int(Parameter.get_parameter_by_key("DEMANAR_FITXA", 1))
        params = {"id": record_card.pk, "reason": duplicity_repetition_reason_id, "comment": comment}
        if not extra_duplicate_info.get("duplicate"):
            params.update({"duplicated_record_card": set_reference(RecordCard, "normalized_record_id")})
        elif not extra_duplicate_info.get("repeat_record_card"):
            params.update({"duplicated_record_card": duplicated_record_card.normalized_record_id})
        elif extra_duplicate_info.get("repeat_record_card"):
            params.update({"duplicated_record_card": record_card.normalized_record_id})

        self.user.usergroup.group = cancel_groups[cancel_profile]
        self.user.usergroup.save()
        if set_pemissions:
            self.set_group_permissions("user_id", self.user.usergroup.group)
        else:
            GroupProfiles.objects.all().delete()

        response = self.post(force_params=params)

        assert response.status_code == expected_response
        record_card = RecordCard.objects.get(pk=record_card.pk)
        assert record_card.responsible_profile == derivated_profile
        if expected_response == HTTP_204_NO_CONTENT:
            self.assert_cancel_updated_response(record_card, comment)

    @pytest.mark.parametrize("reason,comment,expected_response,set_pemissions", (
        (Reason.FALSE_ERRONEOUS_DATA, "Comentari de prova", HTTP_204_NO_CONTENT, True),
        ("", "Comentari de prova", HTTP_400_BAD_REQUEST, True),
        (None, "Comentari de prova", HTTP_400_BAD_REQUEST, True),
        (Reason.FALSE_ERRONEOUS_DATA, "Com de prova", HTTP_400_BAD_REQUEST, True),
        (Reason.FALSE_ERRONEOUS_DATA, "Comentari de prova", HTTP_403_FORBIDDEN, False),
    ))
    def test_cancel_other_reasons(self, reason, comment, expected_response, set_pemissions):
        record_card = self.create_record_card(RecordState.PENDING_ANSWER, Process.EXTERNAL_PROCESSING,
                                              create_record_card_response=True)
        if expected_response == HTTP_204_NO_CONTENT:
            derivated_profile = self.create_direct_derivation(record_card.element_detail_id, RecordState.CANCELLED)
        else:
            derivated_profile = record_card.responsible_profile

        params = {"id": record_card.pk, "reason": reason, "comment": comment}

        if set_pemissions:
            self.set_group_permissions("user_id", self.user.usergroup.group)
        else:
            GroupProfiles.objects.all().delete()

        response = self.post(force_params=params)

        assert response.status_code == expected_response
        record_card = RecordCard.objects.get(pk=record_card.pk)
        assert record_card.responsible_profile == derivated_profile
        if expected_response == HTTP_204_NO_CONTENT:
            self.assert_cancel_updated_response(record_card, comment)

    @staticmethod
    def assert_cancel_updated_response(record_card, comment):
        assert comment in Comment.objects.get(record_card=record_card).comment
        assert RecordCard.objects.get(pk=record_card.pk).record_state_id == RecordState.CANCELLED
        assert RecordCardStateHistory.objects.get(record_card=record_card,
                                                  next_state_id=RecordState.CANCELLED, automatic=False)
        assert record_card.closing_date
        assert record_card.recordcardaudit.close_user

    def test_state_changed_signal(self):
        signal = Mock(spec=Signal)
        with patch("record_cards.models.record_card_state_changed", signal):
            record_card = self.create_record_card(record_state_id=RecordState.PENDING_ANSWER,
                                                  process_pk=Process.EXTERNAL_PROCESSING)
            params = {"id": record_card.pk, "reason": Reason.FALSE_ERRONEOUS_DATA, "comment": "Comentari de prova"}
            response = self.post(force_params=params)
            assert response.status_code == HTTP_204_NO_CONTENT
            signal.send_robust.assert_called_with(record_card=record_card, sender=RecordCard)

    def get_post_params(self, record_card):
        return {"id": record_card.pk, "reason": Reason.FALSE_ERRONEOUS_DATA, "comment": "Comentari de prova"}

    def test_cancel_creation_department(self):
        record_card = self.create_record_card(record_state_id=RecordState.PENDING_ANSWER,
                                              process_pk=Process.EXTERNAL_PROCESSING)
        user = self.when_is_authenticated()

        params = {"id": record_card.pk, "reason": Reason.FALSE_ERRONEOUS_DATA, "comment": "Comentari de prova"}
        response = self.post(force_params=params)

        assert response.status_code == HTTP_204_NO_CONTENT
        record_card = RecordCard.objects.get(pk=record_card.pk)
        assert record_card.close_department == user.imi_data['dptcuser']
        assert record_card.closing_date


class TestRecordCardClose(RecordCardActionsMixin, RecordCardRestrictedTestMixin, CreateDerivationsMixin,
                          BaseOpenAPITest):
    path = "/record_cards/record_cards/{id}/close/"

    @pytest.mark.parametrize("initial_record_state_id,expected_response,create_derivation,close_department", (
        (RecordState.PENDING_VALIDATE, HTTP_204_NO_CONTENT, True, ""),
        (RecordState.CLOSED, HTTP_404_NOT_FOUND, False, ""),
        (RecordState.EXTERNAL_RETURNED, HTTP_204_NO_CONTENT, False, "close_department"),
    ))
    def test_close_record_card(self, initial_record_state_id, expected_response, create_derivation, close_department):

        citizen = mommy.make(Citizen, user_id="2222")
        applicant = mommy.make(Applicant, citizen=citizen, user_id="2222", pend_anonymize=True)
        record_card = self.create_record_card(initial_record_state_id, applicant=applicant)
        object_id = record_card.pk
        if create_derivation:
            derivated_profile = self.create_direct_derivation(record_card.element_detail_id, RecordState.CLOSED)
        else:
            derivated_profile = record_card.responsible_profile

        with patch("record_cards.tasks.anonymize_applicant.delay") as mock_delay:
            response = self.post(force_params={"id": object_id})

            assert response.status_code == expected_response
            record_card = RecordCard.objects.get(pk=object_id)
            assert record_card.record_state_id == RecordState.CLOSED
            assert record_card.responsible_profile == derivated_profile
            if expected_response == HTTP_204_NO_CONTENT:
                mock_delay.assert_called()
                assert record_card.closing_date
                assert record_card.recordcardaudit.close_user
                assert record_card.close_department == self.user.imi_data['dptcuser']
                assert RecordCardStateHistory.objects.get(record_card_id=object_id, next_state_id=RecordState.CLOSED,
                                                          automatic=False)


class TestRecordCardExternalProcessing(RecordCardActionsMixin, CreateDerivationsMixin, RecordCardRestrictedTestMixin,
                                       BaseOpenAPITest):
    path = "/record_cards/record_cards/{id}/external-processing/"

    @pytest.mark.parametrize("initial_record_state_id,expected_response,create_derivation", (
        (RecordState.PENDING_VALIDATE, HTTP_204_NO_CONTENT, True),
        (RecordState.IN_PLANING, HTTP_204_NO_CONTENT, True),
        (RecordState.IN_RESOLUTION, HTTP_204_NO_CONTENT, False),
        (RecordState.PENDING_ANSWER, HTTP_204_NO_CONTENT, True),
        (RecordState.CLOSED, HTTP_204_NO_CONTENT, False),
        (RecordState.CANCELLED, HTTP_204_NO_CONTENT, True),
        (RecordState.NO_PROCESSED, HTTP_204_NO_CONTENT, True),
        (RecordState.EXTERNAL_RETURNED, HTTP_204_NO_CONTENT, True),
        (RecordState.EXTERNAL_PROCESSING, HTTP_404_NOT_FOUND, False),

    ))
    def test_external_processing_record_card(self, initial_record_state_id, expected_response, create_derivation):
        if initial_record_state_id is not None:
            record_card = self.create_record_card(initial_record_state_id, process_pk=Process.EXTERNAL_PROCESSING)
            object_id = record_card.pk
            if create_derivation:
                derivated_profile = self.create_direct_derivation(record_card.element_detail_id,
                                                                  RecordState.EXTERNAL_PROCESSING)
            else:
                derivated_profile = record_card.responsible_profile
        else:
            object_id = 1968
        response = self.post(force_params={"id": object_id})
        assert response.status_code == expected_response
        if initial_record_state_id:
            record_card = RecordCard.objects.get(pk=object_id)
            assert record_card.record_state_id == RecordState.EXTERNAL_PROCESSING
            assert record_card.responsible_profile == derivated_profile
        if expected_response == HTTP_204_NO_CONTENT:
            assert RecordCardStateHistory.objects.get(record_card_id=object_id,
                                                      next_state_id=RecordState.EXTERNAL_PROCESSING, automatic=False)


class TestRecordCardExternalProcessingEmail(TestRecordCardExternalProcessing):
    path = "/record_cards/record_cards/{id}/external-processing-email/"


class TestRecordCardDraftAnswer(RecordCardActionsMixin, RecordCardRestrictedTestMixin, CreateDerivationsMixin,
                                BaseOpenAPITest):
    path = "/record_cards/record_cards/{id}/draft-answer/"
    action_permission = RECARD_SAVE_ANSWER

    @pytest.mark.parametrize("initial_record_state_id,expected_response,response,send_date", (
        (RecordState.IN_PLANING, HTTP_404_NOT_FOUND, "", ""),
        (RecordState.PENDING_ANSWER, HTTP_204_NO_CONTENT, "Respuesta test", "2019-09-05"),
        (RecordState.PENDING_ANSWER, HTTP_400_BAD_REQUEST, "Respuesta test", ""),
        (RecordState.PENDING_ANSWER, HTTP_400_BAD_REQUEST, "", "2019-09-05"),
    ))
    def test_draft_answer_record_card(self, initial_record_state_id, expected_response, response, send_date):
        self.set_usergroup()
        self.set_group_permissions("22222", self.user.usergroup.group, [RECARD_SAVE_ANSWER])
        if initial_record_state_id is not None:
            record_card = self.create_record_card(initial_record_state_id,
                                                  responsible_profile=self.user.usergroup.group)
            object_id = record_card.pk
        else:
            object_id = 1968
            record_card = None
        http_response = self.post(force_params={"id": object_id, "response": response, "send_date": send_date})
        assert http_response.status_code == expected_response
        if initial_record_state_id:
            assert RecordCard.objects.get(pk=object_id).record_state_id == initial_record_state_id
        if expected_response == HTTP_204_NO_CONTENT:
            assert RecordCardTextResponse.objects.get(record_card=record_card).response == response

    def get_record_state_id(self):
        return RecordState.PENDING_ANSWER

    def get_post_params(self, record_card):
        return {"id": record_card.pk, "response": "Respuesta test", "send_date": "2019-09-05"}

    def test_many_draft_answers(self):
        record_card = self.create_record_card(record_state_id=RecordState.PENDING_ANSWER)
        self.set_group_permissions("22222", record_card.responsible_profile, [RECARD_SAVE_ANSWER])
        draft_response = ""
        for draft in range(3):
            draft_response = str(uuid.uuid4())
            http_response = self.post(force_params={"id": record_card.pk, "response": draft_response,
                                                    "send_date": "2020-10-20"})
            assert http_response.status_code == HTTP_204_NO_CONTENT
        assert RecordCardTextResponse.objects.get(record_card=record_card).response == draft_response

    @pytest.mark.parametrize("has_permissions,expected_response", (
        (True, HTTP_204_NO_CONTENT),
        (False, HTTP_403_FORBIDDEN),
    ))
    def test_permissions(self, has_permissions, expected_response):
        record_card = self.create_record_card(RecordState.PENDING_ANSWER)
        if has_permissions:
            self.set_group_permissions("22222", record_card.responsible_profile, [RECARD_SAVE_ANSWER])
        response = self.post(force_params={"id": record_card.pk, "response": "draft response",
                                           "send_date": "2020-10-20"})
        assert response.status_code == expected_response


class TestRecordCardAnswer(RecordCardActionsMixin, RecordCardRestrictedTestMixin, CreateDerivationsMixin,
                           SetPermissionMixin, BaseOpenAPITest):
    path = "/record_cards/record_cards/{id}/answer/"
    action_permission = RECARD_ANSWER

    @pytest.mark.parametrize("initial_record_state_id,expected_response,response,send_date,create_derivation", (
        (RecordState.PENDING_ANSWER, HTTP_204_NO_CONTENT, "Respuesta test", "2019-09-05", False),
        (RecordState.PENDING_ANSWER, HTTP_204_NO_CONTENT, "Respuesta test", "2019-09-05", True),
        (RecordState.PENDING_ANSWER, HTTP_400_BAD_REQUEST, "Respuesta test", "", False),
        (RecordState.PENDING_ANSWER, HTTP_400_BAD_REQUEST, "", "2019-09-05", False),
        (RecordState.EXTERNAL_RETURNED, HTTP_404_NOT_FOUND, "", "", False),
    ))
    def test_answer_record_card(self, initial_record_state_id, expected_response, response, send_date,
                                create_derivation):
        self.set_usergroup()
        self.set_group_permissions("22222", self.user.usergroup.group, [RECARD_ANSWER])
        if initial_record_state_id is not None:
            record_card = self.create_record_card(initial_record_state_id,
                                                  responsible_profile=self.user.usergroup.group)
            object_id = record_card.pk
            if create_derivation:
                derivated_profile = self.create_direct_derivation(record_card.element_detail_id, RecordState.CLOSED)
            else:
                derivated_profile = record_card.responsible_profile
        else:
            object_id = 1968
        response = self.post(force_params={"id": object_id, "response": response, "send_date": send_date,
                                           "worked": ""})
        assert response.status_code == expected_response
        if expected_response == HTTP_204_NO_CONTENT:
            record_card = RecordCard.objects.get(pk=object_id)
            assert record_card.record_state_id == RecordState.CLOSED
            assert record_card.responsible_profile == derivated_profile
        elif initial_record_state_id:
            assert RecordCard.objects.get(pk=object_id).record_state_id == initial_record_state_id

    def test_state_changed_signal(self):
        signal = Mock(spec=Signal)
        with patch("record_cards.models.record_card_state_changed", signal):
            record_card = self.create_record_card(record_state_id=RecordState.PENDING_ANSWER,
                                                  process_pk=Process.EXTERNAL_PROCESSING)
            self.set_group_permissions("22222", record_card.responsible_profile, [RECARD_ANSWER])
            params = {"id": record_card.pk, "response": "Respuesta test", "send_date": "2019-09-05"}
            response = self.post(force_params=params)
            assert response.status_code == HTTP_204_NO_CONTENT
            signal.send_robust.assert_called_with(record_card=record_card, sender=RecordCard)

    @pytest.mark.parametrize("has_permissions,expected_response", (
        (True, HTTP_204_NO_CONTENT),
        (False, HTTP_403_FORBIDDEN),
    ))
    def test_permissions(self, has_permissions, expected_response):
        record_card = self.create_record_card(record_state_id=RecordState.PENDING_ANSWER,
                                              process_pk=Process.EXTERNAL_PROCESSING)
        if has_permissions:
            self.set_group_permissions("22222", record_card.responsible_profile, [RECARD_ANSWER])
        params = {"id": record_card.pk, "response": "Respuesta test", "send_date": "2019-09-05"}
        response = self.post(force_params=params)
        assert response.status_code == expected_response

    def get_record_state_id(self):
        return RecordState.PENDING_ANSWER

    def get_post_params(self, record_card):
        return {"id": record_card.pk, "response": "Respuesta test", "send_date": "2019-09-05"}

    @pytest.mark.parametrize("only_ambit,group_is_ambit,expected_response", (
        (True, True, HTTP_204_NO_CONTENT),
        (True, False, HTTP_409_CONFLICT),
        (False, True, HTTP_204_NO_CONTENT),
        (False, False, HTTP_204_NO_CONTENT),
    ))
    def test_group_can_answer(self, only_ambit, group_is_ambit, expected_response):
        _, parent, _, _, _, _ = create_groups()
        record_card = self.create_record_card(process_pk=Process.PLANING_RESOLUTION_RESPONSE,
                                              record_state_id=RecordState.PENDING_ANSWER, responsible_profile=parent)
        self.set_group_permissions("22222", record_card.responsible_profile, [RECARD_ANSWER])
        if only_ambit:
            record_card.claims_number = 10
            record_card.save()

        record_card.responsible_profile.is_ambit = group_is_ambit
        record_card.responsible_profile.save()
        response = self.post(force_params={"id": record_card.pk, "response": "Respuesta test",
                                           "send_date": "2019-09-05"})
        assert response.status_code == expected_response

    def test_answer_with_draft(self):
        record_card = self.create_record_card(record_state_id=RecordState.PENDING_ANSWER)
        self.set_group_permissions("22222", record_card.responsible_profile, [RECARD_ANSWER])
        derivated_profile = self.create_direct_derivation(record_card.element_detail_id, RecordState.CLOSED)
        mommy.make(RecordCardTextResponse, record_card=record_card, user_id="22222")
        text_response = str(uuid.uuid4())
        response = self.post(force_params={"id": record_card.pk, "response": text_response, "send_date": "2020-10-20"})
        assert response.status_code == HTTP_204_NO_CONTENT
        record_card = RecordCard.objects.get(pk=record_card.pk)
        assert record_card.record_state_id == RecordState.CLOSED
        assert record_card.responsible_profile == derivated_profile
        assert RecordCardTextResponse.objects.get(record_card=record_card).response == text_response

    @pytest.mark.parametrize("response_worked_permission,response_worked,expected_response", (
        (True, "t", HTTP_204_NO_CONTENT),
        (True, "", HTTP_204_NO_CONTENT),
        (False, "4", HTTP_400_BAD_REQUEST),
        (False, "", HTTP_204_NO_CONTENT),
    ))
    def test_record_response_worked(self, response_worked_permission, response_worked, expected_response):
        self.set_usergroup()
        group = self.user.usergroup.group
        if response_worked_permission:
            self.set_permission(RESP_WORKED, group=group)

        record_card = self.create_record_card(record_state_id=RecordState.PENDING_ANSWER, responsible_profile=group,
                                              create_record_card_response=True)
        self.set_group_permissions("22222", record_card.responsible_profile, [RECARD_ANSWER])
        self.when_is_authenticated()

        response = self.post(force_params={"id": record_card.pk, "response": "text_response",
                                           "send_date": "2020-10-20", "worked": response_worked})
        assert response.status_code == expected_response
        if expected_response == HTTP_201_CREATED:
            text_response = RecordCardTextResponse.objects.get(record_card_id=record_card.pk)
            assert text_response.worked == response_worked


class TestRecordCardAnswerResponse(RecordCardActionsMixin, OpenAPIRetrieveMixin, BaseOpenAPITest):
    path = "/record_cards/record_cards/{id}/answer/response/"
    detail_path = "/record_cards/record_cards/{id}/answer/response/"

    def test_retrieve(self):
        record_card = self.create_record_card(RecordState.PENDING_ANSWER)
        RecordCardTextResponse.objects.create(record_card=record_card, response="Respuesta test",
                                              send_date=datetime(2019, 9, 5).date())
        response = self.retrieve(force_params={"id": record_card.pk})
        assert response.status_code == HTTP_200_OK
        self.should_retrieve_object(response, record_card)


class TestCommentCreate(OpenAPIResourceCreateMixin, CreateRecordCardMixin, SetUserGroupMixin,
                        SetPermissionMixin, BaseOpenAPITest):
    path = "/record_cards/record_cards/add-comment/"
    base_api_path = "/services/iris/api"

    def get_default_data(self):
        return {
            "reason": None,
            "record_card": self.create_record_card().pk,
            "comment": "test comment"
        }

    def given_create_rq_data(self):
        return {
            "reason": None,
            "record_card": self.create_record_card().pk,
            "comment": "test comment"
        }

    def when_data_is_invalid(self, data):
        data["record_card"] = None

    @pytest.mark.parametrize("mayorship_permission,mayorship,expected_response", (
        (True, True, HTTP_201_CREATED),
        (True, False, HTTP_201_CREATED),
        (False, True, HTTP_201_CREATED),
        (False, False, HTTP_201_CREATED),
    ))
    def test_mayorship_action(self, mayorship_permission, mayorship, expected_response):
        record_kwargs = {
            "record_state_id": RecordState.IN_RESOLUTION,
            "process_pk": Process.EXTERNAL_PROCESSING,
            "mayorship": mayorship
        }
        if mayorship_permission:
            record_kwargs["responsible_profile"] = self.set_permission(MAYORSHIP)

        record_card = self.create_record_card(**record_kwargs)
        response = self.create(force_params={"reason": None, "record_card": record_card.pk, "comment": "test comment"})
        assert response.status_code == expected_response

    @pytest.mark.parametrize("responsible_group,action_group,expected_response", (
        (2, 1, HTTP_201_CREATED),
        (2, 2, HTTP_201_CREATED),
        (2, 3, HTTP_201_CREATED),
    ))
    def test_can_tramit_action(self, responsible_group, action_group, expected_response):
        groups = dict_groups()
        record_kwargs = {
            "record_state_id": RecordState.IN_RESOLUTION,
            "process_pk": Process.EXTERNAL_PROCESSING,
            "responsible_profile": groups[responsible_group]
        }
        self.set_usergroup(groups[action_group])
        record_card = self.create_record_card(**record_kwargs)
        response = self.create(force_params={"reason": None, "record_card": record_card.pk, "comment": "test comment"})
        assert response.status_code == expected_response

    @pytest.mark.parametrize("reason_id,citizen_alarm", (
        (Reason.CLAIM_CITIZEN_REQUEST, True),
        (None, False),
        (Reason.BREAKE_DOWN_MULTI, False),
    ))
    def test_claim_comment(self, reason_id, citizen_alarm):
        application = Application.objects.get(pk=Application.IRIS_PK)
        record_card = self.create_record_card(application=application)
        self.set_group_permissions("22222", record_card.responsible_profile, [RECARD_CLAIM])
        response = self.create(force_params={"reason": reason_id, "record_card": record_card.pk,
                                             "comment": "test comment"})
        assert response.status_code == HTTP_201_CREATED
        record_card = RecordCard.objects.get(pk=record_card.pk)
        assert record_card.citizen_alarm is citizen_alarm
        assert RecordCardAlarms(record_card, record_card.responsible_profile).citizen_claim_alarm is citizen_alarm
        assert RecordCardAlarms(record_card, record_card.responsible_profile).citizen_claim_web_alarm is False

    @pytest.mark.parametrize("reason_id,cancel_request", (
        (Reason.RECORDCARD_CANCEL_REQUEST, True),
        (None, False),
    ))
    def test_cancel_request_comment(self, reason_id, cancel_request):
        record_card = self.create_record_card(cancel_request=cancel_request)
        response = self.create(force_params={"reason": reason_id, "record_card": record_card.pk,
                                             "comment": "test comment"})
        assert response.status_code == HTTP_201_CREATED
        record_card = RecordCard.objects.get(pk=record_card.pk)
        assert record_card.cancel_request is cancel_request
        assert RecordCardAlarms(record_card, record_card.responsible_profile).cancel_request_alarm is cancel_request

    def test_create_comment_cancel_state(self):
        record_card = self.create_record_card(record_state_id=RecordState.CANCELLED)
        response = self.create(force_params={"reason": Reason.NOT_APPLICABLE, "record_card": record_card.pk,
                                             "comment": "test comment"})
        assert response.status_code == HTTP_409_CONFLICT


class TestRecordCardMultiRecordsView(RecordCardActionsMixin, CreateRecordCardMixin, OpenAPIResourceListMixin,
                                     BaseOpenAPITest):
    path = "/record_cards/record_cards/{id}/multi_complaints/"
    base_api_path = "/services/iris/api"

    paginate_by = 10

    @pytest.mark.parametrize("object_number", (0, 1, 3))
    def test_list(self, object_number):
        record_card = self.create_record_card()
        if object_number:
            record_card.is_multirecord = True
            record_card.save()
        [self.given_an_object(record_card, object_number) for _ in range(0, object_number)]
        response = self.list(force_params={"page_size": self.paginate_by, "id": record_card.pk})
        self.should_return_list(object_number + 1, self.paginate_by, response)

    def given_an_object(self, multirecord_record_card, object_number):
        return self.create_record_card(multirecord_from=multirecord_record_card if object_number else None)


class TestRecordCardBlock(RecordCardActionsMixin, RecordCardRestrictedTestMixin, SetUserGroupMixin, BaseOpenAPITest):
    path = "/record_cards/record_cards/{id}/block/"

    def test_record_card_block(self):
        record_card = self.create_record_card(RecordState.PENDING_VALIDATE)
        response = self.post(force_params={"id": record_card.pk})
        assert response.status_code == HTTP_200_OK
        assert record_card.recordcardblock_set.filter(user_id=get_user_traceability_id(self.user))

    def test_record_card_block_current_user(self):
        record_card = self.create_record_card(RecordState.PENDING_VALIDATE)
        expire_time = timezone.now() + timedelta(minutes=5)
        RecordCardBlock.objects.create(
            user_id=get_user_traceability_id(self.user), record_card=record_card, expire_time=expire_time
        )
        response = self.post(force_params={"id": record_card.pk})
        assert response.status_code == HTTP_200_OK
        assert record_card.recordcardblock_set.filter(user_id=get_user_traceability_id(self.user)).count() == 1

    @pytest.mark.parametrize("active_block,expected_response", (
        (False, HTTP_200_OK), (True, HTTP_409_CONFLICT)
    ))
    def test_record_card_previous_blocked_other_user(self, active_block, expected_response):
        record_card = self.create_record_card(RecordState.PENDING_VALIDATE)
        expire_time = timezone.now()
        if active_block:
            expire_delta_time = int(Parameter.get_parameter_by_key("TEMPS_TREBALL_FITXA", 10))
            expire_time += timedelta(minutes=expire_delta_time) + timedelta(minutes=5)
        RecordCardBlock.objects.create(user_id="user_id_block", record_card=record_card, expire_time=expire_time)
        response = self.post(force_params={"id": record_card.pk})
        assert response.status_code == expected_response

    @pytest.mark.parametrize("mayorship_permission,mayorship,expected_response", (
        (True, True, HTTP_200_OK),
        (True, False, HTTP_200_OK),
        (False, True, HTTP_200_OK),
        (False, False, HTTP_200_OK),
    ))
    def test_mayorship_action(self, mayorship_permission, mayorship, expected_response):
        record_kwargs = {
            "record_state_id": self.get_record_state_id(),
            "process_pk": Process.EXTERNAL_PROCESSING,
            "mayorship": mayorship
        }
        if mayorship_permission:
            record_kwargs["responsible_profile"] = self.set_permission(MAYORSHIP)

        record_card = self.create_record_card(**record_kwargs)
        response = self.post(force_params=self.get_post_params(record_card))
        assert response.status_code == expected_response

    @pytest.mark.parametrize("responsible_group,action_group,expected_response", (
        (2, 1, HTTP_200_OK),
        (2, 2, HTTP_200_OK),
        (2, 3, HTTP_403_FORBIDDEN),
    ))
    def test_can_tramit_action(self, responsible_group, action_group, expected_response):
        groups = dict_groups()
        self.set_usergroup(groups[action_group])
        record_kwargs = {
            "record_state_id": self.get_record_state_id(),
            "process_pk": Process.EXTERNAL_PROCESSING,
            "responsible_profile": groups[responsible_group]
        }
        record_card = self.create_record_card(**record_kwargs)
        response = self.post(force_params=self.get_post_params(record_card))
        assert response.status_code == expected_response

    def get_post_params(self, record_card):
        return {"id": record_card.pk}


class TestRecordCardTraceability(RecordCardActionsMixin, OpenAPIResourceListMixin, BaseOpenAPITest):
    path = "/record_cards/record_cards/{id}/traceability/"

    def test_list(self):
        record_card = self.create_record_card(RecordState.IN_PLANING)
        Comment.objects.create(reason_id=Reason.RECORDCARD_BLOCK_CHANGE, comment="RecordCard blocked",
                               record_card=record_card)

        workflow = Workflow.objects.create(main_record_card=record_card, state_id=RecordState.IN_PLANING)
        record_card.workflow = workflow
        record_card.save()
        WorkflowComment.objects.create(workflow=workflow, task=WorkflowComment.PLAN, comment="RecordCard planified")
        Comment.objects.create(reason_id=Reason.RECORDCARD_BLOCK_CHANGE, comment="RecordCard unblocked",
                               record_card=record_card)
        new_responsible = Group.objects.create(profile_ctrl_user_id="GRPAS", user_id="2222",
                                               parent=record_card.responsible_profile)
        RecordCardReasignation.objects.create(user_id=get_user_traceability_id(self.user), record_card=record_card,
                                              group=record_card.responsible_profile,
                                              previous_responsible_profile=record_card.responsible_profile,
                                              next_responsible_profile=new_responsible,
                                              reason_id=Reason.CITIZEN_RESPONSE, comment="RecordCard Reassignation")

        response = self.list(force_params={"page_size": self.paginate_by, "id": record_card.pk})
        self.should_return_list(4, None, response)


class TestRecordCardReasignationOptions(RecordCardActionsMixin, OpenAPIResourceListMixin, SetUserGroupMixin,
                                        BaseOpenAPITest):
    path = "/record_cards/record_cards/{id}/reasignations/"

    def test_list(self):
        self.given_a_group_hierarchy()
        self.given_a_record_card(RecordState.PENDING_VALIDATE, self.parent)
        self.when_reassigner_group_is(self.parent)
        self.when_group_is_responsible(self.parent)
        self.when_has_permission()
        self.when_reassignation_options_are_got()
        self.should_return_all()

    def given_a_group_hierarchy(self):
        grand_parent, parent, first_son, second_son, noambit_parent, noambit_son = create_groups(True, False)
        self.root = grand_parent
        self.parent = parent
        self.first_son = first_son
        self.second_son = second_son
        self.noambit_parent = noambit_parent
        self.noambit_son = noambit_son

    def given_a_record_card(self, state, responsible):
        self.element_detail = self.create_element_detail(validated_reassignable=False,
                                                         validation_place_days=10)
        self.record_card = self.create_record_card(record_state_id=state, element_detail=self.element_detail,
                                                   claims_number=0, responsible_profile=responsible,
                                                   reassignment_not_allowed=False)

    def when_group_is_responsible(self, group):
        self.record_card.responsible_profile = group
        self.record_card.save()

    def when_reassigner_group_is(self, group):
        self.reassigner = group
        self.user.usergroup.group = group
        self.user.usergroup.save()

    def when_has_permission(self):
        self.set_group_permissions("AAA", self.reassigner, [RECARD_REASSIGN_OUTSIDE, RECARD_REASIGN])

    def when_reassignation_options_are_got(self):
        self.result = self.list(force_params={"id": self.record_card.pk})

    def should_return_all(self):
        assert self.result.status_code == HTTP_200_OK
        options = [opt.get('id') for opt in self.result.json()]
        expected = GroupReassignation.objects.filter(
            origin_group=self.reassigner
        ).values_list('reasign_group', flat=True)
        assert set(options) == set(expected)

    def should_return_empty(self):
        assert self.result.status_code == HTTP_200_OK
        assert len(self.result.json()) == 0


class TestToogleRecordCardReasignable(UpdatePatchMixin, RecordCardActionsMixin, RecordCardRestrictedTestMixin,
                                      BaseOpenAPITest):
    detail_path = "/record_cards/record_cards/{id}/toggle-reassignable/"
    base_api_path = "/services/iris/api"

    @pytest.mark.parametrize("reassignment_not_allowed,set_noreasignable_perm,expected_response", (
        (True, True, HTTP_200_OK),
        (False, True, HTTP_200_OK),
        (True, False, HTTP_403_FORBIDDEN),
        (False, False, HTTP_403_FORBIDDEN),
    ))
    def test_reasignable_toogle_record_card(self, reassignment_not_allowed, set_noreasignable_perm, expected_response):
        self.set_usergroup()
        if set_noreasignable_perm:
            profile = mommy.make(Profile, user_id="222222")
            permission = Permission.objects.get(codename=NO_REASIGNABLE)
            ProfilePermissions.objects.create(permission=permission, profile=profile)
            GroupProfiles.objects.create(group=self.user.usergroup.group, profile=profile)
        record_card = self.create_record_card(responsible_profile=self.user.usergroup.group)
        response = self.patch(force_params={"id": record_card.pk,
                                            "reassignment_not_allowed": reassignment_not_allowed})
        record_card = RecordCard.objects.get(pk=record_card.pk)
        assert response.status_code == expected_response
        if expected_response == HTTP_200_OK:
            assert record_card.reassignment_not_allowed == reassignment_not_allowed

    @pytest.mark.parametrize("mayorship_permission,mayorship,expected_response", (
        (True, True, HTTP_200_OK),
        (True, False, HTTP_200_OK),
        (False, True, HTTP_200_OK),
        (False, False, HTTP_200_OK),
    ))
    def test_mayorship_action(self, mayorship_permission, mayorship, expected_response):
        self.set_usergroup()
        profile = mommy.make(Profile, user_id="222222")
        permission = Permission.objects.get(codename=NO_REASIGNABLE)
        ProfilePermissions.objects.create(permission=permission, profile=profile)
        GroupProfiles.objects.create(group=self.user.usergroup.group, profile=profile)

        record_kwargs = {
            "record_state_id": RecordState.PENDING_VALIDATE,
            "process_pk": Process.EXTERNAL_PROCESSING,
            "mayorship": mayorship,
            "responsible_profile": self.user.usergroup.group
        }
        if mayorship_permission:
            self.set_permission(MAYORSHIP, self.user.usergroup.group)

        record_card = self.create_record_card(**record_kwargs)

        response = self.patch(force_params={"id": record_card.pk, "reassignment_not_allowed": True})
        assert response.status_code == expected_response

    @pytest.mark.parametrize("responsible_group,action_group,expected_response", (
        (2, 1, HTTP_200_OK),
        (2, 2, HTTP_200_OK),
        (2, 3, HTTP_403_FORBIDDEN),
    ))
    def test_can_tramit_action(self, responsible_group, action_group, expected_response):
        groups = dict_groups()
        self.set_usergroup(groups[action_group])
        profile = mommy.make(Profile, user_id="222222")
        permission = Permission.objects.get(codename=NO_REASIGNABLE)
        ProfilePermissions.objects.create(permission=permission, profile=profile)
        GroupProfiles.objects.create(group=self.user.usergroup.group, profile=profile)

        record_kwargs = {
            "record_state_id": self.get_record_state_id(),
            "process_pk": Process.EXTERNAL_PROCESSING,
            "responsible_profile": groups[responsible_group]
        }
        record_card = self.create_record_card(**record_kwargs)
        response = self.patch(force_params=self.get_post_params(record_card))
        assert response.status_code == expected_response


class TestRecordCardReasignationView(PostOperationMixin, CreateRecordCardMixin, SetUserGroupMixin, SetPermissionMixin,
                                     BaseOpenAPITest):
    path = "/record_cards/record_cards/reasign/"
    base_api_path = "/services/iris/api"

    @pytest.mark.parametrize("record_card,next_responsible,reason_id,comment,expected_response", (
        (True, True, Reason.COORDINATOR_EVALUATION, "test", HTTP_201_CREATED),
        (False, True, Reason.COORDINATOR_EVALUATION, "test", HTTP_400_BAD_REQUEST),
        (True, False, Reason.COORDINATOR_EVALUATION, "test", HTTP_400_BAD_REQUEST),
        (True, True, None, "test", HTTP_400_BAD_REQUEST),
        (True, True, Reason.COORDINATOR_EVALUATION, "", HTTP_400_BAD_REQUEST),
    ))
    def test_reasignation(self, record_card, next_responsible, reason_id, comment, expected_response):
        _, parent, first_soon, _, _, _ = create_groups()
        self.set_usergroup(parent)
        self.set_group_permissions("user_id", parent, [RECARD_REASIGN])
        if record_card:
            db_record_card = self.create_record_card(validated_reassignable=True, responsible_profile=parent)
            record_card_pk = db_record_card.pk
            for _ in range(3):
                mommy.make(Conversation, user_id="2222", record_card=db_record_card, is_opened=True)
        else:
            record_card_pk = None

        next_responsible_pk = first_soon.pk if next_responsible else None

        params = {
            "record_card": record_card_pk,
            "next_responsible_profile": next_responsible_pk,
            "reason": reason_id,
            "comment": comment
        }
        response = self.post(force_params=params)
        assert response.status_code == expected_response

    @pytest.mark.parametrize("has_permissions,expected_response", (
        (True, HTTP_201_CREATED),
        (False, HTTP_403_FORBIDDEN),
    ))
    def test_permissions(self, has_permissions, expected_response):
        _, parent, first_soon, _, _, _ = create_groups()
        self.set_usergroup(parent)
        if has_permissions:
            self.set_group_permissions("22222", parent, [RECARD_REASIGN])
        record_card = self.create_record_card(validated_reassignable=True, responsible_profile=parent)
        params = {
            "record_card": record_card.pk,
            "next_responsible_profile": first_soon.pk,
            "reason": Reason.COORDINATOR_EVALUATION,
            "comment": "test comment"
        }
        response = self.post(force_params=params)
        assert response.status_code == expected_response

    @pytest.mark.parametrize("initial_state", (RecordState.CLOSED, RecordState.CANCELLED))
    def test_reasign_closed_states(self, initial_state):
        _, parent, first_soon, _, _, _ = create_groups()
        db_record_card = self.create_record_card(record_state_id=initial_state, validated_reassignable=True,
                                                 responsible_profile=parent)
        self.set_group_permissions("user_id", parent, [RECARD_REASIGN])
        for _ in range(3):
            mommy.make(Conversation, user_id="2222", record_card=db_record_card, is_opened=True)
        params = {
            "record_card": db_record_card.pk,
            "next_responsible_profile": first_soon.pk,
            "reason": Reason.COORDINATOR_EVALUATION,
            "comment": "test comment"
        }
        response = self.post(force_params=params)
        assert response.status_code == HTTP_409_CONFLICT

    @pytest.mark.parametrize(
        "same_responsibles,set_allowed_reassignations,validated_reassignable,expected_response", (
            (False, True, True, HTTP_201_CREATED),
            (True, True, True, HTTP_400_BAD_REQUEST),
            (False, False, True, HTTP_400_BAD_REQUEST),
            (False, True, False, HTTP_201_CREATED),
        ))
    def test_validation(self, same_responsibles, set_allowed_reassignations, validated_reassignable,
                        expected_response):
        _, parent, first_soon, _, _, noambit_soon = create_groups()
        record_card = self.create_record_card(validated_reassignable=validated_reassignable,
                                              responsible_profile=parent)
        self.set_group_permissions("user_id", parent, [RECARD_REASIGN])
        group = record_card.responsible_profile

        if same_responsibles:
            next_responsible = group
        else:
            next_responsible = first_soon if set_allowed_reassignations else noambit_soon

        params = {
            "record_card": record_card.pk,
            "next_responsible_profile": next_responsible.pk,
            "reason": Reason.COORDINATOR_EVALUATION,
            "comment": "test"
        }
        response = self.post(force_params=params)
        assert response.status_code == expected_response

    @pytest.mark.parametrize("mayorship_permission,mayorship,expected_response", (
        (True, True, HTTP_201_CREATED),
        (True, False, HTTP_201_CREATED),
        (False, True, HTTP_201_CREATED),
        (False, False, HTTP_201_CREATED),
    ))
    def test_mayorship_action(self, mayorship_permission, mayorship, expected_response):
        _, parent, first_soon, _, _, noambit_soon = create_groups()
        record_kwargs = {
            "record_state_id": RecordState.PENDING_VALIDATE,
            "process_pk": Process.EXTERNAL_PROCESSING,
            "mayorship": mayorship,
            "validated_reassignable": True,
            "responsible_profile": parent
        }

        if mayorship_permission:
            self.set_permission(MAYORSHIP, group=parent)

        record_card = self.create_record_card(**record_kwargs)
        self.set_group_permissions("user_id", parent, [RECARD_REASIGN])
        response = self.post(force_params={
            "record_card": record_card.pk,
            "next_responsible_profile": first_soon.pk,
            "reason": Reason.COORDINATOR_EVALUATION,
            "comment": "test test"
        })
        assert response.status_code == expected_response

    @pytest.mark.parametrize("responsible_group,action_group,expected_response", (
        (2, 1, HTTP_201_CREATED),
        (2, 2, HTTP_201_CREATED),
        (2, 4, HTTP_400_BAD_REQUEST),
    ))
    def test_can_tramit_action(self, responsible_group, action_group, expected_response):
        groups = dict_groups()
        self.set_usergroup(groups[action_group])
        self.set_group_permissions("user_id", self.user.usergroup.group, [RECARD_REASIGN])
        record_kwargs = {
            "record_state_id": RecordState.PENDING_VALIDATE,
            "process_pk": Process.EXTERNAL_PROCESSING,
            "validated_reassignable": True,
            "responsible_profile": groups[responsible_group]
        }
        GroupReassignation.objects.create(origin_group=groups[action_group], reasign_group=groups[3])

        record_card = self.create_record_card(**record_kwargs)
        response = self.post(force_params={
            "record_card": record_card.pk,
            "next_responsible_profile": groups[3].pk,
            "reason": Reason.COORDINATOR_EVALUATION,
            "comment": "test test"
        })
        assert response.status_code == expected_response


class TestRecordChunkedFileApi(CreateRecordCardMixin, PostOperationMixin, BaseOpenAPITest):
    path = "/record_cards/record_files/upload/"
    base_api_path = "/services/iris/api"
    extra_chunks_path = "/record_cards/record_files/upload/chunk/{id}/"

    DEFAULT_CHUNK_SIZE = 64 * 2 ** 10  # 65536 bytes

    @pytest.mark.parametrize("initial_state,has_permission,expected_response", (
        (RecordState.CLOSED, False, HTTP_403_FORBIDDEN),
        (RecordState.CANCELLED, False, HTTP_403_FORBIDDEN),
        (RecordState.CLOSED, True, HTTP_200_OK),
        (RecordState.CANCELLED, True, HTTP_200_OK),
    ))
    def test_file_upload_closed_states(self, image_file, initial_state, has_permission, expected_response):
        record_card = self.create_record_card(record_state_id=initial_state)
        if has_permission:
            self.set_group_permissions("user_id", record_card.responsible_profile, [RECARD_CLOSED_FILES])
        image_base64 = base64.b64encode(image_file.tobytes())
        image_length = len(image_base64)
        chunks = self.file_chunks(image_base64)
        force_params = {"filename": "img.png", "record_card_id": record_card.pk}
        force_params.update(**{"file": ContentFile(chunks[0])})
        self.client.credentials(**{"HTTP_CONTENT_RANGE": "bytes {}-{}/{}".format(0, self.DEFAULT_CHUNK_SIZE - 1,
                                                                                 image_length)})

        response = self.operation_test("put", self.path, self.spec()["paths"][self.path]["put"], force_params,
                                       format_value="multipart")
        assert response.status_code == expected_response

    def file_chunks(self, image_base64):
        prepare_chunks = True
        chunks = []
        offset = 0
        while prepare_chunks:
            if offset > len(image_base64):
                break
            start = offset
            end = offset + self.DEFAULT_CHUNK_SIZE
            chunks.append(image_base64[start:end])
            offset = end
        return chunks


class TestRecordCardClaimView(RecordCardActionsMixin, RecordCardRestrictedTestMixin, BaseOpenAPITest):
    path = "/record_cards/record_cards/{id}/claim/"

    @pytest.mark.parametrize("mayorship_permission,mayorship,expected_response", (
        (True, True, HTTP_201_CREATED),
        (True, False, HTTP_201_CREATED),
        (False, False, HTTP_201_CREATED),
    ))
    def test_mayorship_action(self, mayorship_permission, mayorship, expected_response):
        record_kwargs = {
            "record_state_id": self.get_record_state_id(),
            "process_pk": Process.EXTERNAL_PROCESSING,
            "mayorship": mayorship
        }
        if mayorship_permission:
            record_kwargs["responsible_profile"] = self.set_permission(MAYORSHIP)

        record_card = self.create_record_card(**record_kwargs)
        self.set_group_permissions("user_id", self.user.usergroup.group, [RECARD_CLAIM])
        response = self.post(force_params=self.get_post_params(record_card))
        assert response.status_code == expected_response

    @pytest.mark.parametrize("responsible_group,action_group,expected_response", (
        (2, 1, HTTP_201_CREATED),
        (2, 2, HTTP_201_CREATED),
    ))
    def test_can_tramit_action(self, responsible_group, action_group, expected_response):
        groups = dict_groups()
        self.set_usergroup(groups[action_group])
        self.set_group_permissions("user_id", self.user.usergroup.group, [RECARD_CLAIM])
        record_kwargs = {
            "record_state_id": self.get_record_state_id(),
            "process_pk": Process.EXTERNAL_PROCESSING,
            "responsible_profile": groups[responsible_group]
        }
        record_card = self.create_record_card(**record_kwargs)
        response = self.post(force_params=self.get_post_params(record_card))
        assert response.status_code == expected_response

    def get_record_state_id(self):
        return RecordState.CLOSED

    def get_post_params(self, record_card):
        return {"id": record_card.pk, "description": "description"}

    @pytest.mark.parametrize(
        "description,initial_state,exists_previous_claim,claim_limit_exceded,applicant_blocked,resolution_type_id,"
        "ans_limit_delta,expected_response", (
            ("description", RecordState.CLOSED, False, False, False, None, None, HTTP_201_CREATED),
            ("description", RecordState.CANCELLED, False, False, False, None, None, HTTP_201_CREATED),
            ("", RecordState.CLOSED, False, False, False, None, None, HTTP_400_BAD_REQUEST),
            ("description", RecordState.PENDING_VALIDATE, False, False, False, None, None, HTTP_409_CONFLICT),
            ("description", RecordState.CLOSED, True, False, False, None, None, HTTP_201_CREATED),
            ("description", RecordState.CLOSED, False, True, False, None, None, HTTP_409_CONFLICT),
            ("description", RecordState.CLOSED, False, False, True, None, None, HTTP_409_CONFLICT),
            ("description", RecordState.CLOSED, False, False, False, ResolutionType.PROGRAM_ACTION, True,
             HTTP_201_CREATED),
            ("description", RecordState.CLOSED, False, False, False, ResolutionType.PROGRAM_ACTION, None,
             HTTP_409_CONFLICT),
        ))
    def test_claim_record_card(self, description, initial_state, exists_previous_claim, claim_limit_exceded,
                               applicant_blocked, resolution_type_id, ans_limit_delta, expected_response):
        citizen = mommy.make(Citizen, blocked=applicant_blocked, user_id="2222")
        applicant = mommy.make(Applicant, citizen=citizen, user_id="2222")

        if ans_limit_delta:
            ans_limit_delta = -24 * 365

        record_card = self.create_record_card(record_state_id=initial_state, applicant=applicant, create_worflow=True,
                                              ans_limit_delta=ans_limit_delta)
        self.set_group_permissions("user_id", record_card.responsible_profile, [RECARD_CLAIM])

        if not resolution_type_id:
            resolution_type_id = mommy.make(ResolutionType, user_id="222", can_claim_inside_ans=True).pk

        WorkflowResolution.objects.create(workflow=record_card.workflow, resolution_type_id=resolution_type_id)

        if exists_previous_claim:
            self.create_record_card(claimed_from_id=record_card.pk)

        if claim_limit_exceded:
            RecordCardStateHistory.objects.create(record_card=record_card, group=record_card.responsible_profile,
                                                  previous_state_id=RecordState.PENDING_VALIDATE,
                                                  next_state_id=initial_state, user_id="22222", automatic=False)
            claim_days_limit = int(Parameter.get_parameter_by_key("DIES_PER_RECLAMAR", 60))
            RecordCardStateHistory.objects.filter(next_state__in=RecordState.CLOSED_STATES,
                                                  record_card_id=record_card.pk).update(
                created_at=timezone.now() - timedelta(days=claim_days_limit + 2))

        params = {"description": description, "id": record_card.pk}
        response = self.post(force_params=params)
        assert response.status_code == expected_response
        if expected_response == HTTP_201_CREATED:
            claim = RecordCard.objects.get(normalized_record_id=response.json()["normalized_record_id"])
            record_card = RecordCard.objects.get(pk=record_card.pk)

            assert claim.record_state_id == RecordState.PENDING_VALIDATE
            assert claim.user_id == get_user_traceability_id(self.user)
            assert claim.claims_number == 2
            assert claim.description == description
            assert claim.claimed_from_id == record_card.pk
            assert claim.citizen_alarm is True
            assert claim.alarm is True
            assert RecordCardAlarms(claim, record_card.responsible_profile).citizen_claim_alarm is True
            assert claim.normalized_record_id == "{}-02".format(record_card.normalized_record_id)

            assert record_card.claims_number == 2
            assert record_card.citizen_alarm is True
            assert record_card.alarm is True

    @pytest.mark.parametrize("has_permissions,expected_response", (
        (True, HTTP_201_CREATED),
        (False, HTTP_403_FORBIDDEN),
    ))
    def test_permissions(self, has_permissions, expected_response):
        record_card = self.create_record_card(record_state_id=RecordState.CLOSED, create_worflow=True)
        if has_permissions:
            self.set_group_permissions("user_id", record_card.responsible_profile, [RECARD_CLAIM])
        params = {"description": "test description", "id": record_card.pk}
        response = self.post(force_params=params)
        assert response.status_code == expected_response

    def test_claim_record_card_autovalidate(self):
        citizen = mommy.make(Citizen, blocked=False, user_id="2222")
        applicant = mommy.make(Applicant, citizen=citizen, user_id="2222")
        element_detail = self.create_element_detail(autovalidate_records=True, process_id=Process.EXTERNAL_PROCESSING)
        record_card = self.create_record_card(record_state_id=RecordState.CLOSED, applicant=applicant,
                                              create_worflow=True, element_detail=element_detail)
        self.set_group_permissions("user_id", record_card.responsible_profile, [RECARD_CLAIM])

        resolution_type_id = mommy.make(ResolutionType, user_id="222", can_claim_inside_ans=True).pk
        WorkflowResolution.objects.create(workflow=record_card.workflow, resolution_type_id=resolution_type_id)

        params = {"description": "description", "id": record_card.pk}
        response = self.post(force_params=params)
        assert response.status_code == HTTP_201_CREATED
        claim = RecordCard.objects.get(normalized_record_id=response.json()["normalized_record_id"])
        assert claim.record_state_id == RecordState.EXTERNAL_PROCESSING


class TestRecordCardClaimCheckView(RecordCardActionsMixin, BaseOpenAPITest):
    path = "/record_cards/record_cards/{id}/claim/check/"

    @pytest.mark.parametrize(
        "initial_state,exists_previous_claim,claim_limit_exceded,applicant_blocked,resolution_type_id,"
        "ans_limit_delta,can_confirm,reason_type,claim_type,reason_comment_id", (
            (RecordState.CLOSED, False, False, False, None, None, True, None, "record", None),
            (RecordState.CANCELLED, False, False, False, None, None, True, None, "record", None),
            (RecordState.IN_PLANING, False, False, False, None, None, False, str, "comment",
             Reason.CLAIM_CITIZEN_REQUEST),
            (RecordState.CLOSED, True, False, False, None, None, True, None, "record", None),
            (RecordState.CLOSED, False, True, False, None, None, False, str, None, None),
            (RecordState.CLOSED, False, False, True, None, None, False, str, None, None),
            (RecordState.CLOSED, False, False, False, ResolutionType.PROGRAM_ACTION, True, True, None, "record",
             None),
            (RecordState.CLOSED, False, False, False, ResolutionType.PROGRAM_ACTION, None, False, str, "comment",
             Reason.CLAIM_CITIZEN_REQUEST),
            (RecordState.CANCELLED, False, False, False, ResolutionType.PROGRAM_ACTION, True, True, None, "record",
             None),
            (RecordState.CANCELLED, False, False, False, ResolutionType.PROGRAM_ACTION, None, False, str, "comment",
             Reason.CLAIM_CITIZEN_REQUEST),
        ))
    def test_claim_check_record_card(self, initial_state, exists_previous_claim, claim_limit_exceded, applicant_blocked,
                                     resolution_type_id, ans_limit_delta, can_confirm, reason_type, claim_type,
                                     reason_comment_id):
        citizen = mommy.make(Citizen, blocked=applicant_blocked, user_id="2222")
        applicant = mommy.make(Applicant, citizen=citizen, user_id="2222")

        if ans_limit_delta:
            ans_limit_delta = -24 * 365

        record_card = self.create_record_card(record_state_id=initial_state, applicant=applicant, create_worflow=True,
                                              ans_limit_delta=ans_limit_delta)
        self.set_group_permissions("user_id", self.user.usergroup.group, [RECARD_CLAIM])
        if not resolution_type_id:
            resolution_type_id = mommy.make(ResolutionType, user_id="222", can_claim_inside_ans=True).pk
        WorkflowResolution.objects.create(workflow=record_card.workflow, resolution_type_id=resolution_type_id)

        if exists_previous_claim:
            self.create_record_card(claimed_from_id=record_card.pk)

        if claim_limit_exceded:
            RecordCardStateHistory.objects.create(record_card=record_card, group=record_card.responsible_profile,
                                                  previous_state_id=RecordState.PENDING_VALIDATE,
                                                  next_state_id=initial_state, user_id="22222", automatic=False)
            claim_days_limit = int(Parameter.get_parameter_by_key("DIES_PER_RECLAMAR", 60))
            RecordCardStateHistory.objects.filter(next_state__in=RecordState.CLOSED_STATES,
                                                  record_card_id=record_card.pk).update(
                created_at=timezone.now() - timedelta(days=claim_days_limit + 2))

        response = self.post(force_params={"id": record_card.pk})
        assert response.status_code == HTTP_200_OK
        action_data = response.json()["__action__"]
        assert action_data["can_confirm"] is can_confirm
        if not reason_type:
            assert isinstance(action_data["reason"], type(None))
        else:
            assert isinstance(action_data["reason"], reason_type)
        assert action_data["claim_type"] == claim_type
        assert action_data.get("reason_comment_id") == reason_comment_id
        if record_card.record_state_id not in RecordState.CLOSED_STATES:
            assert action_data["next_state"] == record_card.record_state_id
        else:
            assert action_data["next_state"] == RecordState.PENDING_VALIDATE

        assert action_data["next_group"]["id"] == record_card.responsible_profile_id
        assert action_data["different_ambit"] is False

    @pytest.mark.parametrize("has_permissions,expected_response", (
        (True, HTTP_200_OK),
        (False, HTTP_403_FORBIDDEN),
    ))
    def test_permissions(self, has_permissions, expected_response):
        record_card = self.create_record_card(record_state_id=RecordState.CLOSED, create_worflow=True)
        if has_permissions:
            self.set_group_permissions("user_id", record_card.responsible_profile, [RECARD_CLAIM])
        params = {"id": record_card.pk}
        response = self.post(force_params=params)
        assert response.status_code == expected_response


class TestWorkflowList(OpenAPIResourceListMixin, CreateRecordCardMixin, BaseOpenAPITest):
    path = "/record_cards/workflows/"
    base_api_path = "/services/iris/api"

    def given_an_object(self):
        record_card = self.create_record_card(citizen_dni=str(uuid.uuid4())[:9])
        next_state_code = record_card.next_step_code
        workflow = Workflow.objects.create(main_record_card=record_card, state_id=next_state_code)
        record_card.workflow = workflow

        record_card.record_state_id = next_state_code
        record_card.save()
        return workflow


class TestWorkflowListFilter(TestWorkflowList):
    use_extra_get_params = True

    @pytest.mark.parametrize("object_number,filter_normalized_record_id", ((1, True), (3, False)))
    def test_list(self, object_number, filter_normalized_record_id):
        workflows = [self.given_an_object() for _ in range(0, object_number)]
        params = {"page_size": self.paginate_by}
        if filter_normalized_record_id:
            params["normalized_record_id"] = workflows[0].main_record_card.normalized_record_id
        else:
            params["applicant_identifier"] = workflows[0].main_record_card.request.applicant.citizen.dni
        response = self.list(force_params=params)
        self.should_return_list(1, self.paginate_by, response)


class WorkflowRestrictedTestMixin(CreateRecordCardMixin, SetUserGroupMixin, SetPermissionMixin):

    @pytest.mark.parametrize("mayorship_permission,mayorship,expected_response", (
        (True, True, HTTP_204_NO_CONTENT),
        (True, False, HTTP_204_NO_CONTENT),
        (False, True, HTTP_204_NO_CONTENT),
        (False, False, HTTP_204_NO_CONTENT),
    ))
    def test_mayorship_action(self, mayorship_permission, mayorship, expected_response):
        record_kwargs = {
            "record_state_id": self.get_record_state_id(),
            "process_pk": Process.EVALUATION_RESOLUTION_RESPONSE,
            "mayorship": mayorship
        }
        if mayorship_permission:
            record_kwargs["responsible_profile"] = self.set_permission(MAYORSHIP)

        record_card = self.create_record_card(**record_kwargs)
        self.set_group_permissions("user_id", record_card.responsible_profile, [RECARD_PLAN_RESOL])
        workflow = Workflow.objects.create(main_record_card=record_card, state_id=self.get_record_state_id())
        record_card.workflow = workflow
        record_card.save()

        response = self.post(force_params=self.get_post_params(workflow))
        assert response.status_code == expected_response

    def get_record_state_id(self):
        return RecordState.IN_PLANING

    def get_post_params(self, workflow):
        return {"id": workflow.pk}

    @pytest.mark.parametrize("responsible_group,action_group,expected_response", (
        (2, 1, HTTP_204_NO_CONTENT),
        (2, 2, HTTP_204_NO_CONTENT),
        (2, 3, HTTP_403_FORBIDDEN),
    ))
    def test_can_tramit_action(self, responsible_group, action_group, expected_response):
        groups = dict_groups()
        self.set_usergroup(groups[action_group])
        self.set_group_permissions("user_id", groups[action_group], [RECARD_PLAN_RESOL])
        record_card = self.create_record_card(responsible_profile=groups[responsible_group],
                                              process_pk=Process.EVALUATION_RESOLUTION_RESPONSE)
        workflow = Workflow.objects.create(main_record_card=record_card, state_id=self.get_record_state_id())
        record_card.workflow = workflow
        record_card.save()

        response = self.post(force_params=self.get_post_params(workflow))
        assert response.status_code == expected_response


class TestWorkflowPlan(RecordCardActionsMixin, CreateDerivationsMixin, WorkflowRestrictedTestMixin, BaseOpenAPITest):
    path = "/record_cards/workflows/{id}/plan/"

    @pytest.mark.parametrize(
        "start_date_process,comment,action_required,expected_response,process_pk,initial_state_pk,expected_state_pk,"
        "create_derivation", (
            ("2012-02-02", "test comment test", False, HTTP_404_NOT_FOUND, Process.CLOSED_DIRECTLY,
             RecordState.PENDING_VALIDATE, RecordState.PENDING_ANSWER, False),
            ("2012-02-02", "test comment test", True, HTTP_404_NOT_FOUND, Process.CLOSED_DIRECTLY,
             RecordState.PENDING_VALIDATE, RecordState.PENDING_ANSWER, False),
            ("2012-02-02", "test comment test", True, HTTP_204_NO_CONTENT,
             Process.EVALUATION_RESOLUTION_RESPONSE, RecordState.IN_PLANING, RecordState.IN_RESOLUTION, True),
            ("", "test comment test", False, HTTP_400_BAD_REQUEST, Process.EVALUATION_RESOLUTION_RESPONSE,
             RecordState.IN_PLANING, RecordState.PENDING_ANSWER, False),
            ("2012-02-02", "", False, HTTP_400_BAD_REQUEST, Process.EVALUATION_RESOLUTION_RESPONSE,
             RecordState.IN_PLANING, RecordState.PENDING_ANSWER, False),
        ))
    def test_plan_workflow(self, start_date_process, comment, action_required, expected_response, process_pk,
                           initial_state_pk, expected_state_pk, create_derivation):
        record_card = self.create_record_card(initial_state_pk, process_pk=process_pk)
        self.set_group_permissions("user_id", record_card.responsible_profile, [RECARD_PLAN_RESOL])
        workflow = Workflow.objects.create(main_record_card=record_card, state_id=initial_state_pk)
        record_card.workflow = workflow
        record_card.save()

        plan_responsible_profile = record_card.responsible_profile.description
        if create_derivation:
            derivated_profile = self.create_direct_derivation(record_card.element_detail_id, expected_state_pk)
        else:
            derivated_profile = record_card.responsible_profile
        response = self.post(force_params={"id": workflow.pk, "responsible_profile": plan_responsible_profile,
                                           "start_date_process": start_date_process, "comment": comment,
                                           "action_required": action_required})
        assert response.status_code == expected_response
        record_card = RecordCard.objects.get(pk=record_card.pk)
        assert record_card.responsible_profile == derivated_profile
        if expected_response == HTTP_204_NO_CONTENT:
            assert WorkflowComment.objects.get(workflow=workflow, task=WorkflowComment.PLAN).comment == comment
            assert record_card.record_state_id == expected_state_pk
            assert record_card.recordcardaudit.planif_user == get_user_traceability_id(self.user)
            assert Workflow.objects.get(pk=workflow.pk).state_id == expected_state_pk
            assert WorkflowPlan.objects.get(workflow_id=workflow.pk).responsible_profile == plan_responsible_profile
            assert RecordCardStateHistory.objects.get(record_card=record_card, next_state_id=expected_state_pk,
                                                      automatic=False)

    @pytest.mark.parametrize("has_permissions,expected_response", (
        (True, HTTP_204_NO_CONTENT),
        (False, HTTP_403_FORBIDDEN),
    ))
    def test_permissions(self, has_permissions, expected_response):
        record_card = self.create_record_card(RecordState.IN_PLANING, process_pk=Process.EVALUATION_RESOLUTION_RESPONSE)
        if has_permissions:
            self.set_group_permissions("22222", record_card.responsible_profile, [RECARD_PLAN_RESOL])
        workflow = Workflow.objects.create(main_record_card=record_card, state_id=RecordState.IN_PLANING)
        record_card.workflow = workflow
        record_card.save()

        response = self.post(force_params={"id": workflow.pk,
                                           "responsible_profile": record_card.responsible_profile.description,
                                           "start_date_process": "2012-12-12", "comment": "test comment test",
                                           "action_required": False})
        assert response.status_code == expected_response

    def test_state_changed_signal(self):
        signal = Mock(spec=Signal)
        with patch("record_cards.models.record_card_state_changed", signal):
            record_card = self.create_record_card(RecordState.IN_PLANING,
                                                  process_pk=Process.EVALUATION_RESOLUTION_RESPONSE)
            self.set_group_permissions("user_id", record_card.responsible_profile, [RECARD_PLAN_RESOL])
            workflow = Workflow.objects.create(main_record_card=record_card, state_id=RecordState.IN_PLANING)
            record_card.workflow = workflow
            record_card.save()

            response = self.post(force_params={"id": workflow.pk, "responsible_profile": "test",
                                               "start_date_process": "2012-02-02", "comment": "test comment test",
                                               "action_required": False})
            assert response.status_code == HTTP_204_NO_CONTENT
            for workflow_record_card in workflow.recordcard_set.all():
                signal.send_robust.assert_called_with(record_card=workflow_record_card, sender=RecordCard)

    def get_post_params(self, workflow):
        return {"id": workflow.pk, "responsible_profile": "test", "start_date_process": "2012-02-02",
                "comment": "test comment test", "action_required": False}


class TestWorkflowPlanCheck(RecordCardActionsMixin, CreateDerivationsMixin, BaseOpenAPITest):
    path = "/record_cards/workflows/{id}/plan/check/"

    def test_plan_workflow_check_derivation_outambit(self):
        _, parent, _, _, noambit_parent, _ = create_groups()
        record_card = self.create_record_card(RecordState.IN_PLANING, process_pk=Process.EVALUATION_RESOLUTION_RESPONSE,
                                              responsible_profile=parent)
        self.set_group_permissions("user_id", record_card.responsible_profile, [RECARD_PLAN_RESOL])
        workflow = Workflow.objects.create(main_record_card=record_card, state_id=RecordState.IN_PLANING)
        record_card.workflow = workflow
        record_card.save()

        plan_responsible_profile = record_card.responsible_profile.description
        self.create_direct_derivation(record_card.element_detail_id, RecordState.IN_RESOLUTION, group=noambit_parent)

        response = self.post(force_params={"id": workflow.pk, "responsible_profile": plan_responsible_profile,
                                           "start_date_process": "2020-02-02", "comment": "test comment test",
                                           "action_required": True})
        assert response.status_code == HTTP_200_OK
        response_data = response.json()
        assert response_data["__action__"]["can_confirm"] is True
        assert response_data["__action__"]["reason"] is None
        assert response_data["__action__"]["next_group"]["id"] == noambit_parent.pk
        assert response_data["__action__"]["next_state"] == RecordState.IN_RESOLUTION
        assert response_data["__action__"]["different_ambit"] is True

    def test_plan_workflow_check_derivation_ambit(self):
        _, parent, _, soon, _, _ = create_groups()
        record_card = self.create_record_card(RecordState.IN_PLANING, process_pk=Process.EVALUATION_RESOLUTION_RESPONSE,
                                              responsible_profile=parent)
        self.set_group_permissions("user_id", record_card.responsible_profile, [RECARD_PLAN_RESOL])
        workflow = Workflow.objects.create(main_record_card=record_card, state_id=RecordState.IN_PLANING)
        record_card.workflow = workflow
        record_card.save()

        plan_responsible_profile = record_card.responsible_profile.description
        self.create_direct_derivation(record_card.element_detail_id, RecordState.IN_RESOLUTION, group=soon)

        response = self.post(force_params={"id": workflow.pk, "responsible_profile": plan_responsible_profile,
                                           "start_date_process": "2020-02-02", "comment": "test comment test",
                                           "action_required": True})
        assert response.status_code == HTTP_200_OK
        response_data = response.json()
        assert response_data["__action__"]["can_confirm"] is True
        assert response_data["__action__"]["reason"] is None
        assert response_data["__action__"]["next_group"]["id"] == soon.pk
        assert response_data["__action__"]["next_state"] == RecordState.IN_RESOLUTION
        assert response_data["__action__"]["different_ambit"] is False

    def test_plan_workflow_check_noderivation(self):
        record_card = self.create_record_card(RecordState.IN_PLANING, process_pk=Process.EVALUATION_RESOLUTION_RESPONSE)
        self.set_group_permissions("user_id", record_card.responsible_profile, [RECARD_PLAN_RESOL])
        workflow = Workflow.objects.create(main_record_card=record_card, state_id=RecordState.IN_PLANING)
        record_card.workflow = workflow
        record_card.save()

        plan_responsible_profile = record_card.responsible_profile.description
        response = self.post(force_params={"id": workflow.pk, "responsible_profile": plan_responsible_profile,
                                           "start_date_process": "2020-02-02", "comment": "test comment test",
                                           "action_required": True})
        assert response.status_code == HTTP_200_OK
        response_data = response.json()
        assert response_data["__action__"]["can_confirm"] is True
        assert response_data["__action__"]["reason"] is None
        assert response_data["__action__"]["next_group"]["id"] == record_card.responsible_profile_id
        assert response_data["__action__"]["next_state"] == RecordState.IN_RESOLUTION
        assert response_data["__action__"]["different_ambit"] is False


class TestWorkflowResolute(RecordCardActionsMixin, CreateDerivationsMixin, WorkflowRestrictedTestMixin,
                           BaseOpenAPITest):
    path = "/record_cards/workflows/{id}/resolute/"

    @pytest.mark.parametrize(
        "service_person_incharge,resolution_type,resolution_date,requires_appointment,"
        "resolution_comment,initial_state_pk,expected_state_pk,expected_response,create_derivation", (
            ("test", 1, "2019-02-02", False, "test comment",
             RecordState.IN_RESOLUTION, RecordState.PENDING_ANSWER, HTTP_400_BAD_REQUEST, False),
            ("test", 1, "2019-02-02 00:00", False, "test comment",
             RecordState.IN_RESOLUTION, RecordState.PENDING_ANSWER, HTTP_204_NO_CONTENT, True),
            ("test", 1, None, False, "test comment",
             RecordState.IN_RESOLUTION, RecordState.PENDING_ANSWER, HTTP_204_NO_CONTENT, False),
            ("", 1, None, False, "test comment",
             RecordState.IN_RESOLUTION, RecordState.PENDING_ANSWER, HTTP_204_NO_CONTENT, True),
            ("test", 1, "2019-02-02 00:00", True, "test comment",
             RecordState.IN_RESOLUTION, RecordState.PENDING_ANSWER, HTTP_204_NO_CONTENT, True),
            ("", 1, "2019-02-02 00:00", True, "test comment",
             RecordState.IN_RESOLUTION, RecordState.PENDING_ANSWER, HTTP_400_BAD_REQUEST, False),
            ("Test", 1, None, True, "test comment",
             RecordState.IN_RESOLUTION, RecordState.PENDING_ANSWER, HTTP_400_BAD_REQUEST, False),
        )
    )
    def test_resolute_workflow(self, service_person_incharge, resolution_type, resolution_date, requires_appointment,
                               resolution_comment, initial_state_pk, expected_state_pk, expected_response,
                               create_derivation):
        record_card = self.create_record_card(initial_state_pk, process_pk=Process.PLANING_RESOLUTION_RESPONSE,
                                              requires_appointment=requires_appointment,
                                              create_record_card_response=True)
        self.set_group_permissions("user_id", record_card.responsible_profile, [RECARD_PLAN_RESOL])

        workflow = Workflow.objects.create(main_record_card=record_card, state_id=initial_state_pk)
        record_card.workflow = workflow
        record_card.save()

        if create_derivation:
            derivated_profile = self.create_direct_derivation(record_card.element_detail_id, expected_state_pk)
        else:
            derivated_profile = record_card.responsible_profile

        if resolution_type and resolution_type < 6:
            mommy.make(ResolutionType, id=resolution_type, user_id="2222")

        params = {
            "id": workflow.pk,
            "service_person_incharge": service_person_incharge,
            "resolution_type": resolution_type,
            "resolution_date": resolution_date,
            "resolution_comment": resolution_comment
        }
        response = self.post(force_params=params)
        assert response.status_code == expected_response
        record_card = RecordCard.objects.get(pk=record_card.pk)
        assert record_card.responsible_profile == derivated_profile

        if expected_response == HTTP_204_NO_CONTENT:
            assert record_card.recordcardaudit.resol_user == get_user_traceability_id(self.user)
            assert record_card.recordcardaudit.resol_comment == resolution_comment
            assert WorkflowComment.objects.get(
                workflow=workflow, task=WorkflowComment.RESOLUTION).comment == resolution_comment
            assert record_card.record_state_id == expected_state_pk
            assert Workflow.objects.get(pk=workflow.pk).state_id == expected_state_pk
            assert WorkflowResolution.objects.get(workflow_id=workflow.pk).resolution_type_id == resolution_type
            assert RecordCardStateHistory.objects.get(record_card=record_card, next_state_id=expected_state_pk,
                                                      automatic=False)

    def test_state_changed_signal(self):
        signal = Mock(spec=Signal)
        with patch("record_cards.models.record_card_state_changed", signal):
            record_card = self.create_record_card(RecordState.IN_RESOLUTION,
                                                  process_pk=Process.PLANING_RESOLUTION_RESPONSE)
            self.set_group_permissions("user_id", record_card.responsible_profile, [RECARD_PLAN_RESOL])
            workflow = Workflow.objects.create(main_record_card=record_card, state_id=RecordState.IN_RESOLUTION)
            record_card.workflow = workflow
            record_card.save()

            response = self.post(force_params={"id": workflow.pk, "service_person_incharge": "test",
                                               "resolution_type": mommy.make(ResolutionType, id=2000,
                                                                             user_id="2222").pk,
                                               "resolution_date": "2019-02-02 19:00",
                                               "resolution_comment": "test comment resolution"})
            assert response.status_code == HTTP_204_NO_CONTENT
            for workflow_record_card in workflow.recordcard_set.all():
                signal.send_robust.assert_called_with(record_card=workflow_record_card, sender=RecordCard)

    @pytest.mark.parametrize("has_permissions,expected_response", (
        (True, HTTP_204_NO_CONTENT),
        (False, HTTP_403_FORBIDDEN),
    ))
    def test_permissions(self, has_permissions, expected_response):
        record_card = self.create_record_card(RecordState.IN_RESOLUTION,
                                              process_pk=Process.PLANING_RESOLUTION_RESPONSE)
        if has_permissions:
            self.set_group_permissions("22222", record_card.responsible_profile, [RECARD_PLAN_RESOL])
        workflow = Workflow.objects.create(main_record_card=record_card, state_id=RecordState.IN_RESOLUTION)
        record_card.workflow = workflow
        record_card.save()

        response = self.post(force_params={"id": workflow.pk, "service_person_incharge": "test",
                                           "resolution_type": mommy.make(ResolutionType, id=2000,
                                                                         user_id="2222").pk,
                                           "resolution_date": "2019-02-02 19:00",
                                           "resolution_comment": "test comment resolution"})
        assert response.status_code == expected_response

    def get_record_state_id(self):
        return RecordState.IN_RESOLUTION

    def get_post_params(self, workflow):
        return {"id": workflow.pk, "service_person_incharge": "test",
                "resolution_type": mommy.make(ResolutionType, id=2000, user_id="2222").pk,
                "resolution_date": "2019-02-02 19:00", "resolution_comment": "test comment resolution"}

    def test_automatically_closed(self):
        record_card = self.create_record_card(RecordState.IN_RESOLUTION, create_record_card_response=True,
                                              process_pk=Process.PLANING_RESOLUTION_RESPONSE)
        self.set_group_permissions("user_id", record_card.responsible_profile, [RECARD_PLAN_RESOL])
        record_card.recordcardresponse.response_channel_id = ResponseChannel.NONE
        record_card.recordcardresponse.save()

        workflow = Workflow.objects.create(main_record_card=record_card, state_id=RecordState.IN_RESOLUTION)
        record_card.workflow = workflow
        record_card.save()

        response = self.post(force_params={"id": workflow.pk, "service_person_incharge": "test",
                                           "resolution_type": mommy.make(ResolutionType, id=2000, user_id="2222").pk,
                                           "resolution_date": "2019-02-02 19:00", "resolution_comment": "test test"})

        assert response.status_code == HTTP_204_NO_CONTENT
        record_card = RecordCard.objects.get(pk=record_card.pk)
        assert record_card.record_state_id == RecordState.CLOSED
        assert record_card.workflow.state_id == RecordState.CLOSED
        assert Comment.objects.get(record_card=record_card, reason=Reason.RECORDCARD_AUTOMATICALLY_CLOSED)


class TestWorkflowResoluteCheck(RecordCardActionsMixin, CreateDerivationsMixin, BaseOpenAPITest):
    path = "/record_cards/workflows/{id}/resolute/check/"

    def test_resolute_workflow_check_derivation_outambit(self):
        _, parent, _, _, noambit_parent, _ = create_groups()
        record_card = self.create_record_card(RecordState.IN_RESOLUTION, process_pk=Process.PLANING_RESOLUTION_RESPONSE,
                                              requires_appointment=False, responsible_profile=parent)
        self.set_group_permissions("user_id", record_card.responsible_profile, [RECARD_PLAN_RESOL])

        workflow = Workflow.objects.create(main_record_card=record_card, state_id=RecordState.IN_RESOLUTION)
        record_card.workflow = workflow
        record_card.save()

        self.create_direct_derivation(record_card.element_detail_id, RecordState.PENDING_ANSWER, group=noambit_parent)

        params = {
            "id": workflow.pk,
            "service_person_incharge": "test",
            "resolution_type": ResolutionType.PROGRAM_ACTION,
            "resolution_date": "2020-02-02 00:00",
            "resolution_comment": "test comment"
        }
        response = self.post(force_params=params)
        assert response.status_code == HTTP_200_OK
        response_data = response.json()
        assert response_data["__action__"]["can_confirm"] is True
        assert response_data["__action__"]["reason"] is None
        assert response_data["__action__"]["next_group"]["id"] == noambit_parent.pk
        assert response_data["__action__"]["next_state"] == RecordState.PENDING_ANSWER
        assert response_data["__action__"]["different_ambit"] is True

    def test_resolute_workflow_check_derivation_ambit(self):
        _, parent, _, soon, _, _ = create_groups()
        record_card = self.create_record_card(RecordState.IN_RESOLUTION, process_pk=Process.PLANING_RESOLUTION_RESPONSE,
                                              requires_appointment=False, responsible_profile=parent)
        self.set_group_permissions("user_id", record_card.responsible_profile, [RECARD_PLAN_RESOL])

        workflow = Workflow.objects.create(main_record_card=record_card, state_id=RecordState.IN_RESOLUTION)
        record_card.workflow = workflow
        record_card.save()

        self.create_direct_derivation(record_card.element_detail_id, RecordState.PENDING_ANSWER, group=soon)

        params = {
            "id": workflow.pk,
            "service_person_incharge": "test",
            "resolution_type": ResolutionType.PROGRAM_ACTION,
            "resolution_date": "2020-02-02 00:00",
            "resolution_comment": "test comment"
        }
        response = self.post(force_params=params)
        assert response.status_code == HTTP_200_OK
        response_data = response.json()
        assert response_data["__action__"]["can_confirm"] is True
        assert response_data["__action__"]["reason"] is None
        assert response_data["__action__"]["next_group"]["id"] == soon.pk
        assert response_data["__action__"]["next_state"] == RecordState.PENDING_ANSWER
        assert response_data["__action__"]["different_ambit"] is False

    def test_plan_workflow_check_noderivation(self):
        record_card = self.create_record_card(RecordState.IN_RESOLUTION, process_pk=Process.PLANING_RESOLUTION_RESPONSE,
                                              requires_appointment=False)
        self.set_group_permissions("user_id", record_card.responsible_profile, [RECARD_PLAN_RESOL])

        workflow = Workflow.objects.create(main_record_card=record_card, state_id=RecordState.IN_RESOLUTION)
        record_card.workflow = workflow
        record_card.save()

        params = {
            "id": workflow.pk,
            "service_person_incharge": "test",
            "resolution_type": ResolutionType.PROGRAM_ACTION,
            "resolution_date": "2020-02-02 00:00",
            "resolution_comment": "test comment"
        }
        response = self.post(force_params=params)
        assert response.status_code == HTTP_200_OK
        response_data = response.json()
        assert response_data["__action__"]["can_confirm"] is True
        assert response_data["__action__"]["reason"] is None
        assert response_data["__action__"]["next_group"]["id"] == record_card.responsible_profile_id
        assert response_data["__action__"]["next_state"] == RecordState.PENDING_ANSWER
        assert response_data["__action__"]["different_ambit"] is False


class TestWorkflowAnswer(RecordCardActionsMixin, BaseOpenAPITest):
    path = "/record_cards/workflow/{id}/answer/"

    def test_workflow_answer(self):
        record_card = self.create_record_card(RecordState.PENDING_ANSWER, create_record_card_response=True,
                                              process_pk=Process.PLANING_RESOLUTION_RESPONSE)
        self.set_group_permissions("22222", record_card.responsible_profile, [RECARD_ANSWER])

        workflow = Workflow.objects.create(main_record_card=record_card, state_id=RecordState.PENDING_ANSWER)
        record_card.workflow = workflow
        record_card.save()
        response = self.post(force_params={"id": workflow.pk, "record_card": record_card.pk, "response": "response",
                                           "send_date": timezone.now().strftime("%Y-%m-%d"), "worked": "t"})

        assert response.status_code == HTTP_204_NO_CONTENT
        record_card = RecordCard.objects.get(pk=record_card.pk)
        assert record_card.record_state_id == RecordState.CLOSED
        assert record_card.closing_date
        assert record_card.workflow.state_id == RecordState.CLOSED
        assert record_card.workflow.close_date
        assert record_card.recordcardaudit.close_user

    def get_body_parameters(self, path_spec, force_params):
        return [force_params]

    @pytest.mark.parametrize("has_permissions,expected_response", (
        (True, HTTP_204_NO_CONTENT),
        (False, HTTP_403_FORBIDDEN),
    ))
    def test_permissions(self, has_permissions, expected_response):
        record_card = self.create_record_card(RecordState.PENDING_ANSWER, create_record_card_response=True,
                                              process_pk=Process.PLANING_RESOLUTION_RESPONSE)
        if has_permissions:
            self.set_group_permissions("22222", record_card.responsible_profile, [RECARD_ANSWER])
        workflow = Workflow.objects.create(main_record_card=record_card, state_id=RecordState.PENDING_ANSWER)
        record_card.workflow = workflow
        record_card.save()
        response = self.post(force_params={"id": workflow.pk, "record_card": record_card.pk, "response": "response",
                                           "send_date": timezone.now().strftime("%Y-%m-%d"), "worked": "t"})
        assert response.status_code == expected_response


class TestApplicantLastRecordsList(OpenAPIResourceListMixin, CreateRecordCardMixin, BaseOpenAPITest):
    path = "/record_cards/applicant-last-records/{id}/"
    base_api_path = "/services/iris/api"
    applicant = None

    @pytest.mark.parametrize("object_number", (0, 1, 5))
    def test_list(self, object_number):
        citizen = mommy.make(Citizen, user_id="22222")
        self.applicant = mommy.make(Applicant, user_id="2222", citizen=citizen)
        [self.given_an_object() for obj in range(0, object_number)]
        response = self.list(force_params={"page_size": self.paginate_by})
        self.should_return_list(object_number, self.paginate_by, response)

    def given_an_object(self):
        return self.create_record_card(applicant=self.applicant)

    def prepare_path(self, path, path_spec, force_params=None):
        """
        :param path: Relative URI of the operation.
        :param path_spec: OpenAPI spec as dict for part.
        :param force_params: Explicitly force params.
        :return: Path for performing a request to the given OpenAPI path.
        """
        path = path.format(id=self.applicant.pk)
        return "{}{}".format(self.base_api_path, path)


class TestInternalOperator(OpenAPIResourceExcelExportMixin, SoftDeleteCheckMixin, SetPermissionMixin,
                           SetUserGroupMixin, AdminUserMixin, BaseOpenAPIResourceTest):
    path = "/record_cards/internal-operators/"
    base_api_path = "/services/iris/api"
    deleted_model_class = InternalOperator
    permission_codename = ADMIN_GROUP

    def get_default_data(self):
        return {
            "document": str(uuid.uuid4())[:15],
            "applicant_type_id": ApplicantType.CIUTADA,
            "input_channel_id": InputChannel.RECLAMACIO_INTERNA,
        }

    def given_create_rq_data(self):
        return {
            "document": str(uuid.uuid4())[:15],
            "applicant_type_id": ApplicantType.CIUTADA,
            "input_channel_id": InputChannel.RECLAMACIO_INTERNA,
        }

    def when_data_is_invalid(self, data):
        data["document"] = ""


class TestSetRecordCardAuditsView(PostOperationMixin, BaseOpenAPITest):
    path = "/record_cards/set-record-audits/"
    base_api_path = "/services/iris/api"

    def test_set_record_card_audit_view(self):
        with patch("record_cards.tasks.set_record_card_audits.delay") as mock_delay:
            response = self.post()
            assert response.status_code == HTTP_200_OK
            mock_delay.assert_called_once()
