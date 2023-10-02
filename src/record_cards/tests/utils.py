import random
from datetime import timedelta, date

from django.contrib.auth.models import User
from django.core.files import File
from django.http import HttpRequest
from django.utils import timezone
from model_mommy import mommy

from features.models import Feature
from iris_masters.models import (InputChannel, MediaType, ApplicantType, Application, CommunicationMedia, RecordType,
                                 Support, Process, RecordState, ResponseChannel, District, InputChannelSupport,
                                 LetterTemplate)
from iris_masters.permissions import ADMIN
from profiles.models import (Group, UserGroup, GroupInputChannel, Permission, Profile, ProfilePermissions,
                             GroupProfiles, GroupsUserGroup)
from record_cards.models import (Ubication, Citizen, Applicant, Request, RecordCard, SocialEntity, RecordCardResponse,
                                 RecordCardSpecialFeatures, RecordCardFeatures, Workflow, RecordFile,
                                 RecordCardTextResponse)
from record_cards.permissions import (VALIDATE, CREATE, UPDATE, CANCEL, RECARD_THEME_CHANGE_SYSTEM,
                                      RESP_CHANNEL_UPDATE)
from record_cards.serializers import RecordCardResponseSerializer, UbicationSerializer
from themes.models import (ElementDetailResponseChannel, ElementDetailFeature, DerivationDirect, DerivationDistrict)
from themes.tests.utils import CreateThemesMixin
from communications.tests.utils import load_missing_data


