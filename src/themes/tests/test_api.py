import pytest
import random
import uuid

from django.utils import timezone
from django.utils.functional import cached_property
from mock import patch, Mock
from model_mommy import mommy
from rest_framework import status

from features.models import Feature, ValuesType, Mask, Values
from iris_masters.models import Process, District, ResponseChannel, Application, RecordState, RecordType
from iris_masters.permissions import ADMIN
from main.open_api.tests.base import (BaseOpenAPIResourceTest, BaseOpenAPITest, OrderUpdateMixin,
                                      OpenAPIResourceListMixin, DictListGetMixin, SoftDeleteCheckMixin,
                                      RetrieveOperation, PostOperationMixin, BasePermissionsTest, ListUpdateMixin,
                                      PreparePathIDMixin)
from main.test.mixins import AdminUserMixin
from profiles.models import Group, UserGroup, Profile, Permission, ProfilePermissions, GroupProfiles, GroupsUserGroup
from profiles.tests.utils import create_groups
from record_cards.tests.utils import (CreateRecordCardMixin, SetRecordCardCreateThemeNoVisiblePermissonMixin,
                                      SetUserGroupMixin, SetPermissionMixin)
from themes.models import (Area, Element, ElementDetail, Keyword, ElementDetailFeature, ElementDetailResponseChannel,
                           DerivationDirect, DerivationDistrict, ThemeGroup, ElementDetailDeleteRegister, Zone)
from themes.tests.utils import CreateThemesMixin
from themes.actions.theme_tree import ThemeTreeBuilder
from communications.tests.utils import load_missing_data
from iris_masters.tests.utils import load_missing_data_process
from main.utils import get_user_traceability_id


class TestArea(SoftDeleteCheckMixin, AdminUserMixin, SetPermissionMixin, SetUserGroupMixin, BaseOpenAPIResourceTest):
    path = "/theme/areas/"
    base_api_path = "/services/iris/api"
    deleted_model_class = Area
    model_class = Area
    delete_previous_objects = True

    def given_create_rq_data(self):
        return {
            "area_code": "AREACODE",
            "description_es": "test_es",
            "description_en": "test_en",
            "description_ca": "test_ca",
            "favourite": True
        }

    def when_data_is_invalid(self, data):
        data["description_es"] = ""

    def get_default_data(self):
        return {
            "description_en": uuid.uuid4(),
            "description_es": uuid.uuid4(),
            "description_ca": uuid.uuid4(),
            "area_code": str(uuid.uuid4())[:12],
            "order": 1,
            "favourite": False
        }


class TestAreaAutoComplete(OpenAPIResourceListMixin, CreateThemesMixin, BaseOpenAPITest):
    path = "/theme/areas/autocomplete/"
    base_api_path = "/services/iris/api"
    model_class = Area
    delete_previous_objects = True

    def given_an_object(self):
        load_missing_data()
        load_missing_data_process()
        return self.create_element_detail()


class TestElement(SoftDeleteCheckMixin, AdminUserMixin, CreateThemesMixin, SetUserGroupMixin, SetPermissionMixin,
                  BaseOpenAPIResourceTest):
    path = "/theme/elements/"
    base_api_path = "/services/iris/api"
    deleted_model_class = Element
    model_class = Element
    delete_previous_objects = True

    @cached_property
    def area(self):
        return self.create_area()

    def given_create_rq_data(self):
        return {
            "description_es": "test",
            "description_en": "test",
            "description_ca": "test",
            "element_code": "ELEMENTCODE",
            "area_id": self.area.pk,
            "order": 1,
            "is_favorite": True
        }

    def when_data_is_invalid(self, data):
        data["description_es"] = ""

    def get_default_data(self):
        return {
            "description_es": uuid.uuid4(),
            "description_en": uuid.uuid4(),
            "description_ca": uuid.uuid4(),
            "element_code": str(uuid.uuid4())[:20],
            "area_id": self.area.pk,
            "order": 1,
            "is_favorite": False
        }


class TestElementAutoComplete(OpenAPIResourceListMixin, CreateThemesMixin, BaseOpenAPITest):
    path = "/theme/elements/autocomplete/"
    base_api_path = "/services/iris/api"
    model_class = Element
    delete_previous_objects = True

    def given_an_object(self):
        load_missing_data()
        load_missing_data_process()
        return self.create_element_detail()


