import random
import uuid
from datetime import timedelta

import pytest
from django.utils import timezone
from model_mommy import mommy
from rest_framework import status
from rest_framework.status import HTTP_200_OK, HTTP_404_NOT_FOUND

from iris_masters.models import (Reason, Application, ResponseChannel, RecordType, Parameter, Support,
                                 ApplicantType, RecordState, InputChannel, MediaType, Process, District,
                                 CommunicationMedia, ResolutionType, Announcement, LetterTemplate)
from iris_masters.permissions import ADMIN, ANNOUNCEMENTS
from iris_masters.serializers import RecordTypeSerializer
from main.open_api.tests.base import (BaseOpenAPIResourceTest, OpenAPIResourceListMixin, BaseOpenAPITest,
                                      ListUpdateMixin, BaseOpenAPICRUResourceTest, SoftDeleteCheckMixin, PutOperation,
                                      BasePermissionsTest, OpenAPIResourceUpdateMixin, OpenAPIRetrieveMixin,
                                      OpenAPIResourceExcelExportMixin)
from main.test.mixins import AdminUserMixin
from profiles.models import Group, UserGroup, Profile, Permission, GroupProfiles, ProfilePermissions, GroupsUserGroup
from record_cards.tests.utils import SetPermissionMixin, SetUserGroupMixin
from themes.models import ElementDetail
from communications.tests.utils import load_missing_data


class TestReasonList(OpenAPIResourceListMixin, BaseOpenAPITest):
    path = "/masters/reasons/"
    base_api_path = "/services/iris/api"

    model_class = Reason
    deleted_model_class = Reason
    delete_previous_objects = True
    soft_delete = True

    def given_an_object(self):
        return mommy.make(Reason, user_id="222")


class TestCancelReason(SoftDeleteCheckMixin, SetUserGroupMixin, SetPermissionMixin, AdminUserMixin,
                       BaseOpenAPIResourceTest):
    path = "/masters/cancel-reasons/"
    base_api_path = "/services/iris/api"
    object_pk_not_exists = -1

    model_class = Reason
    deleted_model_class = Reason
    delete_previous_objects = True
    soft_delete = True

    def get_default_data(self):
        return {
            "description": uuid.uuid4(),
            "reason_type": Reason.TYPE_1
        }

    def given_create_rq_data(self):
        """
        :return: Default request data.
        """
        return {
            "description": uuid.uuid4(),
            "reason_type": Reason.TYPE_1
        }

    def when_data_is_invalid(self, data):
        data["description"] = ""


class TestReasignReason(TestCancelReason):
    path = "/masters/reasign-reasons/"

    def get_default_data(self):
        return {
            "description": uuid.uuid4(),
            "reason_type": Reason.TYPE_2
        }

    def given_create_rq_data(self):
        """
        :return: Default request data.
        """
        return {
            "description": uuid.uuid4(),
            "reason_type": Reason.TYPE_2
        }


class TestMediaType(BaseOpenAPIResourceTest):
    path = "/masters/media_types/"
    base_api_path = "/services/iris/api"

    def get_default_data(self):
        return {
            "user_id": str(uuid.uuid4())[:20],
            "description_en": uuid.uuid4(),
            "description_es": uuid.uuid4(),
            "description_ca": uuid.uuid4(),
            "enabled": True
        }

    def given_create_rq_data(self):
        return {
            "user_id": str(uuid.uuid4())[:20],
            "description_en": "test",
            "description_es": "test",
            "description_ca": "test",
            "enabled": True
        }

    def when_data_is_invalid(self, data):
        data["description_es"] = ""


class TestCommunicationMedia(SoftDeleteCheckMixin, AdminUserMixin, SetPermissionMixin, SetUserGroupMixin,
                             BaseOpenAPIResourceTest):
    path = "/masters/communication_medias/"
    base_api_path = "/services/iris/api"
    deleted_model_class = CommunicationMedia

    def get_default_data(self):
        return {
            "description": uuid.uuid4(),
            "media_type_id": mommy.make(MediaType, user_id="222").pk,
        }

    def given_create_rq_data(self):
        return {
            "description": "test",
            "media_type_id": mommy.make(MediaType, user_id="222").pk,
        }

    def when_data_is_invalid(self, data):
        data["description"] = ""


class TestResponseChannelList(OpenAPIResourceListMixin, BaseOpenAPITest):
    path = "/masters/response_channels/"
    base_api_path = "/services/iris/api"

    model_class = ResponseChannel
    delete_previous_objects = True
    object_tuples = ResponseChannel.RESPONSE_TYPES
    paginate_by = len(ResponseChannel.RESPONSE_TYPES)

    def given_an_object(self):
        return mommy.make(ResponseChannel, user_id="222")


