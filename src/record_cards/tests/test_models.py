from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from django.dispatch import Signal
from django.utils import timezone
from django.utils.functional import cached_property
from mock import patch, Mock
from model_mommy import mommy

from communications.models import Conversation
from features.models import Feature
from iris_masters.models import (InputChannel, ApplicantType, RecordState, Support, District, Parameter,
                                 ResponseChannel, Process, Reason)
from main.utils import ENGLISH
from profiles.models import Group
from profiles.tests.utils import create_groups, add_extra_group_level
from record_cards.models import (RecordCard, RecordCardFeatures, RecordCardSpecialFeatures, RecordCardBlock, Ubication,
                                 Citizen, Applicant, RecordCardStateHistory, Comment, RecordCardAudit,
                                 RecordCardReasignation, RecordCardTextResponse, RecordCardTextResponseFiles,
                                 SocialEntity)
from record_cards.permissions import RECARD_COORDINATOR_VALIDATION_DAYS, RECARD_VALIDATE_OUTAMBIT
from record_cards.record_actions.external_validators import DummyExternalValidator, DummyExternalValidatorNotValidate
from record_cards.tests.utils import (CreateRecordCardMixin, CreateDerivationsMixin, SetUserGroupMixin,
                                      CreateRecordFileMixin)
from themes.tests.utils import CreateThemesMixin
from iris_masters.tests.utils import (load_missing_data_support, load_missing_data_process, load_missing_data_input,
                                      load_missing_data_districts, load_missing_data_reasons)