class TestElementDetailViewSet(SoftDeleteCheckMixin, CreateThemesMixin, AdminUserMixin, SetUserGroupMixin,
                               SetPermissionMixin, BaseOpenAPIResourceTest):
    path = "/theme/details/"
    base_api_path = "/services/iris/api"
    deleted_model_class = ElementDetail

    @pytest.mark.parametrize("object_number", (0, 1, 3))
    def test_list(self, object_number):
        ElementDetail.objects.all().delete()
        [self.given_an_object() for _ in range(0, object_number)]
        response = self.list(force_params={"page_size": self.paginate_by})
        self.should_return_list(object_number, self.paginate_by, response)
        for element_detail in response.data:
            assert "features" not in element_detail

    def test_create_valid(self):
        rq_data = self.given_create_rq_data()
        self.when_is_authenticated()
        with patch("themes.tasks.register_theme_ambits.delay") as mock_delay:
            response = self.create(rq_data)
            assert response.status_code == status.HTTP_201_CREATED
            self.should_create_object(response, rq_data)
            mock_delay.assert_called_once()

    def test_update_put(self):
        obj = self.given_an_object()
        obj.update({self.path_pk_param_name: obj["id"]})
        rq_data = self.given_a_complete_update(obj)
        with patch("themes.tasks.register_theme_ambits.delay") as mock_delay:
            response = self.put(force_params=rq_data)
            assert response.status_code == status.HTTP_200_OK
            self.should_complete_update(response, obj)
            mock_delay.assert_called_once()

    def test_update_patch(self):
        obj = self.given_an_object()
        obj.update({self.path_pk_param_name: obj["id"]})
        rq_data = self.given_a_partial_update(obj)
        with patch("themes.tasks.register_theme_ambits.delay") as mock_delay:
            response = self.patch(force_params=rq_data)
            assert response.status_code == status.HTTP_200_OK
            self.should_partial_update(response, obj)
            mock_delay.assert_called_once()

    @cached_property
    def element(self):
        return self.create_element()

    def given_create_rq_data(self):
        return {
            "description_ca": "Description CA!",
            "description_es": "Description ES!",
            "description_en": "Description EN!",
            "element_id": self.element.pk,
            "process": mommy.make(Process, id=Process.CLOSED_DIRECTLY).pk,
            "direct_derivations": [{
                "group": mommy.make(Group, user_id="222", profile_ctrl_user_id="322").pk,
                "record_state": RecordState.PENDING_VALIDATE
            }],
            "record_type_id": mommy.make(RecordType, user_id="22222").pk,
            "allow_english_lang": False
        }

    def get_default_data(self):
        return {
            "description_ca": uuid.uuid4(),
            "description_es": uuid.uuid4(),
            "description_en": uuid.uuid4(),
            "element_id": self.element.pk,
            "order": 1,
            "process": mommy.make(Process, id=Process.CLOSED_DIRECTLY).pk,
            "polygon_derivations": [{
                "polygon_code": "070",
                "zone": Zone.CARRCENT_PK,
                "group": mommy.make(Group, user_id="222", profile_ctrl_user_id="222").pk
            }],
            "record_type_id": mommy.make(RecordType, user_id="22222").pk,
            "allow_english_lang": True
        }

    def when_data_is_invalid(self, data):
        data["description_ca"] = ""
        data["external_protocol_id"] = ""
        data["process"] = None

    @pytest.mark.parametrize("keywords_list,keywords_filter,elements_expected", (
            ([["test", "test2", "test3"], ["test", "test2"]], "test,test2", 2),
            ([["test", "test2", "test3"], ["test", "test2"]], "test,test2,test4", 2),
            ([["test", "test2", "test3"], ["test", "test2"]], "test", 2),
            ([["test", "test2", "test3"], ["test", "test2"]], "test3", 1),
            ([["test", "test2", "test3"], ["test", "test2"]], "Test,test2", 2),
            ([["test", "test2", "test3"], ["test", "test2"]], "test,TEST2,test4", 2),
            ([["test", "test2", "test3"], ["test", "test2"]], "TEST", 2),
            ([["test", "test2", "test3"], ["test", "test2"]], "teSt3", 1),
    ))
    def test_keywords_filter(self, keywords_list, keywords_filter, elements_expected):
        for keywords in keywords_list:
            self.create_element_detail_with_keywords(keywords)

        find_details_element_description = Mock(return_value=[])
        with patch("themes.actions.theme_keywords_search.KeywordSearch.find_details_element_description",
                   find_details_element_description):
            response = self.list(force_params={"page_size": self.paginate_by,
                                               "keywords": keywords_filter})
        self.should_return_list(elements_expected, self.paginate_by, response)

    def create_element_detail_with_keywords(self, keywords):
        element_detail = self.create_element_detail()
        for keyword_text in keywords:
            mommy.make(Keyword, description=keyword_text, detail=element_detail, user_id="222")

    @pytest.mark.parametrize("record_state,expected_response", (
            (RecordState.PENDING_VALIDATE, status.HTTP_400_BAD_REQUEST),
            (RecordState.IN_PLANING, status.HTTP_201_CREATED),
    ))
    def test_create_combined_derivations(self, record_state, expected_response):
        rq_data = self.given_create_rq_data()
        self.add_district_derivations(rq_data, record_state=record_state)
        self.when_is_authenticated()
        response = self.create(rq_data)
        assert response.status_code == expected_response
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            self.should_be_invalid(response, rq_data)

    @staticmethod
    def add_district_derivations(data, delete_profile_derivations=False, record_state=None):
        if delete_profile_derivations:
            data["direct_derivations"] = []
        group_pk = mommy.make(Group, user_id="222", profile_ctrl_user_id="322").pk
        data["district_derivations"] = []
        data["requires_ubication_district"] = True
        for district in District.objects.filter(allow_derivation=True):
            data["district_derivations"].append({
                "group": group_pk,
                "district": district.pk,
                "record_state": record_state if record_state else RecordState.PENDING_VALIDATE
            })

    def given_a_partial_update(self, obj):
        """
        :param obj: Object that will be updated.
        :return: Dictionary with attrs for creating a partial update on a given obj
        """
        obj["response_channels"] = [{"responsechannel": ResponseChannel.EMAIL}]
        feature = mommy.make(Feature, user_id="22222")
        obj["features"] = [{"feature": feature.pk, "is_mandatory": True, "order": 2}]
        theme_group = mommy.make(ThemeGroup, user_id="222")
        obj["theme_groups"] = [{"theme_group": theme_group.pk}]
        obj["active"] = False
        obj["active_date"] = timezone.now().date()
        obj["visible"] = True
        obj["visible_date"] = timezone.now().date()
        obj["pend_commmunications"] = False
        return obj

    def given_a_complete_update(self, obj):
        """
        :param obj: Object that will be updated.
        :return: Dictionary with attrs for creating a partial update on a given obj
        """
        obj["response_channels"] = [{"responsechannel": ResponseChannel.SMS},
                                    {"responsechannel": ResponseChannel.TELEPHONE}]
        feature = mommy.make(Feature, user_id="22222")
        obj["features"] = [{"feature": feature.pk, "is_mandatory": True, "order": 1}]
        theme_group = mommy.make(ThemeGroup, user_id="222")
        obj["theme_groups"] = [{"theme_group": theme_group.pk}]
        obj["active"] = True
        obj["active_date"] = timezone.now().date()
        obj["visible"] = False
        obj["visible_date"] = timezone.now().date()
        obj["pend_commmunications"] = True
        return obj

    def test_create_district_derivations(self):
        rq_data = self.given_create_rq_data()
        self.add_district_derivations(rq_data, delete_profile_derivations=True)
        self.when_is_authenticated()
        response = self.create(rq_data)
        assert response.status_code == status.HTTP_201_CREATED
        self.should_create_object(response, rq_data)

    def test_update_put_district_derivations(self):
        obj = self.given_an_object()
        obj.update({self.path_pk_param_name: obj["id"]})
        rq_data = self.given_a_complete_update(obj)
        self.add_district_derivations(rq_data, delete_profile_derivations=True)
        response = self.put(force_params=rq_data)
        assert response.status_code == status.HTTP_200_OK
        self.should_complete_update(response, obj)

    def test_create_requires_process(self):
        resp = self.create(force_params={})
        assert "process" in resp.data, "Create should require process"
        resp = self.create(force_params={"process": None})
        assert "process" in resp.data, "Create should require process"

    def test_element_detail_response_channels(self):
        element_detail = self.create_element_detail(add_response_channels=False)
        ElementDetailResponseChannel.objects.create(elementdetail=element_detail,
                                                    responsechannel_id=ResponseChannel.EMAIL)
        ElementDetailResponseChannel.objects.create(elementdetail=element_detail, application_id=Application.ATE_PK,
                                                    responsechannel_id=ResponseChannel.EMAIL)
        element_detail_dict = self.retrieve(force_params={"id": element_detail.pk}).json()
        element_detail_dict["element_id"] = element_detail.element_id
        assert len(element_detail_dict["response_channels"]) == 1
        element_detail_dict["response_channels"] = [{"responsechannel": ResponseChannel.SMS},
                                                    {"responsechannel": ResponseChannel.TELEPHONE}]
        response = self.put(force_params=element_detail_dict)
        assert response.status_code == status.HTTP_200_OK
        assert len(element_detail_dict["response_channels"]) == 2
        assert ElementDetailResponseChannel.objects.filter(
            elementdetail=element_detail, enabled=True, application_id=Application.IRIS_PK).count() == 2
        assert ElementDetailResponseChannel.objects.filter(
            elementdetail=element_detail, application_id=Application.IRIS_PK).count() == 3

    def test_element_detail_enabled_keywords(self):
        rq_data = self.given_create_rq_data()
        rq_data["keywords"] = ["KEYWORD1", "KEYWORD2", "KEYWORD3"]
        self.when_is_authenticated()
        response = self.create(rq_data)
        assert response.status_code == status.HTTP_201_CREATED
        self.should_create_object(response, rq_data)
        element_detail_dict = response.json()
        assert Keyword.objects.filter(detail_id=element_detail_dict["id"], enabled=True).count() == 3
        element_detail_dict["keywords"] = ["KEYWORD1", "KEYWORD3", "KEYWORD4"]
        self.put(force_params=element_detail_dict)
        assert Keyword.objects.filter(detail_id=element_detail_dict["id"], enabled=True).count() == 3
        assert Keyword.objects.filter(detail_id=element_detail_dict["id"]).count() == 4

    def test_element_detail_enabled_direct_derivations(self):
        element_detail = self.create_element_detail(external_protocol_id="22222", requires_ubication_district=True)
        group = mommy.make(Group, user_id="222", profile_ctrl_user_id="322")
        DerivationDirect.objects.create(element_detail=element_detail, group=group,
                                        record_state_id=RecordState.PENDING_VALIDATE)

        element_detail_dict = self.retrieve(force_params={"id": element_detail.pk}).json()
        element_detail_dict["element_id"] = element_detail.element.pk
        assert DerivationDirect.objects.filter(element_detail_id=element_detail_dict["id"], enabled=True).count() == 1
        element_detail_dict["direct_derivations"][0]["group"] = mommy.make(Group, user_id="222",
                                                                           profile_ctrl_user_id="322").pk
        self.put(force_params=element_detail_dict)
        assert DerivationDirect.objects.filter(element_detail_id=element_detail_dict["id"], enabled=True).count() == 1
        assert DerivationDirect.objects.filter(element_detail_id=element_detail_dict["id"]).count() == 2

    @pytest.mark.parametrize("requires_ubication_district,expected_response", (
            (True, status.HTTP_200_OK),
            (False, status.HTTP_400_BAD_REQUEST),
    ))
    def test_element_detail_enabled_district_derivations(self, requires_ubication_district, expected_response):
        element_detail = self.create_element_detail(external_protocol_id="22222",
                                                    requires_ubication_district=requires_ubication_district)
        group = mommy.make(Group, user_id="222", profile_ctrl_user_id="322")

        districts = District.objects.filter(allow_derivation=True)
        for district in districts:
            DerivationDistrict.objects.create(element_detail=element_detail, group=group, district=district,
                                              record_state_id=RecordState.PENDING_VALIDATE)

        element_detail_dict = self.retrieve(force_params={"id": element_detail.pk}).json()
        element_detail_dict["element_id"] = element_detail.element.pk
        assert DerivationDistrict.objects.filter(
            element_detail_id=element_detail_dict["id"], enabled=True).count() == len(districts)
        element_detail_dict["district_derivations"][5]["group"] = mommy.make(
            Group, user_id="222", profile_ctrl_user_id="322").pk
        response = self.put(force_params=element_detail_dict)
        assert response.status_code == expected_response
        if expected_response == status.HTTP_200_OK:
            assert DerivationDistrict.objects.filter(
                element_detail_id=element_detail_dict["id"], enabled=True).count() == len(districts)
            assert DerivationDistrict.objects.filter(
                element_detail_id=element_detail_dict["id"]).count() == len(districts) + 1

    @pytest.mark.parametrize("active,fill_active_mandatory_fields,expected_active", (
            (True, False, True),  # Since Mandatory == Active Mandatory
            (True, True, True),
            (False, False, False),
            (False, True, False),
    ))
    def test_active_mandatory_fields(self, active, fill_active_mandatory_fields, expected_active):

        element_detail = self.create_element_detail(active=active,
                                                    fill_active_mandatory_fields=fill_active_mandatory_fields)
        response = self.retrieve(force_params={"id": element_detail.pk})
        element_detail_data = response.json()
        response = self.put(force_params=element_detail_data)
        assert response.status_code == status.HTTP_200_OK
        element_detail = ElementDetail.objects.get(pk=element_detail.pk)
        assert element_detail.active is expected_active

    @pytest.mark.parametrize("add_response_channels", (True, False))
    def test_active_mandatory_relationships(self, add_response_channels):
        element_detail = self.create_element_detail(active=False,
                                                    fill_active_mandatory_fields=True,
                                                    add_response_channels=add_response_channels)
        response = self.retrieve(force_params={"id": element_detail.pk})
        element_detail_data = response.json()
        element_detail_data["active"] = True
        response = self.put(force_params=element_detail_data)
        assert response.status_code == status.HTTP_200_OK
        assert ElementDetail.objects.get(pk=element_detail.pk).active is add_response_channels

    @pytest.mark.parametrize("groups_number", (0, 1, 10))
    def test_element_detail_group_profiles(self, groups_number):
        element_detail = self.create_element_detail()
        element_detail_dict = self.retrieve(force_params={"id": element_detail.pk}).json()
        groups = []
        for _ in range(groups_number):
            group = mommy.make(Group, user_id="222", profile_ctrl_user_id="2222")
            groups.append({"group": group.pk})

        element_detail_dict.update({"group_profiles": groups})
        response = self.put(force_params=element_detail_dict)
        assert response.status_code == status.HTTP_200_OK
        element_detail = ElementDetail.objects.get(pk=element_detail.pk)
        assert element_detail.groupprofileelementdetail_set.filter(enabled=True).count() == groups_number