class CreateRecordCardMixin(CreateThemesMixin):

    def create_record_card(self, record_state_id=None, process_pk=None, ans_limit_date=None,  # noqa C901
                           ans_limit_nearexpire=None, applicant=None, citizen_dni=False, social_entity_cif=False,
                           requires_appointment=False, element_detail=None, validated_reassignable=False, urgent=False,
                           user_id=None, ans_limit_delta=None, responsible_profile=None, theme_response_channels=None,
                           immediate_response=False, multirecord_from=None, allows_ssi=False, previous_created_at=None,
                           create_record_card_response=False, ubication=None, district_id=None, reasigned=False,
                           features=None, special_features=None, create_worflow=False, input_channel=None, enabled=True,
                           pend_applicant_response=False, applicant_response=False, mayorship=False, claims_number=0,
                           fill_active_mandatory_fields=True, claimed_from_id=None, similar_process=False,
                           response_time_expired=False, possible_similar_records=False, application=None,
                           reassignment_not_allowed=False, communication_media_date=None, cancel_request=False,
                           communication_media_detail="None", creation_group=None, applicant_type=None,
                           closing_date=None, input_channel_description=None, response_to_responsible=False,
                           pend_response_responsible=False, postal_code='01317', province='Barcelona',
                           municipality='Barcelona', normalized_record_id=None):
        load_missing_data()
        if not user_id:
            user_id = "22222"

        if not input_channel:
            if not input_channel_description:
                input_channel = mommy.make(InputChannel, user_id=user_id)
            else:
                input_channel = mommy.make(InputChannel, user_id=user_id, description=input_channel_description)
        if not creation_group:
            letters_num = LetterTemplate.objects.count()
            letter_template = mommy.make(LetterTemplate, user_id=user_id, pk=letters_num+1)
            creation_group = mommy.make(Group, user_id=user_id, profile_ctrl_user_id=user_id,
                                        letter_template_id=letter_template)

        if not applicant_type:
            applicant_type = mommy.make(ApplicantType, user_id=user_id)

        media_type = mommy.make(MediaType, user_id=user_id)
        record_type = mommy.make(RecordType, user_id=user_id)
        communication_media = mommy.make(CommunicationMedia, user_id=user_id, input_channel=input_channel,
                                         media_type=media_type)
        process_id = process_pk if process_pk else Process.CLOSED_DIRECTLY

        if not Process.objects.filter(id=process_id):
            process = mommy.make(Process, id=process_id)
            process_id = process.id

        if not element_detail:
            element_detail = self.create_element_detail(record_type_id=record_type.pk, process_id=process_id,
                                                        requires_appointment=requires_appointment,
                                                        validated_reassignable=validated_reassignable,
                                                        allows_ssi=allows_ssi, immediate_response=immediate_response,
                                                        fill_active_mandatory_fields=fill_active_mandatory_fields)
        if features:
            for feature in features:
                ElementDetailFeature.objects.create(element_detail=element_detail, feature=feature, is_mandatory=True)
        if special_features:
            for feature in special_features:
                ElementDetailFeature.objects.create(element_detail=element_detail, feature=feature, is_mandatory=True)

        if theme_response_channels:
            for response_channel in theme_response_channels:
                ElementDetailResponseChannel.objects.create(elementdetail=element_detail,
                                                            responsechannel_id=response_channel)

        request = self.set_request(user_id, applicant, citizen_dni, social_entity_cif, input_channel,
                                   communication_media, application, applicant_type)
        if not ubication:
            ubication = mommy.make(Ubication, user_id=user_id, district_id=district_id)
        support = mommy.make(Support, user_id=user_id)
        if not responsible_profile:
            responsible_profile = mommy.make(Group, user_id=user_id, profile_ctrl_user_id=user_id, parent=None)
        GroupInputChannel.objects.get_or_create(group=responsible_profile, input_channel=input_channel)
        if hasattr(self, "user") and not hasattr(self.user, "usergroup"):
            self.set_group_permissions(user_id, responsible_profile)
            user_group = UserGroup.objects.create(user=self.user, group=responsible_profile)
            GroupsUserGroup.objects.create(user_group=user_group, group=responsible_profile)
        if normalized_record_id:
            record_card = mommy.make(RecordCard, user_id=user_id, element_detail=element_detail, request=request,
                                     ubication=ubication, record_state_id=record_state_id, record_type=record_type,
                                     applicant_type=applicant_type, responsible_profile=responsible_profile,
                                     support=support, communication_media=communication_media,
                                     process_id=process_id, urgent=urgent, multirecord_from=multirecord_from,
                                     enabled=enabled, reasigned=reasigned, mayorship=mayorship,
                                     claimed_from_id=claimed_from_id, similar_process=similar_process,
                                     response_time_expired=response_time_expired, claims_number=claims_number,
                                     possible_similar_records=possible_similar_records, input_channel=input_channel,
                                     creation_department="TEST", close_department="TEST", closing_date=closing_date,
                                     communication_media_date=communication_media_date, cancel_request=cancel_request,
                                     communication_media_detail=communication_media_detail,
                                     response_to_responsible=response_to_responsible, creation_group=creation_group,
                                     pend_response_responsible=pend_response_responsible,
                                     normalized_record_id=normalized_record_id)
        else:
            record_card = mommy.make(RecordCard, user_id=user_id, element_detail=element_detail, request=request,
                                     ubication=ubication, record_state_id=record_state_id, record_type=record_type,
                                     applicant_type=applicant_type, responsible_profile=responsible_profile,
                                     support=support, communication_media=communication_media,
                                     input_channel=input_channel, process_id=process_id, urgent=urgent,
                                     multirecord_from=multirecord_from, enabled=enabled, reasigned=reasigned,
                                     mayorship=mayorship, claimed_from_id=claimed_from_id,
                                     response_time_expired=response_time_expired, claims_number=claims_number,
                                     possible_similar_records=possible_similar_records,
                                     creation_department="TEST", close_department="TEST", closing_date=closing_date,
                                     communication_media_date=communication_media_date, cancel_request=cancel_request,
                                     communication_media_detail=communication_media_detail,
                                     response_to_responsible=response_to_responsible,
                                     pend_response_responsible=pend_response_responsible,
                                     similar_process=similar_process, creation_group=creation_group)

        self.set_features(record_card, features, special_features)

        self.set_record_card_post_create_info(record_card, record_state_id, multirecord_from, create_worflow,
                                              previous_created_at, pend_applicant_response, applicant_response,
                                              reassignment_not_allowed)
        self.set_ans_limit_fields(record_card, ans_limit_date, ans_limit_nearexpire, ans_limit_delta)
        if create_record_card_response:
            RecordCardResponse.objects.create(record_card=record_card, response_channel_id=ResponseChannel.EMAIL,
                                              address_mobile_email="test@apsl.net", postal_code=postal_code,
                                              province=province, municipality=municipality)
            ElementDetailResponseChannel.objects.create(responsechannel_id=ResponseChannel.EMAIL,
                                                        elementdetail_id=record_card.element_detail_id)
        return record_card

    def set_request(self, user_id, applicant, citizen_dni, social_entity_cif, input_channel, communication_media,
                    application, applicant_type):
        applicant = self.set_applicant(user_id, applicant, citizen_dni, social_entity_cif)
        if not application:
            application = mommy.make(Application, user_id=user_id)
        return mommy.make(Request, user_id=user_id, input_channel=input_channel, application=application,
                          applicant_type=applicant_type, applicant=applicant, communication_media=communication_media)

    def set_features(self, record_card, features, special_features):
        if features:
            self.set_record_features(record_card, features)
        if special_features:
            self.set_record_features(record_card, special_features)

    @staticmethod
    def set_group_permissions(user_id, responsible_profile, permissions_list=None):
        if not permissions_list:
            permissions_list = [VALIDATE, CREATE, UPDATE, CANCEL, ADMIN]
        profile = mommy.make(Profile, user_id=user_id)
        for permission in Permission.objects.filter(codename__in=permissions_list):
            ProfilePermissions.objects.create(permission=permission, profile=profile)
        GroupProfiles.objects.create(group=responsible_profile, profile=profile)

    @staticmethod
    def set_record_features(record_card, features):
        for feature in features:
            if feature.is_special:
                RecordCardSpecialFeatures.objects.create(record_card=record_card, feature=feature,
                                                         value=str(random.randint(0, 99)))
            else:
                RecordCardFeatures.objects.create(record_card=record_card, feature=feature,
                                                  value=str(random.randint(0, 99)))

    @staticmethod
    def set_applicant(user_id, applicant=None, citizen_dni=False, social_entity_cif=False):
        if citizen_dni:
            citizen = mommy.make(Citizen, user_id=user_id, dni=citizen_dni)
            applicant = mommy.make(Applicant, user_id=user_id, citizen=citizen)
        elif social_entity_cif:
            social_entity = mommy.make(SocialEntity, user_id=user_id, cif=social_entity_cif)
            applicant = mommy.make(Applicant, user_id=user_id, social_entity=social_entity)
        if not applicant:
            citizen = mommy.make(Citizen, user_id=user_id, mib_code=971691,  name='test_name',
                                 first_surname='test_1',
                                 second_surname='test_2',
                                 dni='11111111H')
            applicant = mommy.make(Applicant, user_id=user_id, citizen=citizen)
        return applicant

    @staticmethod
    def set_record_card_post_create_info(record_card, record_state_id, multirecord_from, create_workflow,
                                         previous_created_at, pend_applicant_response, applicant_response,
                                         reassignment_not_allowed):
        if record_state_id:
            record_card.record_state_id = record_state_id
        if multirecord_from:
            record_card.is_multirecord = True
        if create_workflow:
            record_card.workflow = Workflow.objects.create(main_record_card=record_card, state=record_card.record_state)
        if previous_created_at:
            record_card.created_at -= timedelta(days=365)
        if pend_applicant_response:
            record_card.pend_applicant_response = True
        if applicant_response:
            record_card.applicant_response = True
        if reassignment_not_allowed:
            record_card.reassignment_not_allowed = True

        record_card.save()

    @staticmethod
    def set_ans_limit_fields(record_card, ans_limit_date, ans_limit_nearexpire, ans_limit_delta):
        if ans_limit_date:
            record_card.ans_limit_date = ans_limit_date
        if ans_limit_nearexpire:
            record_card.ans_limit_nearexpire = ans_limit_nearexpire
        if ans_limit_delta:
            record_card.ans_limit_date = timezone.now() + timedelta(hours=ans_limit_delta)
        record_card.save()

    def get_record_card_data(self, create_group=True, is_anonymous=False, autovalidate_records=False,  # noqa C901
                             group=None, citizen_dni=None, support_nd=False, support=None, multirecord_from=None,
                             feature=None, special_feature=None, set_group_input_channel=True, district_id=None,
                             copy_responsechannel=False, process_id=Process.CLOSED_DIRECTLY, element_detail=None,
                             input_channel=None, user_id="22222", mayorship=False, add_update_permissions=False,
                             set_suport_input_channel=True, applicant_type=None, applicant=None, ubication=None):

        if not input_channel:
            input_channel = mommy.make(InputChannel, user_id=user_id)
        media_type = mommy.make(MediaType, user_id=user_id)
        record_type = mommy.make(RecordType, user_id=user_id)

        if not element_detail:
            element_detail = self.create_element_detail(autovalidate_records=autovalidate_records,
                                                        record_type_id=record_type.pk, process_id=process_id)
        ElementDetailResponseChannel.objects.create(elementdetail=element_detail,
                                                    responsechannel_id=ResponseChannel.EMAIL)
        communication_media = mommy.make(CommunicationMedia, user_id=user_id, input_channel=input_channel,
                                         media_type=media_type)
        record_state = RecordState.objects.get(id=RecordState.PENDING_VALIDATE)
        if not ubication:
            ubication = mommy.make(Ubication, user_id=user_id, district_id=district_id)

        if not feature:
            feature = mommy.make(Feature, user_id=user_id, is_special=False)
        ElementDetailFeature.objects.create(feature=feature, element_detail=element_detail, enabled=True,
                                            is_mandatory=True)
        if not special_feature:
            special_feature = mommy.make(Feature, user_id=user_id, is_special=True)
        ElementDetailFeature.objects.create(feature=special_feature, element_detail=element_detail, enabled=True)

        if not group:
            group, _ = Group.objects.get_or_create(profile_ctrl_user_id="GRP0001", user_id=user_id, parent=None,
                                                   is_anonymous=is_anonymous)
        if set_group_input_channel:
            GroupInputChannel.objects.get_or_create(group=group, input_channel=input_channel)
        if hasattr(self, "user") and not hasattr(self.user, "usergroup") and create_group:
            user_group = UserGroup.objects.create(user=self.user, group=group)
            GroupsUserGroup.objects.create(user_group=user_group, group=group)
        self.set_group_permissions(user_id, group)

        self.add_update_permissions(add_update_permissions)

        applicant = self.set_applicant(user_id, applicant=applicant, citizen_dni=citizen_dni)
        support = self.define_support(support, support_nd)
        self.set_suport_input_channel(set_suport_input_channel, input_channel, support)
        if not applicant_type:
            applicant_type = mommy.make(ApplicantType, user_id=user_id)

        data = {
            "description": "testestest",
            "element_detail_id": element_detail.pk,
            "applicant_id": applicant.pk,
            "applicant_type_id": applicant_type.pk,
            "ubication": {
                "id": ubication.id,
                "via_type": ubication.via_type,
                "official_street_name": ubication.official_street_name,
                "street": ubication.street,
                "street2": ubication.street2,
                "neighborhood": ubication.neighborhood,
                "neighborhood_b": ubication.neighborhood_b,
                "neighborhood_id": ubication.neighborhood_id,
                "district": ubication.district_id,
                "statistical_sector": ubication.statistical_sector,
                "geocode_validation": ubication.geocode_validation,
                "geocode_district_id": ubication.geocode_district_id,
                "research_zone": ubication.research_zone,
                "floor": ubication.floor,
                "stair": ubication.stair,
                "door": ubication.door,
                "letter": ubication.letter,
                "coordinate_x": ubication.coordinate_x,
                "coordinate_y": ubication.coordinate_y,
                "coordinate_utm_x": ubication.coordinate_utm_x,
                "coordinate_utm_y": ubication.coordinate_utm_y,
                "latitude": ubication.latitude,
                "longitude": ubication.longitude,
                "xetrs89a": ubication.xetrs89a,
                "yetrs89a": ubication.yetrs89a,
                "numbering_type": ubication.numbering_type
            },
            "process": int(Process.CLOSED_DIRECTLY),
            "record_state_id": record_state.pk,
            "record_type_id": record_type.pk,
            "closing_date": timezone.now() + timedelta(days=12),
            "communication_media_id": communication_media.pk,
            "communication_media_date": date(2019, 12, 12),
            "communication_media_detail": "",
            "support_id": support.pk,
            "email_external_derivation": "test@test.com",
            "user_displayed": "test",
            "start_date_process": date(2019, 12, 12),
            "notify_quality": True,
            "multi_complaint": 10,
            "input_channel_id": input_channel.pk,
            "ci_date": date(2019, 12, 12),
            "user_id": "2222222",
            "auxiliary": "",
            "mayorship": mayorship,
            "recordcardresponse": {
                "address_mobile_email": "test@test.net",
                "number": "",
                "municipality": "test",
                "province": "test",
                "postal_code": "02712",
                "answered": False,
                "enabled": True,
                "via_type": "",
                "via_name": "",
                "floor": "",
                "door": "",
                "stair": "",
                "correct_response_data": False,
                "response_channel": ResponseChannel.EMAIL,
                "worked": False
            },
            "features": [{"feature": str(feature.pk), "value": "test_value", "description": "new_description"}],
            "special_features": [
                {"feature": str(special_feature.pk), "value": "testvalue", "description": "newdescription"}
            ],
            "organization": "organitzation"
        }
        if multirecord_from:
            data["multirecord_from"] = multirecord_from
            data["multirecord_copy_responsechannel"] = copy_responsechannel

        return data

    def add_update_permissions(self, add_update_permissions):
        if add_update_permissions:
            self.set_group_permissions("aaaaaaa", self.user.usergroup.group,
                                       permissions_list=[RESP_CHANNEL_UPDATE])

    @staticmethod
    def define_support(support, support_nd):
        if not support:
            support = mommy.make(Support, user_id="2222", allow_nd=support_nd)
        else:
            support.allow_nd = support_nd
            support.save()
        return support

    @staticmethod
    def set_suport_input_channel(set_suport_input_channel, input_channel, support):
        if set_suport_input_channel:
            InputChannelSupport.objects.create(input_channel=input_channel, support=support)

    def set_response_text(self, rc):
        return mommy.make(RecordCardTextResponse, record_card=rc, user_id="1")


