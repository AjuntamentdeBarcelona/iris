from django.db import transaction
from django.utils.translation import ugettext_lazy as _

from iris_masters.models import RecordState, Reason
from themes.models import DerivationDirect, DerivationDistrict


class GroupDeleteAction:
    group_delete_register = None

    def __init__(self, group_delete_register) -> None:
        self.group_delete_register = group_delete_register
        super().__init__()

    def group_delete_process(self) -> None:
        """
        Execute the group delete process that consists on reassign all the derivations involved with the deleted group
        and the reasignation of the record cards
        :return:
        """
        with transaction.atomic():
            # Change derivations
            self.derivations_reassign_by_model(DerivationDirect)
            self.derivations_reassign_by_model(DerivationDistrict)

            # Reassign record cards
            self.record_cards_reassign()

            self.group_delete_register.process_finished = True
            self.group_delete_register.save()

    def derivations_reassign_by_model(self, model_class) -> None:
        """
        Reasign the derivations from the deleted group to reasignation group.
        Taking in account the traceabilitu of the models, the previous derivation is disabled and a new created,
        registering the user that has created it.

        :param model_class: Derivation type
        :return:
        """

        for derivation in model_class.objects.filter(group=self.group_delete_register.deleted_group, enabled=True):
            # disable previous derivations
            derivation.enabled = False
            derivation.save()
            # create a new and enabled derivation with the new group
            derivation.pk = None
            derivation.user_id = self.group_delete_register.user_id
            derivation.group = self.group_delete_register.reasignation_group
            derivation.enabled = True
            derivation.save()

    def record_cards_reassign(self) -> None:
        """
        Select the record that has to be reassigned and do the reassignation process.
        The process consists on reassign the record card, close the opened conversations, set the reassigned
        alarm and register the reassignation.
        :return:
        """
        from record_cards.models import RecordCard, RecordCardReasignation
        record_params = {
            'responsible_profile_id': self.group_delete_register.deleted_group_id,
            'enabled': True
        }
        if self.group_delete_register.only_open:
            record_params['record_state_id__in'] = RecordState.OPEN_STATES

        for record_card in RecordCard.objects.filter(**record_params):
            # reasign record, close convesations and register reassigned alarm
            record_card.responsible_profile_id = self.group_delete_register.reasignation_group_id
            record_card.close_record_conversations()
            record_card.reasigned = True
            record_card.alarm = True
            record_card.save(update_fields=["responsible_profile_id", "reasigned", "alarm"])

            # register reassignation
            RecordCardReasignation.objects.create(
                user_id=self.group_delete_register.user_id, record_card=record_card,
                previous_responsible_profile_id=self.group_delete_register.deleted_group_id,
                next_responsible_profile_id=self.group_delete_register.reasignation_group_id,
                reason_id=Reason.GROUP_DELETED,
                group_id=self.group_delete_register.group_id,
                comment=_("The previous responsible group of the RecordCard was deleted"))