class TestElementDetailAutoComplete(OpenAPIResourceListMixin, CreateThemesMixin, BaseOpenAPITest):
    path = "/theme/details/autocomplete/"
    base_api_path = "/services/iris/api"
    model_class = ElementDetail
    delete_previous_objects = True

    def given_an_object(self):
        return self.create_element_detail()


class TestElementDetailSearchView(CreateThemesMixin, OpenAPIResourceListMixin, SetUserGroupMixin,
                                  SetRecordCardCreateThemeNoVisiblePermissonMixin, BaseOpenAPITest):
    path = "/theme/details/search/"
    base_api_path = "/services/iris/api"

    def given_an_object(self, obj=None):
        if obj:
            visible = True if obj % 2 == 0 else False
            set_future_visible_date = True if obj % 3 == 0 else False
        else:
            visible = True
            set_future_visible_date = False
        return self.create_element_detail(active=True, visible=visible, fill_active_mandatory_fields=visible,
                                          set_future_visible_date=set_future_visible_date)

    @pytest.mark.parametrize("theme_novisible_permission,object_number,expected_objects", (
            (False, 0, 0),
            (False, 1, 1),
            (False, 2, 1),
            (False, 3, 2),
            (False, 7, 3),
            (False, 10, 4),
            (False, 15, 6),
            (True, 0, 0),
            (True, 1, 1),
            (True, 7, 7),
    ))
    def test_visible(self, theme_novisible_permission, object_number, expected_objects):
        if theme_novisible_permission:
            self.set_usergroup()
            self.set_recard_create_themenovisible_permission(self.user.usergroup.group)

        [self.given_an_object(obj) for obj in range(0, object_number)]
        response = self.list(force_params={"page_size": self.paginate_by})
        self.should_return_list(expected_objects, self.paginate_by, response)


