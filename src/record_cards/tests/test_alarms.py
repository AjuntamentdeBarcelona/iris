import pytest
from model_mommy import mommy

from profiles.models import Group
from record_cards.record_actions.alarms import RecordCardAlarms
from record_cards.tests.utils import CreateRecordCardMixin


@pytest.mark.django_db
class TestRecordCardAlarms(CreateRecordCardMixin):

    @pytest.mark.parametrize("mayorship", (True, False))
    def test_mayorship_alarm(self, mayorship):
        record_card = self.create_record_card(mayorship=mayorship)
        assert RecordCardAlarms(record_card, record_card.responsible_profile).mayorship_alarm is mayorship

    @pytest.mark.parametrize("urgent", (True, False))
    def test_urgent_alarm(self, urgent):
        record_card = self.create_record_card(urgent=urgent)
        assert RecordCardAlarms(record_card, record_card.responsible_profile).urgent_alarm is urgent

    @pytest.mark.parametrize("pend_applicant_response", (True, False))
    def test_pend_applicant_response_alarm(self, pend_applicant_response):
        record_card = self.create_record_card(pend_applicant_response=pend_applicant_response)
        assert RecordCardAlarms(record_card,
                                record_card.responsible_profile).pend_citizen_response_alarm is pend_applicant_response

    @pytest.mark.parametrize("applicant_response", (True, False))
    def test_applicant_response_alarm(self, applicant_response):
        record_card = self.create_record_card(applicant_response=applicant_response)
        assert RecordCardAlarms(record_card,
                                record_card.responsible_profile).citizen_response_alarm is applicant_response

    @pytest.mark.parametrize("response_time_expired", (True, False))
    def test_response_time_expired_alarm(self, response_time_expired):
        record_card = self.create_record_card(response_time_expired=response_time_expired)
        assert RecordCardAlarms(record_card,
                                record_card.responsible_profile).response_time_expired_alarm is response_time_expired

    @pytest.mark.parametrize("citizen_alarm", (True, False))
    def test_citizen_claim_alarm(self, citizen_alarm):
        record_card = self.create_record_card()
        if citizen_alarm:
            record_card.citizen_alarm = citizen_alarm
            record_card.save()
        assert RecordCardAlarms(record_card, record_card.responsible_profile).citizen_claim_alarm is citizen_alarm

    @pytest.mark.parametrize("citizen_web_alarm", (True, False))
    def test_citizen_claim_web_alarm(self, citizen_web_alarm):
        record_card = self.create_record_card()
        if citizen_web_alarm:
            record_card.citizen_web_alarm = citizen_web_alarm
            record_card.save()
        assert RecordCardAlarms(record_card,
                                record_card.responsible_profile).citizen_claim_web_alarm is citizen_web_alarm

    @pytest.mark.parametrize("similar_process", (True, False))
    def test_related_records_alarm(self, similar_process):
        record_card = self.create_record_card(similar_process=similar_process)
        assert RecordCardAlarms(record_card, record_card.responsible_profile).related_records_alarm is similar_process

    @pytest.mark.parametrize("cancel_request", (True, False))
    def test_cancel_request_alarm(self, cancel_request):
        record_card = self.create_record_card(cancel_request=cancel_request)
        assert RecordCardAlarms(record_card, record_card.responsible_profile).cancel_request_alarm is cancel_request

    @pytest.mark.parametrize("reasigned", (True, False))
    def test_reasigned_task_alarm(self, reasigned):
        record_card = self.create_record_card(reasigned=reasigned)
        assert RecordCardAlarms(record_card, record_card.responsible_profile).reasigned_task_alarm is reasigned

    @pytest.mark.parametrize("possible_similar_records", (True, False))
    def test_possible_similar_records_alarm(self, possible_similar_records):
        record_card = self.create_record_card(possible_similar_records=possible_similar_records)
        assert RecordCardAlarms(
            record_card, record_card.responsible_profile).possible_similar_records_alarm is possible_similar_records

    @pytest.mark.parametrize("response_to_responsible,responsible_check", (
            (True, True),
            (True, False),
            (False, True),
            (False, False),
    ))
    def test_response_to_responsible(self, response_to_responsible, responsible_check):
        record_card = self.create_record_card(response_to_responsible=response_to_responsible)

        if response_to_responsible and responsible_check:
            assert RecordCardAlarms(
                record_card, record_card.responsible_profile).response_to_responsible is True
        else:
            group = mommy.make(Group, user_id="2134e23", profile_ctrl_user_id="asdadsa", group_plate="12334")
            assert RecordCardAlarms(
                record_card, group).response_to_responsible is False

    @pytest.mark.parametrize("pend_response_responsible,responsible_check", (
            (True, True),
            (True, False),
            (False, True),
            (False, False),
    ))
    def test_pend_response_responsible(self, pend_response_responsible, responsible_check):
        record_card = self.create_record_card(pend_response_responsible=pend_response_responsible)

        if pend_response_responsible and responsible_check:
            assert RecordCardAlarms(
                record_card, record_card.responsible_profile).pend_response_responsible is True
        else:
            group = mommy.make(Group, user_id="2134e23", profile_ctrl_user_id="asdadsa", group_plate="12334")
            assert RecordCardAlarms(
                record_card, group).pend_response_responsible is False

    @pytest.mark.parametrize(
        "mayorship,urgent,pend_applicant_response,applicant_response,response_time_expired,similar_process,reasigned,"
        "possible_similar_records,cancel_request,response_to_responsible,pend_response_responsible,citizen_alarm,"
        "citizen_web_alarm", (
                (False, False, False, False, False, False, False, False, False, False, False, False, False),
                (True, False, False, False, False, False, False, False, False, False, False, False, False),
                (False, True, False, False, False, False, False, False, False, False, False, False, False),
                (False, False, True, False, False, False, False, False, False, False, False, False, False),
                (False, False, False, True, False, False, False, False, False, False, False, False, False),
                (False, False, False, False, True, False, False, False, False, False, False, False, False),
                (False, False, False, False, False, True, False, False, False, False, False, False, False),
                (False, False, False, False, False, False, True, False, False, False, False, False, False),
                (False, False, False, False, False, False, False, True, False, False, False, False, False),
                (False, False, False, False, False, False, False, False, True, False, False, False, False),
                (False, False, False, False, False, False, False, False, False, True, False, False, False),
                (False, False, False, False, False, False, False, False, False, False, True, False, False),
                (False, False, False, False, False, False, False, False, False, False, False, True, False),
                (False, False, False, False, False, False, False, False, False, False, False, False, True)
        ))
    def test_basic_alarms(self, mayorship, urgent, pend_applicant_response, applicant_response, response_time_expired,
                          similar_process, reasigned, possible_similar_records, cancel_request, response_to_responsible,
                          pend_response_responsible, citizen_alarm, citizen_web_alarm):
        record_card = self.create_record_card(mayorship=mayorship, urgent=urgent,
                                              pend_applicant_response=pend_applicant_response,
                                              applicant_response=applicant_response,
                                              response_time_expired=response_time_expired,
                                              similar_process=similar_process, reasigned=reasigned,
                                              possible_similar_records=possible_similar_records,
                                              cancel_request=cancel_request,
                                              response_to_responsible=response_to_responsible,
                                              pend_response_responsible=pend_response_responsible)
        if citizen_alarm:
            record_card.citizen_alarm = citizen_alarm
            record_card.save()
        if citizen_web_alarm:
            record_card.citizen_web_alarm = citizen_web_alarm
            record_card.save()
        alarms = RecordCardAlarms(record_card, record_card.responsible_profile).alarms
        assert alarms["mayorship"] is mayorship
        assert alarms["urgent"] is urgent
        assert alarms["pend_citizen_response"] is pend_applicant_response
        assert alarms["citizen_response"] is applicant_response
        assert alarms["response_time_expired"] is response_time_expired
        assert alarms["related_records"] is similar_process
        assert alarms["cancel_request"] is cancel_request
        assert alarms["reasigned_task"] is reasigned
        assert alarms["possible_similar_records"] is possible_similar_records
        assert alarms["response_to_responsible"] is response_to_responsible
        assert alarms["citizen_claim"] is citizen_alarm
        assert alarms["citizen_web_claim"] is citizen_web_alarm

    @pytest.mark.parametrize(
        "mayorship,urgent,pend_applicant_response,applicant_response,response_time_expired,similar_process,reasigned,"
        "possible_similar_records,cancel_request,response_to_responsible,pend_response_responsible,citizen_alarm,"
        "citizen_web_alarm,exist_alarm", (
                (False, False, False, False, False, False, False, False, False, False, False, False, False, False),
                (True, False, False, False, False, False, False, False, False, False, False, False, False, True),
                (False, True, False, False, False, False, False, False, False, False, False, False, False, True),
                (False, False, True, False, False, False, False, False, False, False, False, False, False, True),
                (False, False, False, True, False, False, False, False, False, False, False, False, False, True),
                (False, False, False, False, True, False, False, False, False, False, False, False, False, True),
                (False, False, False, False, False, True, False, False, False, False, False, False, False, True),
                (False, False, False, False, False, False, True, False, False, False, False, False, False, True),
                (False, False, False, False, False, False, False, True, False, False, False, False, False, True),
                (False, False, False, False, False, False, False, False, True, False, False, False, False, True),
                (False, False, False, False, False, False, False, False, False, True, False, False, False, True),
                (False, False, False, False, False, False, False, False, False, False, True, False, False, True),
                (False, False, False, False, False, False, False, False, False, False, False, True, False, True),
                (False, False, False, False, False, False, False, False, False, False, False, False, True, True)
        ))
    def test_basic_check_alarms(self, mayorship, urgent, pend_applicant_response, applicant_response,
                                response_time_expired, similar_process, reasigned, possible_similar_records,
                                cancel_request, response_to_responsible, pend_response_responsible, citizen_alarm,
                                citizen_web_alarm, exist_alarm):
        record_card = self.create_record_card(mayorship=mayorship, urgent=urgent,
                                              pend_applicant_response=pend_applicant_response,
                                              applicant_response=applicant_response,
                                              response_time_expired=response_time_expired,
                                              similar_process=similar_process, reasigned=reasigned,
                                              possible_similar_records=possible_similar_records,
                                              cancel_request=cancel_request,
                                              response_to_responsible=response_to_responsible,
                                              pend_response_responsible=pend_response_responsible)
        if citizen_alarm:
            record_card.citizen_alarm = citizen_alarm
            record_card.save()
        if citizen_web_alarm:
            record_card.citizen_web_alarm = citizen_web_alarm
            record_card.save()
        assert RecordCardAlarms(record_card, record_card.responsible_profile).check_alarms() is exist_alarm