class SetGroupRequestMixin:

    @staticmethod
    def set_group_request(group=None, citizen_nd=False):
        if not group:
            group = mommy.make(Group, profile_ctrl_user_id="GRP0001", user_id="2222", citizen_nd=citizen_nd)
        try:
            user = User.objects.get(username="test")
        except User.DoesNotExist:
            user = User.objects.create(username="test")
        try:
            user_group = UserGroup.objects.get(user=user, group=group)
        except UserGroup.DoesNotExist:
            user_group = UserGroup.objects.create(user=user, group=group)
        GroupsUserGroup.objects.create(user_group=user_group, group=group)
        request = HttpRequest()
        setattr(user, 'imi_data', {'user': 'test', 'dptcuser': 'test'})
        request.user = user
        return group, request


class SetPermissionMixin:

    @staticmethod
    def set_permission(permission, group=None):
        if not group:
            group = mommy.make(Group, profile_ctrl_user_id="GRP0001", user_id="2222")
        profile = mommy.make(Profile, user_id="22222")
        db_permission = Permission.objects.get(codename=permission)
        ProfilePermissions.objects.create(permission=db_permission, profile=profile)
        GroupProfiles.objects.create(group=group, profile=profile)
        return group


class FeaturesMixin:

    @staticmethod
    def create_features(features_number=3, is_special=False):
        features = []
        for _ in range(features_number):
            features.append(mommy.make(Feature, user_id="222", is_special=is_special))
        return features