class TestElementDetailCheckView(CreateThemesMixin, RetrieveOperation, PostOperationMixin, AdminUserMixin,
                                 BaseOpenAPITest):
    detail_path = "/theme/details/{id}/"
    path = "/theme/details/{id}/check/"
    base_api_path = "/services/iris/api"

    @pytest.mark.parametrize("active,fill_active_mandatory_fields,mandatory_fields_missing,will_be_active", (
            (True, False, True, True),  # Since active mandatory and mandatory al the same, the result will be true
            (True, True, False, True),
            (False, False, True, False),  # Since active mandatory and mandatory al the same, the result will be true
            (False, True, False, False),
    ))
    def test_element_detail_check(self, active, fill_active_mandatory_fields, mandatory_fields_missing, will_be_active):
        element_detail = self.create_element_detail(active=active,
                                                    fill_active_mandatory_fields=fill_active_mandatory_fields)
        response = self.retrieve(force_params={"id": element_detail.pk})
        response = self.post(force_params=response.json())
        assert response.status_code == status.HTTP_200_OK
        chech_data_response = response.json()
        assert chech_data_response["can_save"] is True
        assert chech_data_response["will_be_active"] is will_be_active

    @pytest.mark.parametrize("add_response_channels", (True, False))
    def test_active_mandatory_relationships(self, add_response_channels):
        element_detail = self.create_element_detail(active=False,
                                                    fill_active_mandatory_fields=True,
                                                    add_response_channels=add_response_channels)
        response = self.retrieve(force_params={"id": element_detail.pk})
        response = self.post(force_params=response.json())
        assert response.status_code == status.HTTP_200_OK
        chech_data_response = response.json()
        assert chech_data_response["can_save"] is True
        assert chech_data_response["will_be_active"] is False


