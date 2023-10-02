class RecordCardAlarms:
    """
    Class to identify the alarms of a RecordCard
    """

    def __init__(self, record_card, group) -> None:
        self.record_card = record_card
        self.group = group
        super().__init__()

    @property
    def alarms(self):
        return {
            "mayorship": self.mayorship_alarm,
            "urgent": self.urgent_alarm,
            "pend_citizen_response": self.pend_citizen_response_alarm,
            "response_time_expired": self.response_time_expired_alarm,
            "citizen_response": self.citizen_response_alarm,
            "reasigned_task": self.reasigned_task_alarm,
            "citizen_claim": self.citizen_claim_alarm,
            "citizen_web_claim": self.citizen_claim_web_alarm,
            "related_records": self.related_records_alarm,
            "cancel_request": self.cancel_request_alarm,
            "possible_similar_records": self.possible_similar_records_alarm,
            "response_to_responsible": self.response_to_responsible,
            "pend_response_responsible": self.pend_response_responsible
        }

    @property
    def mayorship_alarm(self):
        return self.record_card.mayorship

    @property
    def urgent_alarm(self):
        return self.record_card.urgent

    @property
    def pend_citizen_response_alarm(self):
        return self.record_card.pend_applicant_response

    @property
    def response_time_expired_alarm(self):
        return self.record_card.response_time_expired

    @property
    def citizen_response_alarm(self):
        return self.record_card.applicant_response

    @property
    def citizen_claim_alarm(self):
        return self.record_card.citizen_alarm

    @property
    def citizen_claim_web_alarm(self):
        return self.record_card.citizen_web_alarm

    @property
    def related_records_alarm(self):
        return self.record_card.similar_process

    @property
    def cancel_request_alarm(self):
        return self.record_card.cancel_request

    @property
    def reasigned_task_alarm(self):
        return self.record_card.reasigned

    @property
    def possible_similar_records_alarm(self):
        return self.record_card.possible_similar_records

    @property
    def response_to_responsible(self):
        return self.record_card.response_to_responsible and self.record_card.group_can_open_conversation(self.group)

    @property
    def pend_response_responsible(self):
        return self.record_card.pend_response_responsible and self.record_card.group_can_open_conversation(self.group)

    def check_alarms(self, alarm_pop_keys=None):
        """
        :param alarm_pop_keys: If is set, allows to check all the alarms except the indicateds
        :return: True if any alarm is activated, else False
        """
        alarms = self.alarms
        if alarm_pop_keys:
            for alarm_pop_key in alarm_pop_keys:
                alarms.pop(alarm_pop_key, None)

        for alarm, value in alarms.items():
            if value:
                return True
        return False
