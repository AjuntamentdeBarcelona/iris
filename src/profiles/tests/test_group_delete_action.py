import pytest
from model_mommy import mommy

from communications.models import Conversation
from communications.tests.utils import load_missing_data
from iris_masters.models import RecordState, Reason, Process
from iris_masters.tests.utils import load_missing_data_districts, load_missing_data_reasons
from profiles.group_delete import GroupDeleteAction
from profiles.models import GroupDeleteRegister
from profiles.tests.utils import create_groups
from record_cards.models import RecordCard, RecordCardReasignation
from record_cards.tests.utils import CreateDerivationsMixin, CreateRecordCardMixin
from themes.models import DerivationDirect, DerivationDistrict
from themes.tests.utils import CreateThemesMixin


@pytest.mark.django_db
class TestGroupDeleteAction(CreateDerivationsMixin, CreateRecordCardMixin, CreateThemesMixin):

    @pytest.mark.parametrize('model_class,expected_derivations_num', (
            (DerivationDirect, 3),
            (DerivationDistrict, 10)
    ))
    def test_derivations_reassign_by_model(self, model_class, expected_derivations_num):
        """
        Last case (DerivationDistrict, 10) uses BCN Districts (10 districts in total with derivation enabled)
        in order for this test to work, we load 10 districts with load_distr
        """
        load_missing_data()
        load_missing_data_districts()
        if not Process.objects.filter(id=0):
            process = Process(id=0)
            process.save()
        _, parent, first_soon, _, _, _ = create_groups()
        element_detail = self.create_element_detail()
        if model_class == DerivationDirect:
            self.create_direct_derivation(element_detail.pk, RecordState.IN_PLANING, first_soon)
            self.create_direct_derivation(element_detail.pk, RecordState.IN_RESOLUTION, first_soon)
            self.create_direct_derivation(element_detail.pk, RecordState.CLOSED, first_soon)
        else:
            self.create_district_derivation(element_detail.pk, RecordState.IN_RESOLUTION, first_soon)

        assert model_class.objects.filter(group=first_soon, enabled=True).count() == expected_derivations_num

        group_delete_register = GroupDeleteRegister.objects.create(user_id='222', deleted_group=first_soon,
                                                                   reasignation_group=parent, group=parent)

        GroupDeleteAction(group_delete_register).derivations_reassign_by_model(model_class)
        assert model_class.objects.filter(group=first_soon, enabled=True).count() == 0
        assert model_class.objects.filter(group=first_soon, enabled=False).count() == expected_derivations_num
        assert model_class.objects.filter(group=parent, enabled=True).count() == expected_derivations_num

    @pytest.mark.parametrize('records_opened,records_closed,only_open,expected_reassignations', (
            (3, 3, False, 6),
            (0, 3, False, 3),
            (4, 0, False, 4),
            (3, 3, True, 3),
            (0, 3, True, 0),
            (4, 0, True, 4),

    ))
    def test_record_cards_reassign(self, records_opened, records_closed, only_open, expected_reassignations):
        load_missing_data()
        load_missing_data_reasons()
        _, parent, first_soon, _, _, _ = create_groups()
        for _ in range(records_opened):
            record = self.create_record_card(responsible_profile=first_soon)
            mommy.make(Conversation, record_card=record, is_opened=True, external_email='test@test.com',
                       type=Conversation.INTERNAL, user_id='2222')

        for _ in range(records_closed):
            record = self.create_record_card(responsible_profile=first_soon, record_state_id=RecordState.CLOSED)
            mommy.make(Conversation, record_card=record, is_opened=True, external_email='test@test.com',
                       type=Conversation.INTERNAL, user_id='2222')

        group_delete_register = GroupDeleteRegister.objects.create(user_id='222', deleted_group=first_soon,
                                                                   reasignation_group=parent, group=parent,
                                                                   only_open=only_open)
        GroupDeleteAction(group_delete_register).record_cards_reassign()

        reassigned_records = RecordCard.objects.filter(responsible_profile_id=parent.pk)
        assert reassigned_records.count() == expected_reassignations
        if expected_reassignations:
            for record_card in reassigned_records:
                assert Conversation.objects.get(record_card=record_card, is_opened=False)
                assert record_card.responsible_profile == parent
                assert record_card.reasigned is True
                assert record_card.alarm is True
                assert RecordCardReasignation.objects.get(record_card=record_card, reason_id=Reason.GROUP_DELETED,
                                                          previous_responsible_profile=first_soon,
                                                          next_responsible_profile=parent, group=parent)

    @pytest.mark.parametrize('records_opened,records_closed,only_open,expected_reassignations', (
            (3, 3, False, 6),
            (0, 3, False, 3),
            (4, 0, False, 4),
            (3, 3, True, 3),
            (0, 3, True, 0),
            (4, 0, True, 4),
    ))
    def test_group_delete_process(self, records_opened, records_closed, only_open, expected_reassignations):
        load_missing_data()
        load_missing_data_districts()
        load_missing_data_reasons()
        _, parent, first_soon, _, _, _ = create_groups()
        element_detail = self.create_element_detail()
        self.create_derivations(element_detail, first_soon)
        for _ in range(records_opened):
            record = self.create_record_card(responsible_profile=first_soon, element_detail=element_detail)
            mommy.make(Conversation, record_card=record, is_opened=True, external_email='test@test.com',
                       type=Conversation.EXTERNAL, user_id='2222')

        for _ in range(records_closed):
            record = self.create_record_card(responsible_profile=first_soon, record_state_id=RecordState.CLOSED,
                                             element_detail=element_detail)
            mommy.make(Conversation, record_card=record, is_opened=True, external_email='test@test.com',
                       type=Conversation.EXTERNAL, user_id='2222')

        group_delete_register = GroupDeleteRegister.objects.create(user_id='222', deleted_group=first_soon,
                                                                   reasignation_group=parent, group=parent,
                                                                   only_open=only_open)
        GroupDeleteAction(group_delete_register).group_delete_process()

        reassigned_records = RecordCard.objects.filter(responsible_profile_id=parent.pk)
        assert reassigned_records.count() == expected_reassignations

        assert DerivationDirect.objects.filter(group=first_soon, enabled=True).count() == 0
        assert DerivationDirect.objects.filter(group=first_soon, enabled=False).count() == 3
        assert DerivationDirect.objects.filter(group=parent, enabled=True).count() == 3

        assert DerivationDistrict.objects.filter(group=first_soon, enabled=True).count() == 0
        assert DerivationDistrict.objects.filter(group=first_soon, enabled=False).count() == 10
        assert DerivationDistrict.objects.filter(group=parent, enabled=True).count() == 10

        group_delete_register = GroupDeleteRegister.objects.get(pk=group_delete_register.pk)
        assert group_delete_register.process_finished is True

    def create_derivations(self, element_detail, group):
        self.create_direct_derivation(element_detail.pk, RecordState.IN_PLANING, group)
        self.create_direct_derivation(element_detail.pk, RecordState.IN_RESOLUTION, group)
        self.create_direct_derivation(element_detail.pk, RecordState.CLOSED, group)
        self.create_district_derivation(element_detail.pk, RecordState.IN_RESOLUTION, group)