class TestElementDetailAmbitTaskView(DictListGetMixin, CreateThemesMixin, BaseOpenAPITest):
    path = "/theme/details/ambit-task/"
    base_api_path = "/services/iris/api"

    @pytest.mark.parametrize("object_number", (0, 1, 3))
    def test_ambit_task(self, object_number):
        ElementDetail.objects.all().delete()
        [self.create_element_detail(create_direct_derivations=True, create_district_derivations=True)
         for _ in range(object_number)]

        with patch("themes.actions.theme_set_ambits.register_theme_ambits.delay") as mock_delay:
            response = self.dict_list_retrieve()
            assert response.status_code == status.HTTP_200_OK
            assert mock_delay.call_count == object_number
            if object_number > 0:
                mock_delay.assert_called()


class TestElementDetailChangeList(CreateRecordCardMixin, OpenAPIResourceListMixin, SetUserGroupMixin, BaseOpenAPITest):
    path = "/theme/details/change/{id}/"
    base_api_path = "/services/iris/api"

    @pytest.mark.parametrize("group,record_state,validated_reassignable,previous_created_at,expected_themes", (
            (1, RecordState.PENDING_VALIDATE, False, False, 4),
            (2, RecordState.PENDING_VALIDATE, False, False, 4),
            (3, RecordState.PENDING_VALIDATE, False, False, 4),
            (3, RecordState.IN_RESOLUTION, False, False, 1),
            (2, RecordState.PENDING_VALIDATE, False, True, 1),
            (2, RecordState.IN_RESOLUTION, True, True, 1),
    ))
    def test_list(self, group, record_state, validated_reassignable, previous_created_at, expected_themes):
        ElementDetail.objects.all().delete()
        for _ in range(3):
            self.create_element_detail(validated_reassignable=validated_reassignable)

        element_detail = self.create_element_detail(validated_reassignable=validated_reassignable,
                                                    create_direct_derivations=True,
                                                    create_district_derivations=True)
        element_detail.register_theme_ambit()

        self.set_usergroup(group=Group.objects.get(pk=group))
        self.record_card = self.create_record_card(record_state_id=record_state,
                                                   responsible_profile=Group.objects.get(pk=3),
                                                   element_detail=element_detail,
                                                   previous_created_at=previous_created_at)

        response = self.list()
        assert response.status_code == status.HTTP_200_OK
        self.should_return_list(expected_themes, None, response)

    def prepare_path(self, path, path_spec, force_params=None):
        """
        :param path: Relative URI of the operation.
        :param path_spec: OpenAPI spec as dict for part.
        :param force_params: Explicitly force params.
        :return: Path for performing a request to the given OpenAPI path.
        """
        return "{}{}".format(self.base_api_path, path.format(id=self.record_card.pk))