@pytest.mark.django_db
class TestRecordCardModel(CreateRecordCardMixin, CreateDerivationsMixin, CreateThemesMixin, SetUserGroupMixin):

    @cached_property
    def user(self):
        """
        :return: User for authenticated requests, override for custom needs.
        """
        return User.objects.create(username='test')

    @staticmethod
    def add_features(record_card):
        feature = mommy.make(Feature, user_id='222', values_type=None)
        RecordCardFeatures.objects.create(feature=feature, record_card=record_card, value="value")
        RecordCardSpecialFeatures.objects.create(feature=feature, record_card=record_card, value="value")

    @pytest.mark.parametrize("features_number,description,set_to_internal_claim,is_web_claim,set_alarms", (
            (0, "description", True, False, True),
            (1, "description2", False, True, False),
            (3, "description3", True, False, True)
    ))
    def test_create_record_claim(self, features_number, description, set_to_internal_claim, is_web_claim, set_alarms):
        if not ApplicantType.objects.filter(id=23):
            applicant_type = ApplicantType(id=23)
            applicant_type.save()
        load_missing_data_support()
        load_missing_data_input()
        record_card = self.create_record_card(create_record_card_response=True)
        [self.add_features(record_card) for _ in range(features_number)]

        signal = Mock(spec=Signal)
        with patch("record_cards.models.record_card_created", signal):
            claim = record_card.create_record_claim("user_id", description, is_web_claim=is_web_claim,
                                                    set_to_internal_claim=set_to_internal_claim, set_alarms=set_alarms)

            signal.send_robust.assert_called_with(record_card=claim, sender=RecordCard)

            assert record_card.pk != claim.pk
            assert record_card.normalized_record_id in claim.normalized_record_id
            assert "-" in claim.normalized_record_id
            assert claim.description == description
            assert record_card.recordcardresponse.response_channel_id == claim.recordcardresponse.response_channel_id
            assert record_card.recordcardresponse.pk != claim.recordcardresponse.pk

            assert record_card.recordcardfeatures_set.count() == claim.recordcardfeatures_set.count()
            assert record_card.recordcardspecialfeatures_set.count() == claim.recordcardspecialfeatures_set.count()

            if set_to_internal_claim:
                assert claim.input_channel_id == InputChannel.RECLAMACIO_INTERNA
                assert claim.applicant_type_id == ApplicantType.RECLAMACIO_INTERNA
                assert claim.support_id == Support.RECLAMACIO_INTERNA
            else:
                assert claim.input_channel_id == record_card.input_channel_id
                assert claim.applicant_type_id == record_card.applicant_type_id
                assert claim.support_id == record_card.support_id

            if set_alarms:
                assert record_card.citizen_alarm is True
                assert record_card.alarm is True
                assert claim.citizen_alarm is True
                assert claim.alarm is True
                if is_web_claim:
                    assert claim.citizen_web_alarm
                else:
                    assert not claim.citizen_web_alarm

    @pytest.mark.parametrize("time_expired_delta,user_id_block,user_id_check,expected_result", (
            (0, 'user', 'user', False),
            (10, 'user', 'user', False),
            (10, 'user1', 'user2', True),
            (0, 'user1', 'user2', False),
    ))
    def test_record_card_is_blocked(self, time_expired_delta, user_id_block, user_id_check, expected_result):
        record_card = self.create_record_card()
        expire_time = timezone.now() + timedelta(minutes=time_expired_delta)
        RecordCardBlock.objects.create(user_id=user_id_block, expire_time=expire_time, record_card=record_card)
        result = record_card.is_blocked(user_id_check)
        assert result is expected_result

    @pytest.mark.parametrize("automatic,perform_derivation,process_pk", (
            (True, True, Process.PLANING_RESOLUTION_RESPONSE),
            (True, False, Process.PLANING_RESOLUTION_RESPONSE),
            (False, True, Process.PLANING_RESOLUTION_RESPONSE),
            (False, False, Process.PLANING_RESOLUTION_RESPONSE),
            (True, True, Process.CLOSED_DIRECTLY),
            (False, True, Process.CLOSED_DIRECTLY),
    ))
    def test_change_state(self, automatic, perform_derivation, process_pk):
        load_missing_data_process()
        load_missing_data_reasons()
        close_department = "close_department"
        element_detail = self.create_element_detail(create_direct_derivations=True)
        # groups are created on derivations creation
        pk = Group.objects.all().first().pk
        dair = Group.objects.get(pk=pk)
        parent = Group.objects.get(pk=pk+1)

        record_card = self.create_record_card(element_detail=element_detail, responsible_profile=parent,
                                              process_pk=process_pk)
        previous_state_id = record_card.record_state_id
        next_state_id = record_card.next_step_code

        record_card.change_state(next_state_id, self.user, close_department, automatic=automatic,
                                 perform_derivation=perform_derivation)
        record_card = RecordCard.objects.get(pk=record_card.pk)
        assert record_card.record_state_id == next_state_id

        if process_pk == Process.CLOSED_DIRECTLY:
            assert record_card.close_department == close_department
            assert record_card.closing_date

        if perform_derivation:
            assert record_card.responsible_profile == dair
        else:
            assert record_card.responsible_profile == parent
        assert RecordCardStateHistory.objects.get(record_card=record_card, group=parent, automatic=automatic,
                                                  previous_state_id=previous_state_id, next_state_id=next_state_id)

    @pytest.mark.parametrize("response_channel_id", (ResponseChannel.NONE, ResponseChannel.LETTER, ResponseChannel.SMS))
    def test_pending_answer_change_state(self, response_channel_id):
        load_missing_data_reasons()

        close_department = "close_department"
        initial_record_state = RecordState.IN_RESOLUTION
        record_card = self.create_record_card(create_record_card_response=True, record_state_id=initial_record_state,
                                              process_pk=Process.PLANING_RESOLUTION_RESPONSE)
        record_card.recordcardresponse.response_channel_id = response_channel_id
        record_card.recordcardresponse.save()

        record_card.pending_answer_change_state(record_card.next_step_code, self.user, close_department)

        if response_channel_id == ResponseChannel.NONE:
            assert record_card.record_state_id == RecordState.CLOSED
            assert record_card.close_department == close_department
            assert record_card.closing_date
            assert RecordCardStateHistory.objects.get(
                record_card=record_card, automatic=True, previous_state_id=initial_record_state,
                next_state_id=RecordState.CLOSED)
            assert Comment.objects.get(record_card=record_card, reason=Reason.RECORDCARD_AUTOMATICALLY_CLOSED)
        else:
            assert record_card.record_state_id == RecordState.PENDING_ANSWER
            assert RecordCardStateHistory.objects.get(
                record_card=record_card, automatic=False, previous_state_id=initial_record_state,
                next_state_id=RecordState.PENDING_ANSWER)

    @pytest.mark.parametrize(
        "create_direct_derivation,create_district_derivation,district_id,record_state_id,derivation_state_id,reasigned,"
        "check_derivation", (
                (True, False, District.CIUTAT_VELLA, RecordState.PENDING_VALIDATE, RecordState.PENDING_VALIDATE, False,
                 True),
                (True, False, District.CIUTAT_VELLA, RecordState.PENDING_VALIDATE, RecordState.PENDING_VALIDATE, False,
                 False),
                (False, False, District.CIUTAT_VELLA, RecordState.PENDING_VALIDATE, RecordState.IN_PLANING, False,
                 True),
                (False, False, District.CIUTAT_VELLA, RecordState.PENDING_VALIDATE, RecordState.IN_PLANING, False,
                 False),
                (False, True, District.CIUTAT_VELLA, RecordState.PENDING_VALIDATE, RecordState.PENDING_VALIDATE, False,
                 True),
                (False, True, District.CIUTAT_VELLA, RecordState.PENDING_VALIDATE, RecordState.PENDING_VALIDATE, False,
                 False),
                (False, True, None, RecordState.PENDING_VALIDATE, RecordState.PENDING_VALIDATE, False, True),
                (False, True, None, RecordState.PENDING_VALIDATE, RecordState.PENDING_VALIDATE, False, False),
                (False, False, None, RecordState.PENDING_VALIDATE, RecordState.PENDING_VALIDATE, True, True),
                (False, False, None, RecordState.PENDING_VALIDATE, RecordState.PENDING_VALIDATE, True, False)
        ))
    def test_record_card_derivation(self, create_direct_derivation, create_district_derivation, district_id,
                                    record_state_id, derivation_state_id, reasigned, check_derivation):
        load_missing_data_districts()
        load_missing_data_reasons()
        record_card = self.create_record_card(district_id=district_id, record_state_id=record_state_id,
                                              reasigned=reasigned)

        for _ in range(3):
            mommy.make(Conversation, user_id='2222', record_card=record_card, is_opened=True)

        initial_responsible_profile = record_card.responsible_profile
        if create_direct_derivation:
            responsible_profile = self.create_direct_derivation(element_detail_id=record_card.element_detail_id,
                                                                record_state_id=derivation_state_id)
        elif create_district_derivation:
            district_group_id = self.create_district_derivation(element_detail_id=record_card.element_detail_id,
                                                                record_state_id=derivation_state_id)
            if district_id and record_state_id == derivation_state_id:
                responsible_profile = district_group_id
            else:
                responsible_profile = None
        else:
            responsible_profile = None

        with patch('profiles.tasks.send_allocated_notification.delay') as mock_delay:
            record_card.derivate(user_id="userid", is_check=check_derivation)
            if responsible_profile:
                if not check_derivation:
                    assert record_card.responsible_profile == responsible_profile
                    assert not record_card.user_displayed
                    assert RecordCardReasignation.objects.get(record_card=record_card,
                                                              next_responsible_profile=responsible_profile,
                                                              reason_id=Reason.DERIVATE_RESIGNATION)
                    mock_delay.assert_called_once()
                assert Conversation.objects.filter(record_card=record_card).count() == 3
                assert Conversation.objects.filter(record_card=record_card, is_opened=check_derivation).count() == 3
            else:
                assert record_card.responsible_profile == initial_responsible_profile

    @pytest.mark.parametrize("reasigned,allow_multiderivation", (
            (True, True), (True, False), (False, True), (False, False)
    ))
    def test_record_card_derivate_allow_derivation(self, reasigned, allow_multiderivation):
        load_missing_data_districts()
        load_missing_data_reasons()
        dair, parent, _, _, _, _ = create_groups()
        record_card = self.create_record_card(district_id=District.CIUTAT_VELLA, responsible_profile=dair,
                                              record_state_id=RecordState.IN_RESOLUTION, reasigned=reasigned)
        record_card.allow_multiderivation = allow_multiderivation
        record_card.save()
        self.create_district_derivation(element_detail_id=record_card.element_detail_id,
                                        record_state_id=RecordState.IN_RESOLUTION, group=parent)
        record_card.derivate(user_id="user_id")
        if reasigned and not allow_multiderivation:
            assert record_card.responsible_profile == dair
        else:
            assert record_card.responsible_profile == parent

    @pytest.mark.parametrize("reasigned,allow_multiderivation", (
            (True, True), (True, False), (False, True), (False, False)
    ))
    def test_record_card_derivate_allow_derivation_pending_validate(self, reasigned, allow_multiderivation):
        dair, parent, _, _, _, _ = create_groups()
        load_missing_data_districts()
        load_missing_data_reasons()
        record_card = self.create_record_card(district_id=District.CIUTAT_VELLA, responsible_profile=dair,
                                              record_state_id=RecordState.PENDING_VALIDATE, reasigned=reasigned)
        record_card.allow_multiderivation = allow_multiderivation
        record_card.save()
        self.create_district_derivation(element_detail_id=record_card.element_detail_id,
                                        record_state_id=RecordState.PENDING_VALIDATE, group=parent)
        record_card.derivate(user_id="user_id")
        assert record_card.responsible_profile == parent

    @pytest.mark.parametrize("exceed_hours", (True, False))
    def test_exceed_temporary_proximity(self, exceed_hours):
        element_detail = self.create_element_detail(similarity_hours=5, fill_active_mandatory_fields=False)

        record_card = self.create_record_card(element_detail=element_detail)
        possible_similar = self.create_record_card(element_detail=element_detail)
        if exceed_hours:
            possible_similar.created_at += timedelta(hours=10)

        assert record_card.exceed_temporary_proximity(possible_similar) is exceed_hours

    @pytest.mark.parametrize("similarity_meters,set_ubications,etrs89a,etrs89a2,exceed_meters", (
            (2000, True, (427236.69, 4582247.42), (426053.09, 4583681.06), False),
            (1000, True, (427236.69, 4582247.42), (426053.09, 4583681.06), True),
            (1000, False, (427236.69, 4582247.42), (426053.09, 4583681.06), True),
            (2000, True, (None, 4582247.42), (426053.09, 4583681.06), True),
            (2000, True, (427236.69, None), (426053.09, 4583681.06), True),
            (2000, True, (427236.69, 4582247.42), (None, 4583681.06), True),
            (2000, True, (427236.69, 4582247.42), (426053.09, None), True),
    ))
    def test_exceed_meters_proximity(self, similarity_meters, set_ubications, etrs89a, etrs89a2, exceed_meters):
        element_detail = self.create_element_detail(similarity_meters=similarity_meters,
                                                    fill_active_mandatory_fields=False)

        if set_ubications:
            ubication = Ubication.objects.create(via_type="carrer", street="carrer", xetrs89a=etrs89a[0],
                                                 yetrs89a=etrs89a[1])
            ubication2 = Ubication.objects.create(via_type="test", street="test", xetrs89a=etrs89a2[0],
                                                  yetrs89a=etrs89a2[1])
        else:
            ubication = None
            ubication2 = None

        record_card = self.create_record_card(element_detail=element_detail, ubication=ubication)
        possible_similar = self.create_record_card(element_detail=element_detail, ubication=ubication2)

        assert record_card.exceed_meters_proximity(possible_similar) is exceed_meters

    @pytest.mark.parametrize(
        "similar_state,same_element_detail,same_ambit_responsible,exceed_hours,exceed_meters,records_are_similar", (
                (RecordState.IN_RESOLUTION, True, True, False, False, True),
                (RecordState.IN_RESOLUTION, False, True, False, False, False),
                (RecordState.IN_RESOLUTION, True, False, False, False, False),
                (RecordState.IN_RESOLUTION, True, True, True, False, False),
                (RecordState.PENDING_VALIDATE, True, True, False, False, False),
                (RecordState.EXTERNAL_RETURNED, True, True, False, False, False),
                (RecordState.IN_RESOLUTION, True, True, False, True, False),
                (RecordState.CLOSED, True, True, False, False, False),
        ))
    def test_check_similarity(self, similar_state, same_element_detail, same_ambit_responsible, exceed_hours,
                              exceed_meters, records_are_similar):
        grand_parent, parent, first_soon, second_soon, noambit_parent, noambit_soon = create_groups()

        similarity_meters = 1000 if exceed_meters else 5000
        element_detail = self.create_element_detail(similarity_hours=5, similarity_meters=similarity_meters,
                                                    fill_active_mandatory_fields=False)

        ubication = Ubication.objects.create(via_type="carrer", street="test", xetrs89a=427236.69, yetrs89a=4582247.42)
        record_card = self.create_record_card(responsible_profile=second_soon, element_detail=element_detail,
                                              ubication=ubication)

        possible_similar_element_detail = record_card.element_detail if same_element_detail else None
        possible_similar_responsible = parent if same_ambit_responsible else noambit_parent
        possible_ubication = Ubication.objects.create(via_type="carrer", street="test", xetrs89a=426053.09,
                                                      yetrs89a=4583681.06)
        possible_similar = self.create_record_card(element_detail=possible_similar_element_detail,
                                                   responsible_profile=possible_similar_responsible,
                                                   record_state_id=similar_state, ubication=possible_ubication)
        if exceed_hours:
            possible_similar.created_at += timedelta(hours=10)

        assert record_card.check_similarity(possible_similar, self.user) is records_are_similar

    @pytest.mark.parametrize("has_permission,same_ambit_responsible,records_are_similar", (
            (True, True, True),
            (True, False, True),
            (False, True, True),
            (False, False, False),
    ))
    def test_check_similarity_ambit_permission(self, has_permission, same_ambit_responsible, records_are_similar):
        grand_parent, parent, first_soon, second_soon, noambit_parent, noambit_soon = create_groups()

        element_detail = self.create_element_detail(similarity_hours=5, similarity_meters=5000,
                                                    fill_active_mandatory_fields=False)

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

        assert record_card.check_similarity(possible_similar, self.user) is records_are_similar

    @pytest.mark.parametrize("similar_records,other_records", ((0, 0), (0, 1), (1, 0), (1, 1), (3, 3), (5, 3), (2, 10)))
    def test_get_possible_similar_records(self, similar_records, other_records):
        _, _, _, second_soon, _, _ = create_groups()
        element_detail = self.create_element_detail(similarity_hours=5, similarity_meters=5000)

        ubication = Ubication.objects.create(via_type="carrer", street="test", xetrs89a=427236.69, yetrs89a=4582247.42)
        record_card = self.create_record_card(responsible_profile=second_soon, element_detail=element_detail,
                                              ubication=ubication)
        for _ in range(similar_records):
            self.create_record_card(element_detail=record_card.element_detail, record_state_id=RecordState.IN_PLANING,
                                    responsible_profile=record_card.responsible_profile, ubication=ubication)
        for _ in range(other_records):
            self.create_record_card()

        assert len(record_card.get_possible_similar_records()) == similar_records

    @pytest.mark.parametrize("similar_records,other_records", ((0, 0), (0, 1), (1, 0), (1, 1), (3, 3), (5, 3), (2, 10)))
    def test_set_similar_records(self, similar_records, other_records):
        _, _, _, second_soon, _, _ = create_groups()
        element_detail = self.create_element_detail(similarity_hours=5, similarity_meters=5000)

        ubication = Ubication.objects.create(via_type="carrer", street="test", xetrs89a=427236.69, yetrs89a=4582247.42)
        record_card = self.create_record_card(responsible_profile=second_soon, element_detail=element_detail,
                                              ubication=ubication)
        similars_ids = [
            self.create_record_card(element_detail=record_card.element_detail, record_state_id=RecordState.IN_PLANING,
                                    responsible_profile=record_card.responsible_profile, ubication=ubication).pk
            for _ in range(similar_records)]

        for _ in range(other_records):
            self.create_record_card()

        record_card.set_similar_records()
        record_card = RecordCard.objects.get(pk=record_card.pk)

        assert record_card.possible_similar.count() == similar_records
        possible_similar_records = True if similar_records else False
        assert record_card.possible_similar_records is possible_similar_records
        assert record_card.alarm is possible_similar_records

        if similar_records:
            for similar in RecordCard.objects.filter(pk__in=similars_ids):
                assert similar.possible_similar_records is possible_similar_records

    @pytest.mark.parametrize("only_ambit,group_is_ambit,group_can_answer", (
            (True, True, True),
            (True, False, False),
            (False, True, True),
            (False, False, True),
    ))
    def test_group_can_answer(self, only_ambit, group_is_ambit, group_can_answer):
        _, parent, _, _, _, _ = create_groups()
        record_card = self.create_record_card(responsible_profile=parent)
        if only_ambit:
            record_card.claims_number = 10
            record_card.save()
        group = mommy.make(Group, is_ambit=group_is_ambit, user_id='2222', profile_ctrl_user_id='2222')

        can_answer = record_card.group_can_answer(group)
        assert can_answer['can_answer'] is group_can_answer
        if not can_answer['can_answer']:
            assert "reason" in can_answer

    @pytest.mark.parametrize("claims_number,old_response_days,only_ambit", (
            (3, 0, False), (5, 0, True), (3, 100, True), (5, 80, True), (2, 80, False)
    ))
    def test_only_answer_ambit_coordinators(self, claims_number, old_response_days, only_ambit):
        Parameter.objects.filter(parameter='FITXES_PARE_RESPOSTA').update(valor=5)
        Parameter.objects.filter(parameter='DIES_ANTIGUITAT_RESPOSTA').update(valor=90)
        record_card = self.create_record_card()
        if claims_number:
            record_card.claims_number = claims_number
            record_card.save()
        if old_response_days:
            record_card.created_at = record_card.created_at - timedelta(days=old_response_days)

        only_answer_coordinators = record_card.only_answer_ambit_coordinators()
        assert only_answer_coordinators['only_coordinators'] is only_ambit
        if only_answer_coordinators['only_coordinators']:
            assert "reason" in only_answer_coordinators

    @pytest.mark.parametrize("record_state_id,previous_created_at,has_permission,has_expired", (
            (RecordState.PENDING_VALIDATE, False, True, False),
            (RecordState.PENDING_VALIDATE, True, False, True),
            (RecordState.EXTERNAL_RETURNED, False, False, False),
            (RecordState.EXTERNAL_RETURNED, True, True, True),
            (RecordState.PENDING_ANSWER, False, False, False),
            (RecordState.PENDING_ANSWER, True, True, False),
    ))
    def test_has_expired(self, record_state_id, previous_created_at, has_permission, has_expired):
        record_card = self.create_record_card(record_state_id=record_state_id, previous_created_at=previous_created_at)
        if has_permission:
            self.set_group_permissions("usre_id", record_card.responsible_profile, [RECARD_COORDINATOR_VALIDATION_DAYS])
        assert record_card.has_expired(record_card.responsible_profile) is has_expired

    @pytest.mark.parametrize("responsible_profile, user_group, can_tramit", (
            (0, 0, True), (0, 1, False), (0, 2, False), (0, 3, False), (0, 4, False), (0, 5, False),
            (1, 0, True), (1, 1, True), (1, 2, False), (1, 3, False), (1, 4, False), (1, 5, False),
            (2, 0, True), (2, 1, True), (2, 2, True), (2, 3, False), (2, 4, False), (2, 5, False),
            (3, 0, True), (3, 1, True), (3, 2, False), (3, 3, True), (3, 4, False), (3, 5, False),
            (4, 0, True), (4, 1, False), (4, 2, False), (4, 3, False), (4, 4, True), (4, 5, False),
            (5, 0, True), (5, 1, False), (5, 2, False), (5, 3, False), (5, 4, True), (5, 5, True),
    ))
    def test_group_can_tramit_record(self, responsible_profile, user_group, can_tramit):
        grand_parent, parent, first_soon, second_soon, noambit_parent, noambit_soon = create_groups()
        groups = {
            0: grand_parent,
            1: parent,
            2: first_soon,
            3: second_soon,
            4: noambit_parent,
            5: noambit_soon
        }
        record_card = self.create_record_card(responsible_profile=groups[responsible_profile])
        assert record_card.group_can_tramit_record(groups[user_group]) is can_tramit

    def test_set_close_data(self):
        close_department = "test_department"
        record_card = self.create_record_card()
        record_card.set_close_data(close_department, self.user)
        assert record_card.closing_date
        assert record_card.close_department == close_department
        assert record_card.recordcardaudit.close_user

    @pytest.mark.parametrize("create_previous", (True, False))
    def test_get_record_audit(self, create_previous):
        previous_audit_pk = None
        record_card = self.create_record_card()
        if create_previous:
            previous_audit_pk = RecordCardAudit.objects.create(record_card=record_card).pk

        audit = record_card.get_record_audit()
        assert audit
        assert hasattr(record_card, "recordcardaudit")
        if create_previous:
            assert audit.pk == previous_audit_pk

    def test_register_audit_field(self):
        record_card = self.create_record_card()
        audit_field = "planif_user"
        audit_value = "test"
        record_card.register_audit_field(audit_field, audit_value)
        record_card = RecordCard.objects.get(pk=record_card.pk)
        assert hasattr(record_card, "recordcardaudit")
        assert getattr(record_card.recordcardaudit, audit_field) == audit_value

    def test_close_record_conversations(self):
        record_card = self.create_record_card(applicant_response=True, pend_applicant_response=True,
                                              response_to_responsible=True, pend_response_responsible=True,
                                              response_time_expired=True)
        record_card.close_record_conversations()
        record_card = RecordCard.objects.get(pk=record_card.pk)
        assert record_card.applicant_response is True
        assert record_card.pend_applicant_response is True
        assert record_card.response_to_responsible is False
        assert record_card.pend_response_responsible is False
        assert record_card.response_time_expired is True

    def test_set_ans_limits(self):
        element_detail = self.create_element_detail(sla_hours=24)
        record_card = self.create_record_card(element_detail=element_detail)
        assert record_card.ans_limit_date
        assert record_card.ans_limit_nearexpire
        assert record_card.ans_limit_nearexpire < record_card.ans_limit_date

    def test_not_is_claimed(self):
        record_card = self.create_record_card()
        record_card.update_claims_number()
        assert not record_card.is_claimed

    def test_is_claimed(self):
        record_card = self.create_record_card()
        claim = record_card.create_record_claim("user_id", "claim_description")
        claim.update_claims_number()

        record_card = RecordCard.objects.get(pk=record_card.pk)
        assert record_card.is_claimed
        assert not claim.is_claimed

    def test_claim_num(self):
        record_card = self.create_record_card()
        claim = record_card.create_record_claim("user_id", "claim_description")
        claim.update_claims_number()

        record_card = RecordCard.objects.get(pk=record_card.pk)
        assert record_card.claim_num == "-02"
        assert claim.claim_num == "-02"

    @pytest.mark.parametrize("claims", (1, 3, 5))
    def test_get_last_claim(self, claims):
        record_card = self.create_record_card()
        record_to_claim = record_card
        for i in range(claims):
            record_to_claim = record_to_claim.create_record_claim("user_id", "claim_description")
            record_to_claim.update_claims_number()

        record_card = RecordCard.objects.get(pk=record_card.pk)
        last_claim = record_card.get_last_claim()
        assert last_claim.normalized_record_id == "{}-0{}".format(record_card.normalized_record_id, claims + 1)

    def test_days_in_ambit_reasignation(self):
        load_missing_data_districts()
        load_missing_data_reasons()
        dair, parent, first_soon, _, _, _ = create_groups()
        add_extra_group_level(first_soon)
        record_card = self.create_record_card(responsible_profile=parent)
        reasing = RecordCardReasignation.objects.create(record_card=record_card, group=dair,
                                                        previous_responsible_profile=dair,
                                                        next_responsible_profile=parent,
                                                        reason_id=Reason.COORDINATOR_EVALUATION)
        reasing.created_at -= timedelta(days=7)
        reasing.save()
        assert record_card.days_in_ambit == 7

    def test_days_in_ambit_no_reasignation(self):
        record_card = self.create_record_card(previous_created_at=True)
        assert record_card.days_in_ambit == 365

    @pytest.mark.parametrize("record_state,expected_result", (
            (RecordState.PENDING_VALIDATE, True),
            (RecordState.EXTERNAL_RETURNED, True),
            (RecordState.PENDING_ANSWER, False),
            (RecordState.CLOSED, False),
    ))
    def test_record_can_be_autovalidated_states(self, record_state, expected_result):
        element_detail = self.create_element_detail(autovalidate_records=True)
        record_card = self.create_record_card(record_state_id=record_state, element_detail=element_detail)
        assert record_card.record_can_be_autovalidated() is expected_result

    @pytest.mark.parametrize("autovalidate_records,expected_result", (
            (True, True),
            (False, False),
    ))
    def test_record_can_be_autovalidated_detail(self, autovalidate_records, expected_result):
        element_detail = self.create_element_detail(autovalidate_records=autovalidate_records)
        record_card = self.create_record_card(record_state_id=RecordState.PENDING_VALIDATE,
                                              element_detail=element_detail)
        assert record_card.record_can_be_autovalidated() is expected_result

    @pytest.mark.parametrize("autovalidate_records,expected_result", (
            (True, True),
            (False, False),
    ))
    def test_record_can_be_autovalidated_newdetail(self, autovalidate_records, expected_result):
        element_detail = self.create_element_detail(autovalidate_records=autovalidate_records)
        record_card = self.create_record_card(record_state_id=RecordState.PENDING_VALIDATE)
        assert record_card.record_can_be_autovalidated(element_detail) is expected_result

    @pytest.mark.parametrize("remove_applicant,expected_result", (
            (False, True),
            (True, False),
    ))
    def test_record_can_be_autovalidated_applicant(self, remove_applicant, expected_result):
        element_detail = self.create_element_detail(autovalidate_records=True)
        record_card = self.create_record_card(record_state_id=RecordState.PENDING_VALIDATE,
                                              element_detail=element_detail)
        if remove_applicant:
            record_card.request.applicant = None
            record_card.request.save()

        assert record_card.record_can_be_autovalidated() is expected_result

    def test_autovalidate_record(self):
        element_detail = self.create_element_detail(autovalidate_records=True)
        record_card = self.create_record_card(record_state_id=RecordState.PENDING_VALIDATE,
                                              element_detail=element_detail)
        get_external_validator = Mock(return_value=None)
        with patch('record_cards.models.get_external_validator', get_external_validator):
            assert not record_card.autovalidate_record('', self.user)
            record_card = RecordCard.objects.get(pk=record_card.pk)
            assert record_card.record_state_id == RecordState.CLOSED

    def test_autovalidate_record_external_validator_support_autovalidation(self):
        element_detail = self.create_element_detail(autovalidate_records=True)
        record_card = self.create_record_card(record_state_id=RecordState.PENDING_VALIDATE,
                                              element_detail=element_detail)
        external_validator = DummyExternalValidator(record_card)
        get_external_validator = Mock(return_value=external_validator)
        with patch('record_cards.models.get_external_validator', get_external_validator):
            assert not record_card.autovalidate_record('', self.user)
            record_card = RecordCard.objects.get(pk=record_card.pk)
            assert record_card.record_state_id == RecordState.CLOSED

    def test_autovalidate_record_external_validator_fails(self):
        load_missing_data_reasons()
        element_detail = self.create_element_detail(autovalidate_records=True)
        record_card = self.create_record_card(record_state_id=RecordState.PENDING_VALIDATE,
                                              element_detail=element_detail)
        external_validator = DummyExternalValidatorNotValidate(record_card)
        get_external_validator = Mock(return_value=external_validator)
        with patch('record_cards.models.get_external_validator', get_external_validator):
            with patch('record_cards.models.RecordCard.validate') as mock_validate:
                assert not record_card.autovalidate_record('', self.user)
                mock_validate.assert_not_called()
                record_card = RecordCard.objects.get(pk=record_card.pk)
                assert record_card.record_state_id == RecordState.PENDING_VALIDATE
                assert Comment.objects.filter(record_card_id=record_card.pk, reason_id=Reason.OBSERVATION).exists()


