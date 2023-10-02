import pytest
from model_mommy import mommy

from iris_masters.models import Reason
from profiles.models import Group
from record_cards.models import Comment, RecordCard
from record_cards.tests.utils import CreateRecordCardMixin
from themes.actions.theme_delete import ElementDetailDeleteAction
from themes.models import ElementDetailDeleteRegister
from communications.tests.utils import load_missing_data
from iris_masters.tests.utils import load_missing_data_process, load_missing_data_reasons


@pytest.mark.django_db
class TestElementDetailDeleteAction(CreateRecordCardMixin):

    @pytest.mark.parametrize("num_records", (0, 1, 3))
    def test_add_traceability_comments(self, num_records):
        load_missing_data()
        load_missing_data_process()
        load_missing_data_reasons()
        element_detail = self.create_element_detail()
        next_element_detail = self.create_element_detail()
        group = mommy.make(Group, user_id="wwwww", profile_ctrl_user_id="asdadsaa")
        elementdetail_delete_register = ElementDetailDeleteRegister.objects.create(
            group=group, deleted_detail=element_detail, reasignation_detail=next_element_detail)
        records_ids = [self.create_record_card(element_detail=element_detail).pk for _ in range(num_records)]
        delete_action = ElementDetailDeleteAction(elementdetail_delete_register=elementdetail_delete_register)

        delete_action._add_traceability_comments(records_ids)
        assert Comment.objects.filter(reason_id=Reason.THEME_DELETED).count() == num_records

    @pytest.mark.parametrize("num_records", (0, 1, 3))
    def test_record_cards_update_themes(self, num_records):
        load_missing_data()
        load_missing_data_process()
        load_missing_data_reasons()
        element_detail = self.create_element_detail()
        next_element_detail = self.create_element_detail()
        group = mommy.make(Group, user_id="wwwww", profile_ctrl_user_id="asdadsaa")
        elementdetail_delete_register = ElementDetailDeleteRegister.objects.create(
            group=group, deleted_detail=element_detail, reasignation_detail=next_element_detail)
        [self.create_record_card(element_detail=element_detail) for _ in range(num_records)]
        delete_action = ElementDetailDeleteAction(elementdetail_delete_register=elementdetail_delete_register)

        delete_action.record_cards_update_themes()
        assert RecordCard.objects.filter(element_detail_id=element_detail.pk).count() == 0
        assert RecordCard.objects.filter(element_detail_id=next_element_detail.pk).count() == num_records

    def test_elementdetail_postdelete_process(self):
        load_missing_data()
        load_missing_data_process()
        load_missing_data_reasons()
        element_detail = self.create_element_detail()
        next_element_detail = self.create_element_detail()
        group = mommy.make(Group, user_id="wwwww", profile_ctrl_user_id="asdadsaa")
        elementdetail_delete_register = ElementDetailDeleteRegister.objects.create(
            group=group, deleted_detail=element_detail, reasignation_detail=next_element_detail)
        [self.create_record_card(element_detail=element_detail) for _ in range(5)]
        delete_action = ElementDetailDeleteAction(elementdetail_delete_register=elementdetail_delete_register)

        delete_action.elementdetail_postdelete_process()
        elementdetail_delete_register = ElementDetailDeleteRegister.objects.get(pk=elementdetail_delete_register.pk)
        assert elementdetail_delete_register.process_finished is True
