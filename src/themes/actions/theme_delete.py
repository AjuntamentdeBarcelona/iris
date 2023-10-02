from django.db import transaction
from django.utils.translation import ugettext as _

from iris_masters.models import RecordState, Reason


class ElementDetailDeleteAction:
    """
    Class to perform element detail post delete action
    """

    def __init__(self, elementdetail_delete_register) -> None:
        self.delete_register = elementdetail_delete_register
        super().__init__()

    def elementdetail_postdelete_process(self) -> None:
        """
        Execute the elementdetail delete process that consists on update the element detail of recordcards involved
        :return:
        """
        with transaction.atomic():
            # Reassign record cards
            self.record_cards_update_themes()

            self.delete_register.process_finished = True
            self.delete_register.save()

    def record_cards_update_themes(self) -> None:
        """
        Update record card themes and add traceability comments

        :return:
        """
        from record_cards.models import RecordCard
        record_params = {
            "enabled": True,
            "element_detail_id": self.delete_register.deleted_detail_id
        }
        if self.delete_register.only_open:
            record_params["record_state_id__in"] = RecordState.OPEN_STATES

        records = RecordCard.objects.filter(**record_params)
        records.update(element_detail_id=self.delete_register.reasignation_detail_id)
        records_ids = records.values_list("id", flat=True)
        self._add_traceability_comments(records_ids)

    def _add_traceability_comments(self, records_ids) -> None:
        """
        Add a comment to traceability for each record card which element detail has been changed

        :param records_ids:
        :return:
        """
        from record_cards.models import Comment
        comment = _("ElementDetail changed from {} to {} because of the deletion of the previous one.").format(
            self.delete_register.deleted_detail.description, self.delete_register.reasignation_detail.description)
        comments = []
        for record_id in records_ids:
            comments.append(Comment(group=self.delete_register.group, reason_id=Reason.THEME_DELETED,
                                    record_card_id=record_id, comment=comment))
        Comment.objects.bulk_create(comments)