@pytest.mark.django_db
class TestUbication:

    @pytest.mark.parametrize("xetrs89a,yetrs89a,expected_result", (
            (427236.69, 4582247.42, (41.38846686717844, -9.870309797208614)),
            (None, 4582247.42, None),
            (427236.69, None, None),
    ))
    def test_etrs_to_location(self, xetrs89a, yetrs89a, expected_result):
        ubication = Ubication.objects.create(via_type="carrer", street="carrer", xetrs89a=xetrs89a, yetrs89a=yetrs89a)
        assert ubication.etrs_to_latlon == expected_result

    @pytest.mark.parametrize("xetrs89a1,yetrs89a1,xetrs89a2,yetrs89a2,expected_result", (
            (427236.69, 4582247.42, 426053.09, 4583681.06, 1859.71544),
            (None, 4582247.42, 426053.09, 4583681.06, None),
            (427236.69, None, 426053.09, 4583681.06, None),
            (427236.69, 4582247.42, None, 4583681.06, None),
            (427236.69, 4582247.42, 426053.09, None, None),
    ))
    def test_distance(self, xetrs89a1, yetrs89a1, xetrs89a2, yetrs89a2, expected_result):
        ubication = Ubication.objects.create(via_type="carrer", street="carrer", xetrs89a=xetrs89a1, yetrs89a=yetrs89a1)
        ubication2 = Ubication.objects.create(via_type="test", street="test", xetrs89a=xetrs89a2, yetrs89a=yetrs89a2)
        distance = ubication.distance(ubication2)
        if distance:
            distance = round(distance, 5)
        assert distance == expected_result


