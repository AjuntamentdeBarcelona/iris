from django.db.models import Q
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from iris_masters.models import Parameter


class PossibleReassignations:
    """
    Class to get the possible groups to reassignate a record_card giving a reasignator group
    """

    NO_REASIGN_GROUPS = 0
    REASIGN_AMBIT_GROUPS = 1
    REASIGN_COORDINATOR_ONLY = 2
    REASIGN_CONFIG_GROUPS = 3

    def __init__(self, record_card, outside_ambit_permission=True) -> None:
        """
        :param record_card:
        :param outside_ambit_permission: Indicates if the user has permission for assigning outside its ambit
        """
        self.record_card = record_card
        self.outside_ambit_permission = outside_ambit_permission
        super().__init__()

    def get_reassignation_coordinator(self, reasigner_group):
        """
        When reassigning only in ambit, a parent group must be choosen as the coordinator.
        The coordinator will be the group with depth level = 1 in the tree, in other words a Coordinator or Supra.
        If the group is the coordinator, supra or DAIR, the coordinator will be the group itself.
        :return: Reassignation ambit coordinator
        """
        return reasigner_group.get_ambit_coordinator()

    def reasignations(self, reasigner_group):
        """
        Look for the possible groups to reassignate the record.

        :param reasigner_group: Group which will do the reassignation
        :return: List of possible groups to reassignate the record
        """
        if not self.record_card.group_can_tramit_record(reasigner_group):
            return []

        reasignation_type = self.select_reasignation_type(reasigner_group)
        if reasignation_type["reasignation_type"] == self.NO_REASIGN_GROUPS:
            return []
        elif reasignation_type["reasignation_type"] == self.REASIGN_AMBIT_GROUPS:
            group_ascendant = self.get_reassignation_coordinator(reasigner_group)
            return self.possible_reasignations(
                reasigner_group,
                group_ascendant=group_ascendant,
                only_ambit=True,
            )
        elif reasignation_type["reasignation_type"] == self.REASIGN_COORDINATOR_ONLY:
            return [self.get_reassignation_coordinator(reasigner_group)]
        else:  # reasignation_type["reasignation_type"] == self.REASIGN_CONFIG_GROUPS:
            return self.possible_reasignations(reasigner_group)

    def reasign_action(self, reasigner_group) -> dict:
        """
        Set recordcard reasign action

        :param reasigner_group: Group which will do the reassignation
        :return:
        """
        if not self.record_card.group_can_tramit_record(reasigner_group):
            return {"action_url": None, "check_url": None, "reason": _("Group {} can not tramit record {}").format(
                reasigner_group.description, self.record_card.normalized_record_id), "can_perform": False,
                    "action_method": "post"}

        action_url = reverse("private_api:record_cards:record_card_reasign")
        reasignation_type = self.select_reasignation_type(reasigner_group)
        if reasignation_type["reasignation_type"] == self.NO_REASIGN_GROUPS:
            return {"action_url": None, "check_url": None, "reason": reasignation_type["reason"], "can_perform": False,
                    "action_method": "post"}
        elif reasignation_type["reasignation_type"] == self.REASIGN_AMBIT_GROUPS:
            return {"action_url": action_url, "check_url": None, "reason": reasignation_type["reason"],
                    "can_perform": True, "action_method": "post"}
        elif reasignation_type["reasignation_type"] == self.REASIGN_COORDINATOR_ONLY:
            return {"action_url": action_url, "check_url": None, "reason": reasignation_type["reason"],
                    "can_perform": True, "action_method": "post"}
        else:  # reasignation_type["reasignation_type"] == self.REASIGN_CONFIG_GROUPS:
            return {"action_url": action_url, "check_url": None, "reason": None, "can_perform": True,
                    "action_method": "post"}

    def select_reasignation_type(self, reasigner_group) -> dict:
        """
        Select the type of reasignation depending on RecordCard conditions.

        If recordCard has reassignment not allowed, return No RESIAGN GROUPS and the reason
        If recordCard applies the only ambit conditions, return REASIGN AMBIT GROUPS and the reason
        Else return reasign config groups

        :param reasigner_group: Group which will do the reassignation
        :return: {"reasignation_type": "int", "reason": "str"}
        """

        if self.record_card.reassignment_not_allowed:
            return {"reasignation_type": self.REASIGN_AMBIT_GROUPS,
                    "reason": _("RecordCard is set as 'No Reasignable'.")}

        ambit_reasignation = self.only_ambit_reasignation(reasigner_group)
        if ambit_reasignation["only_ambit"] or not self.outside_ambit_permission:
            return {"reasignation_type": self.REASIGN_AMBIT_GROUPS, "reason": ambit_reasignation.get("reason")}

        if self.record_card.claims_number >= Parameter.max_claims_number() and not reasigner_group.is_ambit:
            return {"reasignation_type": self.REASIGN_COORDINATOR_ONLY,
                    "reason": _("Only a coordinator is allowed to send the response")}

        return {"reasignation_type": self.REASIGN_CONFIG_GROUPS}

    def only_ambit_reasignation(self, reasigner_group) -> dict:
        """
        Check if a RecordCard can only be reassigned to a group from the ambit.
        Ambit conditions are:
        - If record card is validated and theme does not allow reassignation after validation
        - If record card has expired
        - If record card has been claimed more than the limit number of times and the reasigner group is a coordinator

        :param reasigner_group: Group which will do the reassignation
        :return: {"only_ambit": "bool", "reason": "str"}
        """

        if self.record_card.is_validated and not self.record_card.element_detail.validated_reassignable:
            return {"only_ambit": True,
                    "reason": _("RecordCard {} can not be reasigned outside group's ambit after validation because "
                                "it's theme does not allow it.").format(self.record_card.normalized_record_id)}

        if self.record_card.has_expired(reasigner_group):
            return {"only_ambit": True,
                    "reason": _("RecordCard {} can not be reasigned outside group's ambit because the period to do "
                                "it has overcome. To be reasigned, the record must be cancelled by expiration"
                                ).format(self.record_card.normalized_record_id)}

        max_claims = Parameter.max_claims_number()
        if self.record_card.claims_number >= max_claims and reasigner_group.is_ambit:
            return {"only_ambit": True,
                    "reason": _("RecordCard {} can not be reasigned outside group's ambit because it has been claimed "
                                "more than {} times").format(self.record_card.normalized_record_id, max_claims)}

        return {"only_ambit": False}

    def possible_reasignations(self, reasigner_group, **kwargs):
        """
        Get the possible reassignation of the reasigner group

        :param reasigner_group: Group that is doing the reasignation
        :return: Possible reassignation of the reasigner group, adding on the first place the las reassignation
        """
        only_ambit = kwargs.pop('only_ambit', False)
        group_ascendant = kwargs.pop('group_ascendant', None)
        possible_reasignations = {}
        last_reasignation_group = self.record_card.recordcardreasignation_set.last_record_card_reasignation(
            reasigner_group.pk)

        if last_reasignation_group and not only_ambit:
            possible_reasignations[last_reasignation_group.pk] = last_reasignation_group

        group_reassignations = reasigner_group.groupreassignation_set.select_related("reasign_group").filter(
            enabled=True, reasign_group__deleted__isnull=True
        )
        if group_ascendant and group_ascendant.parent:
            if group_ascendant == reasigner_group:
                group_reassignations = group_reassignations.filter(
                    Q(reasign_group__group_plate__startswith=group_ascendant.group_plate) |
                    Q(reasign_group__group_plate=group_ascendant.parent.group_plate)
                )
            else:
                group_reassignations = group_reassignations.filter(
                    reasign_group__group_plate__startswith=group_ascendant.group_plate
                )

        group_reassignations = group_reassignations.exclude(
            reasign_group_id=self.record_card.responsible_profile_id
        ).order_by("reasign_group__description")

        for reasignation in group_reassignations:
            possible_reasignations[reasignation.reasign_group_id] = reasignation.reasign_group

        return list(possible_reasignations.values())
