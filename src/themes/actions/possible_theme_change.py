from iris_masters.models import Parameter, RecordState
from record_cards.permissions import RECARD_COORDINATOR_VALIDATION_DAYS
from themes.actions.group_tree import GroupThemeTree
from themes.models import ElementDetail


class PossibleThemeChange:

    def __init__(self, record_card, group) -> None:
        super().__init__()
        self.record_card = record_card
        self.user_group = group

    def themes_to_change(self) -> list:
        query_kwargs = ElementDetail.ENABLED_ELEMENTDETAIL_FILTERS.copy()
        if self.only_ambit_themes():
            qs = GroupThemeTree(self.group).themes_for_record(self.record_card)
        else:
            qs = ElementDetail.objects.all()
        return qs.filter(**query_kwargs)

    @property
    def group(self):
        return self.record_card.responsible_profile

    def only_ambit_themes(self) -> bool:
        """
        Check if only can be retrieved ambit themes or not.

        Record card theme can only be changed to one inside group ambit:
        - If group is dair, follow the ambit rules (in fact, all themes)
        - If the record has been validated
        - If record card has overcome the period of reassign the record outsite its ambit

        :return: True if only ambit themes can be retrieved, else False
        """
        if self.record_card.is_validated and not self.record_card.record_state_id == RecordState.CLOSED:
            return True

        if RECARD_COORDINATOR_VALIDATION_DAYS in self.group.group_permissions_codes:
            max_reasign_days_outsite_ambit = int(Parameter.get_parameter_by_key("DIES_CANVI_TEMATICA_FORA_AREA_COORD",
                                                                                10))
        else:
            max_reasign_days_outsite_ambit = int(Parameter.get_parameter_by_key("DIES_CANVI_TEMATICA_FORA_AREA", 8))
        if self.record_card.days_in_ambit > max_reasign_days_outsite_ambit:
            return True
        return False