class TestThemeGroup(SoftDeleteCheckMixin, AdminUserMixin, SetPermissionMixin, SetUserGroupMixin,
                     BaseOpenAPIResourceTest):
    path = "/theme/theme_groups/"
    base_api_path = "/services/iris/api"
    deleted_model_class = ThemeGroup
    object_pk_not_exists = 100000

    def get_default_data(self):
        return {
            "description": uuid.uuid4(),
            "position": random.randrange(0, 1000),
        }

    def given_create_rq_data(self):
        return {
            "description": uuid.uuid4(),
            "position": random.randrange(0, 1000),
        }

    def when_data_is_invalid(self, data):
        data["description"] = ""


class TestElementDetailBulkActiveView(ListUpdateMixin, AdminUserMixin, CreateThemesMixin, BaseOpenAPITest):
    path = "/theme/details/active/"
    base_api_path = "/services/iris/api"

    @pytest.mark.parametrize("object_number,add_errors,expected_response", (
            (0, False, status.HTTP_204_NO_CONTENT),
            (1, False, status.HTTP_204_NO_CONTENT),
            (10, False, status.HTTP_204_NO_CONTENT),
            (0, True, status.HTTP_204_NO_CONTENT),
            (1, True, status.HTTP_204_NO_CONTENT),
            (10, True, status.HTTP_204_NO_CONTENT)
    ))
    def test_list_update(self, object_number, add_errors, expected_response):
        rq_data = [self.given_an_object(add_errors) for _ in range(object_number)]
        response = self.list_update(force_params=rq_data)
        assert response.status_code == expected_response

    def prepare_path(self, path, path_spec, force_params=None):
        """
        :param path: Relative URI of the operation.
        :param path_spec: OpenAPI spec as dict for part.
        :param force_params: Explicitly force params.
        :return: Path for performing a request to the given OpenAPI path.
        """
        return "{}{}".format(self.base_api_path, path)

    def given_an_object(self, add_errors):
        if add_errors:
            element_detail = self.create_element_detail(active=False, fill_active_mandatory_fields=False)
        else:
            element_detail = self.create_element_detail(active=False)
        return {"id": element_detail.pk, "active": True, "activation_date": "2020-01-01"}