class SetUserGroupMixin:

    def set_usergroup(self, group=None):
        if not group:
            group = mommy.make(Group, user_id="2222", profile_ctrl_user_id="2222222", parent=None, lft=1, rght=2,
                               level=0, tree_id=1, tree_levels=0)
            Group.objects.rebuild()
        user_group = UserGroup.objects.create(user=self.user, group=group)
        GroupsUserGroup.objects.create(user_group=user_group, group=group)


class SetRecordCardCreateThemeNoVisiblePermissonMixin:

    def set_recard_create_themenovisible_permission(self, group):
        no_visible_permission = Permission.objects.get(codename=RECARD_THEME_CHANGE_SYSTEM)
        profile = mommy.make(Profile, user_id="2222")
        ProfilePermissions.objects.create(profile=profile, permission=no_visible_permission)
        create_recard_permission = Permission.objects.get(codename=CREATE)
        ProfilePermissions.objects.create(profile=profile, permission=create_recard_permission)
        GroupProfiles.objects.create(group=group, profile=profile)


class CreateDerivationsMixin:

    @staticmethod
    def create_direct_derivation(element_detail_id, record_state_id, group=None):
        if not group:
            group = mommy.make(Group, user_id="2222", profile_ctrl_user_id="2222222", parent=None, lft=1, rght=2,
                               level=0, tree_id=1)
        DerivationDirect.objects.create(element_detail_id=element_detail_id, record_state_id=record_state_id,
                                        group=group)
        return group

    @staticmethod
    def create_district_derivation(element_detail_id, record_state_id, group=None):
        if not group:
            group = mommy.make(Group, user_id="2222", profile_ctrl_user_id="2222222", parent=None, lft=1, rght=2,
                               level=0, tree_id=1)
        for district in District.objects.filter(allow_derivation=True):
            DerivationDistrict.objects.create(element_detail_id=element_detail_id, group=group,
                                              district_id=district.pk, record_state_id=record_state_id)
        return group