class TestRecordTypeListUpdateViewSet(OpenAPIResourceListMixin, OpenAPIRetrieveMixin, OpenAPIResourceUpdateMixin,
                                      BaseOpenAPITest):
    path = "/masters/record_types/"
    detail_path = "/masters/record_types/{id}/"
    base_api_path = "/services/iris/api"

    def given_an_object(self):
        record_type = mommy.make(RecordType, user_id="222", description=str(uuid.uuid4()),
                                 description_es=str(uuid.uuid4()), description_ca=str(uuid.uuid4()),
                                 description_en=str(uuid.uuid4()))
        return RecordTypeSerializer(instance=record_type).data

    def given_a_partial_update(self, obj):
        """
        :param obj: Object that will be updated.
        :return: Dictionary with attrs for creating a partial update on a given obj
        """
        obj["tri"] = 100
        return obj

    def given_a_complete_update(self, obj):
        """
        :param obj: Object that will be updated.
        :return: Dictionary with attrs for creating a partial update on a given obj
        """
        obj["trt"] = 100
        return obj


class TestRecordStateList(OpenAPIResourceListMixin, BaseOpenAPITest):
    path = "/masters/record_states/"
    base_api_path = "/services/iris/api"

    model_class = RecordState
    delete_previous_objects = True
    object_tuples = RecordState.STATES
    paginate_by = len(RecordState.STATES)

    def given_an_object(self):
        return mommy.make(RecordState, user_id="2222", id=RecordState.PENDING_VALIDATE)


class TestParameterList(OpenAPIResourceExcelExportMixin, OpenAPIResourceListMixin, SetPermissionMixin,
                        SetUserGroupMixin, BaseOpenAPITest):
    path = "/masters/parameters/"
    base_api_path = "/services/iris/api"

    model_class = Parameter
    delete_previous_objects = True

    def given_an_object(self):
        return mommy.make(Parameter, user_id="222", show=True)


class TestParameterListVisible(OpenAPIResourceListMixin, BaseOpenAPITest):
    path = "/masters/parameters/visible/"
    base_api_path = "/services/iris/api"

    paginate_by = 5

    def given_an_object(self, visible):
        return mommy.make(Parameter, user_id="222", show=True, visible=visible)

    @pytest.mark.parametrize("visibles_list,visibles_num", (
            ([False, False, False, False, False], 0),
            ([False, False, True, False, False], 1),
            ([True, False, True, False, False], 2),
            ([True, False, True, False, True], 3),
            ([True, True, True, False, True], 4),
            ([True, True, True, True, True], 5),
    ))
    def test_list(self, visibles_list, visibles_num):
        Parameter.objects.all().delete()
        [self.given_an_object(visible) for visible in visibles_list]
        response = self.list(force_params={"page_size": self.paginate_by})
        self.should_return_list(visibles_num, self.paginate_by, response)