@pytest.mark.django_db
class TestApplicantModel(CreateRecordCardMixin):

    def test_save_applicant_response(self):
        citizen = mommy.make(Citizen, user_id='222222')
        applicant = mommy.make(Applicant, user_id='22222', citizen=citizen)
        record_card = self.create_record_card(create_record_card_response=True, applicant=applicant)
        recordcard_response = record_card.recordcardresponse
        applicant_response = applicant.save_applicant_response(recordcard_response)

        assert applicant_response.language == recordcard_response.language
        assert applicant_response.email == recordcard_response.address_mobile_email
        assert applicant_response.response_channel_id == recordcard_response.response_channel_id
        assert applicant_response.street_type == recordcard_response.via_type
        if record_card.recordcardresponse.response_channel == ResponseChannel.LETTER:
            assert applicant_response.street == recordcard_response.address_mobile_email
        assert applicant_response.number == recordcard_response.number
        assert applicant_response.floor == recordcard_response.floor
        assert applicant_response.door == recordcard_response.door
        assert applicant_response.door == recordcard_response.door
        assert applicant_response.scale == recordcard_response.stair
        assert applicant_response.postal_code == recordcard_response.postal_code
        assert applicant_response.municipality == recordcard_response.municipality
        assert applicant_response.province == recordcard_response.province

    def test_no_save_applicant_response_english(self):
        citizen = mommy.make(Citizen, user_id='222222')
        applicant = mommy.make(Applicant, user_id='22222', citizen=citizen)
        record_card = self.create_record_card(create_record_card_response=True, applicant=applicant)
        record_card.recordcardresponse.language = ENGLISH
        record_card.recordcardresponse.save()
        applicant_response = applicant.save_applicant_response(record_card.recordcardresponse)
        assert applicant_response is None

    def test_save_applicant_response_nd(self):
        citizen = mommy.make(Citizen, user_id='222222', dni='ND')
        applicant = mommy.make(Applicant, user_id='22222', citizen=citizen)
        record_card = self.create_record_card(create_record_card_response=True, applicant=applicant)
        recordcard_response = record_card.recordcardresponse
        assert applicant.save_applicant_response(recordcard_response) is None

    def test_can_be_anonymized_social_entity(self):
        social_entity = mommy.make(SocialEntity, user_id='222222')
        applicant = mommy.make(Applicant, user_id='22222', social_entity=social_entity)
        assert applicant.can_be_anonymized is False

    def test_can_be_anonymized_citizen_norecords(self):
        citizen = mommy.make(Citizen, user_id='222222', dni='ND')
        applicant = mommy.make(Applicant, user_id='22222', citizen=citizen)
        assert applicant.can_be_anonymized is True

    @pytest.mark.parametrize("record_state_id,anonymized", (
            (RecordState.PENDING_VALIDATE, False), (RecordState.CLOSED, True)
    ))
    def test_can_be_anonymized_citizen_withrecords(self, record_state_id, anonymized):
        citizen = mommy.make(Citizen, user_id='222222', dni='ND')
        applicant = mommy.make(Applicant, user_id='22222', citizen=citizen)
        self.create_record_card(applicant=applicant, record_state_id=record_state_id)
        assert applicant.can_be_anonymized is anonymized

    def test_anonymize_social_entity(self):
        social_entity = mommy.make(SocialEntity, user_id='222222')
        applicant = mommy.make(Applicant, user_id='22222', social_entity=social_entity)
        applicant.anonymize()
        assert applicant.pend_anonymize is False

    def test_anonymize_citizen_norecords(self):
        citizen = mommy.make(Citizen, user_id='222222', dni='ND')
        applicant = mommy.make(Applicant, user_id='22222', citizen=citizen)
        applicant.anonymize()
        applicant = Applicant.objects.get(id=applicant.pk)
        assert applicant.pend_anonymize is False

    @pytest.mark.parametrize("record_state_id,pend_anonymize", (
            (RecordState.PENDING_VALIDATE, True),
            (RecordState.CLOSED, False)
    ))
    def test_anonymize_citizen_withrecords(self, record_state_id, pend_anonymize):
        citizen = mommy.make(Citizen, user_id='222222', dni='ND')
        applicant = mommy.make(Applicant, user_id='22222', citizen=citizen)
        self.create_record_card(applicant=applicant, record_state_id=record_state_id)
        applicant.anonymize()
        applicant = Applicant.objects.get(id=applicant.pk)
        assert applicant.pend_anonymize is pend_anonymize