class CreateRecordFileMixin:

    @staticmethod
    def create_file(tmpdir_factory, record_card, file_number):
        filename = "test{}.txt".format(file_number)
        fn = tmpdir_factory.mktemp("data").join(filename)
        with open(fn, "w") as file:
            file.write("Woops! I have deleted the content!")

        with open(fn, "r") as file:
            mem_file = File(file=file, name=filename)
            return RecordFile.objects.create(file=mem_file, record_card=record_card, filename=filename)


class RecordUpdateMixin:
    @staticmethod
    def set_initial_expected_data(record_card):
        return {
            "expected_description": record_card.description,
            "expected_support": record_card.support_id,
            "expected_input_channel": record_card.input_channel_id,
            "expected_communication_media": record_card.communication_media_id,
            "expected_communication_media_date": record_card.communication_media_date,
            "expected_communication_media_detail": record_card.communication_media_detail,
            "expected_mayorship": record_card.mayorship,
            "expected_ubication": record_card.ubication_id,
            "expected_response_channel": record_card.recordcardresponse.response_channel_id
        }

    @staticmethod
    def set_data_update(record_card, description, change_features, features, update_mayorship,
                        update_ubication, update_response_channel):

        data = {"reference": record_card.normalized_record_id}
        update_data = {}
        if isinstance(description, str):
            data["description"] = description
            update_data["description"] = description

        if change_features:
            data["features"] = [{"feature": f.pk, "value": str(random.randint(0, 99))}
                                for f in features if not f.is_special]
            data["special_features"] = [{"feature": f.pk, "value": str(random.randint(0, 99))}
                                        for f in features if f.is_special]
        if update_mayorship:
            new_mayorship = not record_card.mayorship
            data["mayorship"] = new_mayorship
            update_data["new_mayorship"] = new_mayorship

        if update_ubication:
            new_ubication = mommy.make(Ubication, user_id="22222")
            data["ubication"] = UbicationSerializer(instance=new_ubication).data
            update_data["new_ubication"] = new_ubication.pk

        if update_response_channel:
            record_card_response_data = RecordCardResponseSerializer(instance=record_card.recordcardresponse).data
            record_card_response_data["response_channel"] = ResponseChannel.SMS
            data["recordcardresponse"] = record_card_response_data
            update_data["new_response_channel"] = ResponseChannel.SMS
        return data, update_data

    @staticmethod
    def update_expected_data(expected_data, updated_data):
        if "description" in updated_data:
            expected_data["expected_description"] = updated_data["description"]
        if "new_mayorship" in updated_data:
            expected_data["expected_mayorship"] = updated_data["new_mayorship"]
        if "new_ubication" in updated_data:
            expected_data["expected_ubication"] = updated_data["new_ubication"]
        if "new_response_channel" in updated_data:
            expected_data["expected_response_channel"] = updated_data["new_response_channel"]
