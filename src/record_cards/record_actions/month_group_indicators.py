from calendar import monthrange
from datetime import datetime, timedelta


from django.db.models import OuterRef, Subquery, Avg, F, Q
from django.db.models.functions import Coalesce

from iris_masters.models import RecordState
from profiles.models import Group
from record_cards.models import RecordCardStateHistory, RecordCardReasignation, RecordCard, MonthIndicator


class MonthGroupIndicators:
    """
    Class to calculate the month group indicataors, giving a year and a month
    """

    def __init__(self, year, month) -> None:
        self.year = year
        self.month = month
        self.set_dates_limits()
        super().__init__()

    def set_dates_limits(self):
        self.date_limit = datetime(self.year, self.month, 1)
        last_month_day = monthrange(self.year, self.month)[1]
        self.month_limit = datetime(self.year, self.month, last_month_day) + timedelta(days=1)

    def register_month_indicators(self):
        """
        Get all the no anonymous groups and calculate its indicators for the (year,month) of the class

        :return:
        """
        groups = Group.objects.filter(is_anonymous=False, deleted__isnull=True)
        for group in groups:
            self.register_group_indicators(group)

    def register_group_indicators(self, group):
        """
        Giving a group get the records, calculate the month indicators and save it to the dabase

        :param group: group to calculate the month indicators
        :return:
        """
        records = self.get_group_records(group)
        average_close_days = self.calculate_average_close_days(records)
        average_age_days = self.calculate_average_age_days(records)
        num_entries_records = self.calculate_entries_records(records, group)
        indicators_dict = self.set_indicators(records, average_close_days, average_age_days, num_entries_records)
        self.save_group_indicators(indicators_dict, group)

    def get_group_records(self, group) -> list:
        """
        Get the record that the group owns on the indicated (month,year)

        :param group: group to get the records
        :return: Records that the group owns on the indicated (month,year)
        """
        month_state_histories = self.get_states_histories()
        record_reasignations = self.get_record_reasignations()
        entries_reasignations = self.get_entries_reasignations()

        records = RecordCard.objects.filter(
            Q(closing_date__isnull=True) | Q(closing_date__gte=self.date_limit)).annotate(
            temp_state=Coalesce(Subquery(month_state_histories.values("next_state_id")), "record_state_id"),
            last_state_created_at=Subquery(month_state_histories.values("created_at")),
            temp_group=Coalesce(Subquery(record_reasignations.values("next_responsible_profile_id")),
                                "responsible_profile_id"),
            entry_group=Subquery(entries_reasignations.values("next_responsible_profile_id")),
        ).values("temp_state", "last_state_created_at", "created_at", "temp_group", "entry_group")

        return records.filter(temp_group=group.pk)

    def get_states_histories(self):
        """
        Get the last state change of each record card

        :return: Queryset of the last state changes of each record card
        """
        return RecordCardStateHistory.objects.filter(
            created_at__lt=self.month_limit, record_card_id=OuterRef('pk')).order_by(
            "record_card_id", "-created_at").distinct("record_card_id")

    def get_record_reasignations(self):
        """
        Get the last record card reasignation of each record card

        :return: Queryset of last record card reasignation of each record card
        """
        return RecordCardReasignation.objects.filter(
            created_at__lt=self.month_limit, record_card_id=OuterRef('pk'),
        ).order_by("record_card_id", "-created_at").distinct("record_card_id")

    def get_entries_reasignations(self):
        """
        Get the last record card reasignation of each record card

        :return: Queryset of last record card reasignation of each record card
        """
        return RecordCardReasignation.objects.filter(
            created_at__lt=self.month_limit, created_at__gte=self.date_limit, record_card_id=OuterRef('pk'),
        ).order_by("record_card_id", "-created_at").distinct("record_card_id")

    def calculate_average_close_days(self, records) -> int:
        """
        Calculate the average of days to close records

        :param records: queryset of record for group
        :return:  Average of days to close records
        """
        average_close_days = records.filter(temp_state=RecordState.CLOSED).aggregate(
            close_days=Avg(F("last_state_created_at") - F("created_at")))
        return average_close_days["close_days"].days if average_close_days["close_days"] else 0

    def calculate_average_age_days(self, records) -> int:
        """
        Calculate the average age of open records on days

        :param records: queryset of record for group
        :return:  Average of days of open records
        """
        average_age_days = records.filter(
            temp_state__in=RecordState.STATES_IN_PROCESSING + RecordState.PEND_VALIDATE_STATES
        ).exclude(
            last_state_created_at__isnull=True
        ).aggregate(age_days=Avg(self.month_limit - F("created_at")))
        return average_age_days["age_days"].days if average_age_days["age_days"] else 0

    def calculate_entries_records(self, records, group) -> int:
        """
        Count records created for a group

        :param records: queryset of record for group
        :param group: group to get the records
        """
        return records.filter(entry_group=group.pk).count()

    def set_indicators(self, records, average_close_days, average_age_days, num_entries_records) -> dict:
        """
        Count the indicators of the month

        :param records: list of records owned by group at the indicted month-year pair
        :param average_close_days: Average of days used to close the records
        :param average_age_days: Average of days of records age
        :param num_entries_records: number of entries for group
        :return: indicators dict
        """
        indicators_dict = self.set_initial_indicators(average_close_days, average_age_days, num_entries_records)

        for rec in records:
            if rec["temp_state"] in RecordState.PEND_VALIDATE_STATES:
                indicators_dict["pending_validation"] += 1
                indicators_dict["pending_records"] += 1
            elif rec["temp_state"] in RecordState.STATES_IN_PROCESSING:
                indicators_dict["processing"] += 1
                indicators_dict["pending_records"] += 1
            elif rec["temp_state"] == RecordState.CLOSED:
                indicators_dict["closed"] += 1
            elif rec["temp_state"] == RecordState.CANCELLED:
                indicators_dict["cancelled"] += 1
            elif rec["temp_state"] == RecordState.EXTERNAL_PROCESSING:
                indicators_dict["external_processing"] += 1
                indicators_dict["pending_records"] += 1

        return indicators_dict

    def set_initial_indicators(self, average_close_days, average_age_days, num_entries_records) -> dict:
        """
        Set the initial structure of month indicators

        :param average_close_days: Average of days used to close the records
        :param average_age_days: Average of days of records age
        :param num_entries_records: Anumber of entries for group
        :return: initial indicators dict
        """
        return {
            "entries": num_entries_records,
            "pending_validation": 0,
            "processing": 0,
            "closed": 0,
            "cancelled": 0,
            "external_processing": 0,
            "pending_records": 0,
            "average_close_days": average_close_days,
            "average_age_days": average_age_days
        }

    def save_group_indicators(self, indicators_dict, group):
        """
        Save group indicators on the database, with the group and the indicated (month,year) pair

        :param indicators_dict: indicators dict from group
        :param group: group of indicatorss
        :return:
        """
        month_base_indicators = {"group": group, "year": self.year, "month": self.month}
        try:
            month_indicator = MonthIndicator.objects.get(**month_base_indicators)
            for attribute, value in indicators_dict.items():
                setattr(month_indicator, attribute, value)
            month_indicator.save()
        except MonthIndicator.DoesNotExist:
            indicators_dict.update(month_base_indicators)
            MonthIndicator.objects.create(**indicators_dict)