class TestElementDetailFeaturesList(OpenAPIResourceListMixin, CreateThemesMixin, PreparePathIDMixin, BaseOpenAPITest):
    path = "/theme/details/{id}/features/"
    base_api_path = "/services/iris/api"

    @pytest.mark.parametrize("object_number", (0, 1, 3))
    def test_list(self, object_number):
        element_detail = self.create_element_detail()
        [self.given_an_object(element_detail) for _ in range(0, object_number)]
        response = self.list(force_params={"page_size": self.paginate_by, "id": element_detail.pk})
        self.should_return_list(object_number, self.paginate_by, response)

    def given_an_object(self, element_detail):
        values_type = mommy.make(ValuesType, user_id="222")
        for _ in range(3):
            mommy.make(Values, user_id="222", values_type=values_type)
        mask = Mask.objects.first()
        feature = mommy.make(Feature, deleted=None, user_id="222", values_type=values_type, mask=mask)
        mommy.make(ElementDetailFeature, element_detail=element_detail, feature=feature, user_id="ssss")
        return feature


class TestAreaOrder(OrderUpdateMixin, CreateThemesMixin, AdminUserMixin, BaseOpenAPITest):
    path = "/theme/area/{id}/set-order/{position}/"
    base_api_path = "/services/iris/api"
    model_class = Area

    @pytest.mark.parametrize("new_order", (4, 58, 3))
    def test_order(self, new_order):
        object = self.given_an_object()
        response = self.order_update(force_params={"pk": object.pk, "position": new_order})
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert self.model_class.objects.get(pk=object.pk).order == new_order

    def prepare_path(self, path, path_spec, force_params=None):
        """
        :param path: Relative URI of the operation.
        :param path_spec: OpenAPI spec as dict for part.
        :param force_params: Explicitly force params.
        :return: Path for performing a request to the given OpenAPI path.
        """
        path = path.format(id=force_params["pk"], position=force_params["position"])
        return "{}{}".format(self.base_api_path, path)

    def given_an_object(self):
        return self.create_area()


class TestElementOrder(TestAreaOrder):
    path = "/theme/element/{id}/set-order/{position}/"
    model_class = Element

    def given_an_object(self):
        return self.create_element()


class TestElementDetailOrder(TestAreaOrder):
    path = "/theme/details/{id}/set-order/{position}/"
    model_class = ElementDetail

    def given_an_object(self):
        return self.create_element_detail()


class TestListGetThemesTreeView(DictListGetMixin, CreateThemesMixin, BaseOpenAPITest):
    path = "/theme/tree/"
    base_api_path = "/services/iris/api"

    def test_get_themes_tree(self):
        element_detail = self.create_element_detail()
        for _ in range(3):
            mommy.make(Keyword, detail=element_detail, user_id="222")
        builder = ThemeTreeBuilder()
        builder.clear_cache()
        response = self.dict_list_retrieve()
        assert response.status_code == status.HTTP_200_OK
        json_tree = response.json()
        builder.clear_cache()

        area_pk = str(element_detail.element.area_id)
        element_pk = str(element_detail.element_id)
        element_detail_pk = str(element_detail.pk)
        assert area_pk in json_tree
        assert element_pk in json_tree[area_pk]["elements"]
        assert element_detail_pk in json_tree[area_pk]["elements"][element_pk]["details"]
        for keyword in element_detail.keyword_set.all():
            assert keyword.description in json_tree[area_pk][
                "elements"][element_pk]["details"][element_detail_pk]["keywords"]


class TestThemesAdminPermissions(CreateThemesMixin, BasePermissionsTest):
    base_api_path = "/services/iris/api"

    cases = [
        {
            "detail_path": "/theme/theme_groups/{id}/",
            "model_class": ThemeGroup,
        },
        {
            "detail_path": "/theme/areas/{id}/",
            "model_class": Area,
        },
        {
            "detail_path": "/theme/elements/{id}/",
            "model_class": Element,
        },
        {
            "detail_path": "/theme/details/{id}/",
            "model_class": ElementDetail,
        }
    ]

    def given_an_object(self, model_class):
        if model_class == Element:
            return self.create_element()
        if model_class == ElementDetail:
            return self.create_element_detail()
        return mommy.make(model_class, user_id="2222")

    def set_admin_permission(self):
        if not hasattr(self.user, "usergroup"):
            group = mommy.make(Group, user_id="222", profile_ctrl_user_id="22222")
            user_group = UserGroup.objects.create(user=self.user, group=group)
            GroupsUserGroup.objects.create(user_group=user_group, group=group)
        else:
            group = self.user.usergroup.group
            GroupsUserGroup.objects.create(user_group=self.user.usergroup, group=group)
        profile = mommy.make(Profile, user_id="222")
        admin_permission = Permission.objects.get(codename=ADMIN)
        ProfilePermissions.objects.create(permission=admin_permission, profile=profile)
        GroupProfiles.objects.create(group=group, profile=profile)