class TestParameterListUpdate(ListUpdateMixin, AdminUserMixin, BaseOpenAPITest):
    path = "/masters/parameters/update/"
    base_api_path = "/services/iris/api"

    @pytest.mark.parametrize("object_number,add_errors,expected_response", (
            (0, False, status.HTTP_204_NO_CONTENT),
            (1, False, status.HTTP_204_NO_CONTENT),
            (10, False, status.HTTP_204_NO_CONTENT),
            (0, True, status.HTTP_204_NO_CONTENT),
            (1, True, status.HTTP_400_BAD_REQUEST),
            (10, True, status.HTTP_400_BAD_REQUEST)
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
        param = mommy.make(Parameter, user_id="222", show=True)
        param_dict = {"id": param.pk, "category": param.category}
        if not add_errors:
            param_dict["valor"] = "valor"
        return param_dict


class TestApplicationList(OpenAPIResourceListMixin, BaseOpenAPITest):
    path = "/masters/applications/"
    base_api_path = "/services/iris/api"

    model_class = Application
    delete_previous_objects = True

    def given_an_object(self):
        return mommy.make(Application, enabled=True, user_id="222")


class TestSupport(SoftDeleteCheckMixin, AdminUserMixin, SetPermissionMixin, SetUserGroupMixin, BaseOpenAPIResourceTest):
    path = "/masters/supports/"
    base_api_path = "/services/iris/api"

    model_class = Support
    deleted_model_class = Support
    delete_previous_objects = True

    def get_default_data(self):
        return {
            "description": uuid.uuid4(),
            "order": 1,
            "allow_nd": True,
            "communication_media_required": True,
            "register_required": False
        }

    def given_create_rq_data(self):
        return {
            "description": "test",
            "order": 1,
            "allow_nd": False,
            "communication_media_required": True,
            "register_required": False
        }

    def when_data_is_invalid(self, data):
        data["description"] = ""

    @staticmethod
    def add_response_channel(obj):
        response_channel = ResponseChannel.objects.get(id=random.randint(0, 5))
        obj["response_channels"].append({"response_channel": response_channel.pk})
        return obj

    def given_a_complete_update(self, obj):
        return self.add_response_channel(obj)

    def given_a_partial_update(self, obj):
        return self.add_response_channel(obj)

    def test_update_put(self):
        load_missing_data()
        super().test_update_put()

    def test_update_patch(self):
        load_missing_data()
        super().test_update_patch()


class TestApplicantType(SoftDeleteCheckMixin, AdminUserMixin, SetPermissionMixin, SetUserGroupMixin,
                        BaseOpenAPIResourceTest):
    path = "/masters/applicant_types/"
    base_api_path = "/services/iris/api"
    object_pk_not_exists = 1000

    model_class = ApplicantType
    deleted_model_class = ApplicantType
    delete_previous_objects = True

    def get_default_data(self):
        return {
            "description": uuid.uuid4(),
            "order": 1,
            "send_response": True
        }

    def given_create_rq_data(self):
        return {
            "description": "test",
            "order": 1,
            "send_response": False
        }

    def when_data_is_invalid(self, data):
        data["description"] = ""


class TestInputChannel(SoftDeleteCheckMixin, AdminUserMixin, SetPermissionMixin, SetUserGroupMixin,
                       BaseOpenAPIResourceTest):
    path = "/masters/input_channels/"
    base_api_path = "/services/iris/api"
    deleted_model_class = InputChannel
    model_class = InputChannel
    delete_previous_objects = True

    def get_default_data(self):
        if not ApplicantType.objects.filter(id=ApplicantType.CIUTADA):
            applicant_type = ApplicantType(id=ApplicantType.CIUTADA)
            applicant_type.save()
        support = mommy.make(Support, user_id="2222")
        return {
            "user_id": str(uuid.uuid4())[:20],
            "description": uuid.uuid4(),
            "visible": True,
            "order": 1,
            "supports": [{"support": support.pk, "order": 0, "description": support.description}],
            "applicant_types": [{"applicant_type": ApplicantType.CIUTADA, "order": 0}],
            "can_be_mayorship": True
        }

    def given_create_rq_data(self):
        if not ApplicantType.objects.filter(id=ApplicantType.CIUTADA):
            applicant_type = ApplicantType(id=ApplicantType.CIUTADA)
            applicant_type.save()
        support = mommy.make(Support, user_id="2222")
        return {
            "user_id": str(uuid.uuid4())[:20],
            "description": "test",
            "visible": False,
            "order": 1,
            "supports": [{"support": support.pk, "order": 0, "description": support.description}],
            "applicant_types": [{"applicant_type": ApplicantType.CIUTADA, "order": 0}],
            "can_be_mayorship": False
        }

    def when_data_is_invalid(self, data):
        data["description"] = ""

    def given_an_object(self):
        return mommy.make(InputChannel, user_id="2222")


class TestProcess(OpenAPIResourceListMixin, BaseOpenAPITest):
    path = "/masters/process/"
    base_api_path = "/services/iris/api"

    model_class = Process
    delete_previous_objects = True
    object_tuples = Process.TYPES
    paginate_by = len(Process.TYPES)
    add_user_id = False

    def given_an_object_process(self):
        return mommy.make(Process)

    @pytest.mark.parametrize("object_number", (0, 1, 3))
    def test_list(self, object_number):
        ElementDetail.objects.all().delete()
        Process.objects.all().delete()

        if self.model_class and object_number > 1 and self.object_tuples:
            # If we have to create N objects and the ids are setted by default,
            # mommy can override the objects using the same id more than one time
            object_number = self.paginate_by
            [self.given_a_tupled_object(object_id) for object_id, _ in self.object_tuples[:object_number]]
        else:
            [self.given_an_object_process() for _ in range(0, object_number)]
        response = self.list(force_params={'page_size': self.paginate_by})
        assert response.status_code == HTTP_200_OK
        self.should_return_list(object_number, self.paginate_by, response)


class TestDistrict(OpenAPIResourceListMixin, BaseOpenAPITest):
    path = "/masters/districts/"
    base_api_path = "/services/iris/api"

    model_class = District
    delete_previous_objects = True
    object_tuples = District.DISTRICTS
    paginate_by = len(District.DISTRICTS)
    add_user_id = False


class TestResolutionType(SoftDeleteCheckMixin, AdminUserMixin, SetPermissionMixin, SetUserGroupMixin,
                         BaseOpenAPIResourceTest):
    path = "/masters/resolution-types/"
    base_api_path = "/services/iris/api"
    deleted_model_class = ResolutionType
    model_class = ResolutionType
    delete_previous_objects = True

    def get_default_data(self):
        return {
            "description": uuid.uuid4(),
            "can_claim_inside_ans": True,
            "order": 1
        }

    def given_create_rq_data(self):
        return {
            "description": uuid.uuid4(),
            "can_claim_inside_ans": False,
            "order": 1
        }

    def when_data_is_invalid(self, data):
        data["description"] = ""


class TestAnnouncements(OpenAPIResourceExcelExportMixin, SoftDeleteCheckMixin, AdminUserMixin, SetPermissionMixin,
                        SetUserGroupMixin, BaseOpenAPICRUResourceTest):
    path = "/masters/announcements/"
    base_api_path = "/services/iris/api"
    deleted_model_class = Announcement
    permission_codename = ANNOUNCEMENTS

    def get_default_data(self):
        set_expiration_date = random.randint(0, 1)
        return {
            "title": uuid.uuid4(),
            "description": uuid.uuid4(),
            "expiration_date": timezone.now() + timedelta(days=365) if set_expiration_date else None,
            "important": True,
            "xaloc": True,
            "order": 1
        }

    def given_create_rq_data(self):
        set_expiration_date = random.randint(0, 1)
        return {
            "title": uuid.uuid4(),
            "description": uuid.uuid4(),
            "expiration_date": timezone.now() + timedelta(days=365) if set_expiration_date else None,
            "important": True,
            "xaloc": True,
            "order": 1
        }

    def when_data_is_invalid(self, data):
        data["description"] = ""


class TestAnnouncementsSeenBy(PutOperation, AdminUserMixin, BaseOpenAPITest):
    detail_path = "/masters/announcements/{id}/mark-as-seen/"
    base_api_path = "/services/iris/api"

    @pytest.mark.parametrize("delete_announcement,expected_response,expected_seen_by", (
            (False, HTTP_200_OK, 1),
            (True, HTTP_404_NOT_FOUND, 0),
    ))
    def test_annoucements_seen_by(self, delete_announcement, expected_response, expected_seen_by):
        announcement = mommy.make(Announcement, user_id="2222")
        if delete_announcement:
            announcement.delete()
        response = self.put(force_params={"id": announcement.pk})
        assert response.status_code == expected_response
        assert announcement.seen_by.count() == expected_seen_by


class TestMastersAdminPermissions(BasePermissionsTest):
    base_api_path = "/services/iris/api"

    cases = [
        {
            "detail_path": "/masters/input_channels/{id}/",
            "model_class": InputChannel,
        },
        {
            "detail_path": "/masters/supports/{id}/",
            "model_class": Support,
        },
        {
            "detail_path": "/masters/announcements/{id}/",
            "model_class": Announcement,
        },
        {
            "detail_path": "/masters/communication_medias/{id}/",
            "model_class": CommunicationMedia,
        },
        {
            "detail_path": "/masters/cancel-reasons/{id}/",
            "model_class": Reason,
        },
        {
            "detail_path": "/masters/reasign-reasons/{id}/",
            "model_class": Reason,
        },
        {
            "detail_path": "/masters/resolution-types/{id}/",
            "model_class": ResolutionType,
        },
    ]

    def given_an_object(self, model_class):
        if "cancel" in self.detail_path and model_class == Reason:
            return mommy.make(model_class, user_id="2222", reason_type="1")
        if "reasign" in self.detail_path and model_class == Reason:
            return mommy.make(model_class, user_id="2222", reason_type="2")
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
        for perm in [ADMIN, ANNOUNCEMENTS]:
            admin_permission = Permission.objects.get(codename=perm)
            ProfilePermissions.objects.create(permission=admin_permission, profile=profile)
        GroupProfiles.objects.create(group=group, profile=profile)


class TestLetterTemplateList(OpenAPIResourceListMixin, BaseOpenAPITest):
    path = "/masters/letter-templates/"
    base_api_path = "/services/iris/api"

    @pytest.mark.parametrize("object_number", (0, 1, 11))
    def test_list(self, object_number):
        [self.given_an_object(number) for number in range(0, object_number)]
        response = self.list(force_params={'page_size': self.paginate_by})
        assert response.status_code == HTTP_200_OK
        self.should_return_list(object_number, self.paginate_by, response)

    def given_an_object(self, number):
        return mommy.make(LetterTemplate, user_id="222222", id=number)
