from datetime import timedelta

from django.db.models import Q, Manager, QuerySet
from django.utils import timezone
from drf_chunked_upload.models import ChunkedUpload

from iris_masters.models import RecordState, Reason


class RecordCardQueryset(QuerySet):

    def near_to_expire_records(self):
        return self.filter(Q(ans_limit_date__gt=timezone.now()),
                           Q(ans_limit_nearexpire__lte=timezone.now()), enabled=True).exclude(
            record_state_id__in=RecordState.CLOSED_STATES)

    def applicants_open_records(self, applicants_ids):
        return self.filter(request__applicant_id__in=applicants_ids,
                           record_state_id__in=RecordState.OPEN_STATES).exists()


class RecordCardReasignationManager(QuerySet):

    def last_record_card_reasignation(self, reasigner_group_id, record_card_id=None):
        qs = self.exclude(
            Q(group_id=reasigner_group_id) |
            Q(reason_id=Reason.DERIVATE_RESIGNATION) |
            Q(reason_id=Reason.INITIAL_ASSIGNATION)
        ).order_by("created_at")
        if record_card_id:
            qs = self.filter(record_card_id=record_card_id)
        return qs.last().group if qs else None


class RecordFileManager(Manager):
    """
    A manager that adds a "completed()" and "old()" methods for all chunk files
    """

    def completed(self):
        """
        Only completely uploaded photos
        """
        return self.filter(status=ChunkedUpload.COMPLETE)

    def old(self):
        """
        Only completely uploaded photos with more than an hour
        """
        return self.filter(created_at__lte=timezone.now() - timedelta(hours=1))