class TestCreateElementDetailDeleteRegisterView(CreateThemesMixin, PostOperationMixin, SetUserGroupMixin,
                                                AdminUserMixin, BaseOpenAPITest):
    path = "/theme/details/delete/"
    base_api_path = "/services/iris/api"

    @pytest.mark.parametrize("add_deleted_detail,add_reasignation_detail,only_open,expected_response", (
            (True, True, False, status.HTTP_201_CREATED),
            (True, False, False, status.HTTP_400_BAD_REQUEST),
            (False, True, True, status.HTTP_400_BAD_REQUEST),
            (False, False, True, status.HTTP_400_BAD_REQUEST),
    ))
    def test_create_group_delete_register(self, add_deleted_detail, add_reasignation_detail, only_open,
                                          expected_response):
        dair, parent, soon, _, noambit_parent, _ = create_groups()
        self.set_usergroup(dair)

        data = {"only_open": only_open}
        element_detail = self.create_element_detail()
        if add_deleted_detail:
            data["deleted_detail_id"] = element_detail.pk
        if add_reasignation_detail:
            data["reasignation_detail_id"] = self.create_element_detail().pk

        with patch("themes.tasks.elementdetail_delete_action_execute.delay") as mock_delay:
            response = self.post(force_params=data)
            assert response.status_code == expected_response
            if expected_response == status.HTTP_201_CREATED:
                assert ElementDetail.all_objects.get(pk=element_detail.pk).deleted
                response_content = response.json()
                assert ElementDetailDeleteRegister.objects.get(pk=response_content["id"])
                mock_delay.assert_called_once()

    def test_same_detail(self):
        element_detail = self.create_element_detail()
        data = {
            "only_open": True,
            "deleted_detail_id": element_detail.pk,
            "reasignation_detail_id": element_detail.pk,
        }
        response = self.post(force_params=data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestElementDetailCopyView(CreateThemesMixin, PostOperationMixin, SetUserGroupMixin, AdminUserMixin,
                                PreparePathIDMixin, BaseOpenAPITest):
    path = "/theme/details/{id}/copy/"
    base_api_path = "/services/iris/api"

    @pytest.mark.parametrize("description_ca,description_en,description_es,expected_response", (
            ("description_ca", "description_en", "description_es", status.HTTP_201_CREATED),
            (None, "description_en", "description_es", status.HTTP_400_BAD_REQUEST),
            ("description_ca", None, "description_es", status.HTTP_400_BAD_REQUEST),
            ("description_ca", "description_en", None, status.HTTP_400_BAD_REQUEST),
    ))
    def test_detail_copy(self, description_ca, description_en, description_es, expected_response):
        related_objects = 3
        dair, _, _, _, _, _ = create_groups()
        self.set_usergroup(dair)
        prev_element_detail = self.create_element_detail()
        [mommy.make(Keyword, user_id="2322", detail=prev_element_detail) for _ in range(related_objects)]
        data = {
            "id": prev_element_detail.pk,
            "description_ca": description_ca,
            "description_en": description_en,
            "description_es": description_es
        }
        response = self.post(force_params=data)
        assert response.status_code == expected_response
        if expected_response == status.HTTP_201_CREATED:
            element_detail = ElementDetail.objects.get(pk=response.json()["id"])
            assert element_detail.user_id == get_user_traceability_id(self.user)
            assert element_detail.description_ca == description_ca
            assert element_detail.description_en == description_en
            assert element_detail.description_es == description_es
            assert element_detail.keyword_set.count() == related_objects
            assert prev_element_detail.keyword_set.count() == related_objects

    @pytest.mark.parametrize("valid_element_id, expected_response", (
            (True, status.HTTP_201_CREATED), (False, status.HTTP_400_BAD_REQUEST)
    ))
    def test_element_detail_copy_element(self, valid_element_id, expected_response):
        data = {"description_ca": "testtest", "description_en": "testtest", "description_es": "testtest",
                "id": self.create_element_detail().pk}
        if valid_element_id:
            data["element_id"] = self.create_element().pk
        else:
            data["element_id"] = 10
        response = self.post(force_params=data)
        assert response.status_code == expected_response