@pytest.mark.django_db
class TestCitizenModel(CreateRecordCardMixin):

    def test_can_be_anonymized_norecords(self):
        citizen = mommy.make(Citizen, user_id='222222', dni='ND')
        mommy.make(Applicant, user_id='22222', citizen=citizen)
        assert citizen.can_be_anonymized is True

    @pytest.mark.parametrize("record_state_id,anonymized", (
            (RecordState.PENDING_VALIDATE, False), (RecordState.CLOSED, True)
    ))
    def test_can_be_anonymized_withrecords(self, record_state_id, anonymized):
        citizen = mommy.make(Citizen, user_id='222222', dni='ND')
        applicant = mommy.make(Applicant, user_id='22222', citizen=citizen)
        self.create_record_card(applicant=applicant, record_state_id=record_state_id)
        assert citizen.can_be_anonymized is anonymized


@pytest.mark.django_db
class TestWorkflow(CreateRecordCardMixin):

    @pytest.mark.parametrize("initial_state_id,unclosed_records", (
            (RecordState.PENDING_ANSWER, True),
            (RecordState.CLOSED, False),
            (RecordState.CANCELLED, False),
            (RecordState.IN_RESOLUTION, True),
    ))
    def test_unclosed_records(self, initial_state_id, unclosed_records):
        record_card = self.create_record_card(initial_state_id, create_worflow=True)
        assert record_card.workflow.unclosed_records == unclosed_records

    def test_close_workflow(self):
        record_card = self.create_record_card(create_worflow=True)
        workflow = record_card.workflow
        workflow.close()
        assert workflow.state_id == RecordState.CLOSED
        assert workflow.close_date

    @pytest.mark.parametrize("initial_state_id,expected_state_id", (
            (RecordState.PENDING_ANSWER, RecordState.PENDING_ANSWER),
            (RecordState.CLOSED, RecordState.CLOSED)
    ))
    def test_state_change(self, initial_state_id, expected_state_id):
        record_card = self.create_record_card(initial_state_id, create_worflow=True)
        workflow = record_card.workflow
        workflow.state_id = RecordState.IN_RESOLUTION
        workflow.save()

        workflow.state_change(RecordState.PENDING_ANSWER)
        assert workflow.state_id == expected_state_id


@pytest.mark.django_db
class TestRecordCardTextResponse(CreateRecordCardMixin, CreateRecordFileMixin):

    @pytest.mark.parametrize("num_files", (0, 1, 5))
    def test_enabled_record_files(self, tmpdir_factory, num_files):
        record_card = self.create_record_card(create_record_card_response=True)
        record_card_text_response = mommy.make(RecordCardTextResponse, user_id="222", record_card=record_card)
        files = [self.create_file(tmpdir_factory, record_card, num_file) for num_file in range(num_files)]
        for file in files:
            RecordCardTextResponseFiles.objects.create(text_response=record_card_text_response, record_file=file)
        assert len(record_card_text_response.enabled_record_files) == num_files
