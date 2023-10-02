import pytest
from rest_framework.status import HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from iris_masters.models import Process, RecordState, Reason
from main.open_api.tests.base import BaseOpenAPITest
from main.urls import PUBLIC_AUTH_API_URL_NAME
from record_cards.models import RecordCardBlock, Comment, RecordCard, RecordCardStateHistory
from record_cards.tests.test_api import RecordCardActionsMixin, RecordCardRestrictedTestMixin


@pytest.mark.django_db
class BasePublicAuthAPITest(BaseOpenAPITest):
    """
    BaseClass for creating RestFramework view tests that take advantage of the OpenAPI specification. The main goals
    of this class are:
     - Check if an API call is conformant to the OpenAPI schema defined.
     - Give abstractions for creating integration and functional API tests.
     - Generate deterministic test cases easily.

    This class can be extended for more common and concrete use cases.
    """
    path = None
    open_api_format = ".json"
    open_api_url_name = PUBLIC_AUTH_API_URL_NAME


class RecordCardExternalTestMixin(RecordCardActionsMixin, RecordCardRestrictedTestMixin, BasePublicAuthAPITest):
    base_api_path = "/services/iris/api-internet/management"
    next_external_state_id = None
    external_reason_id = None

    def get_next_external_state(self):
        if not self.next_external_state_id:
            raise Exception("Set next external state id")
        return self.next_external_state_id

    def get_external_reason_id(self):
        if not self.external_reason_id:
            raise Exception("Set external reason id")
        return self.external_reason_id

    @pytest.mark.parametrize("initial_record_state_id,comment,is_blocked,expected_response", (
            (RecordState.EXTERNAL_PROCESSING, "test comment", False, HTTP_204_NO_CONTENT),
            (RecordState.EXTERNAL_PROCESSING, "", False, HTTP_400_BAD_REQUEST),
            (RecordState.NO_PROCESSED, "test comment", False, HTTP_404_NOT_FOUND),
    ))
    def test_record_external_processing(self, initial_record_state_id, comment, is_blocked, expected_response):
        record_card = self.create_record_card(record_state_id=initial_record_state_id,
                                              process_pk=Process.EXTERNAL_PROCESSING)
        next_external_state_id = self.get_next_external_state()
        if is_blocked:
            RecordCardBlock.objects.create(record_card=record_card, blocked=True)
        response = self.post(force_params={"id": record_card.pk, "comment": comment})
        assert response.status_code == expected_response
        if expected_response == HTTP_204_NO_CONTENT:
            db_comment = Comment.objects.get(record_card=record_card)
            assert db_comment.comment == comment
            assert db_comment.reason_id == self.get_external_reason_id()
            record_card = RecordCard.objects.get(pk=record_card.pk)
            assert record_card.record_state_id == next_external_state_id
            assert RecordCardStateHistory.objects.get(record_card=record_card, next_state=next_external_state_id)

    def get_post_params(self, record_card):
        return {"id": record_card.pk, "comment": "teeest ttteeeest teteasdsads"}

    def get_record_state_id(self):
        return RecordState.EXTERNAL_PROCESSING


class TestRecordCardExternalReturnedView(RecordCardExternalTestMixin):
    path = "/return/{id}/"
    next_external_state_id = RecordState.EXTERNAL_RETURNED
    external_reason_id = Reason.RECORDCARD_EXTERNAL_RETURN


class TestRecordCardExternalCancelView(RecordCardExternalTestMixin):
    path = "/cancel/{id}/"
    next_external_state_id = RecordState.CANCELLED
    external_reason_id = Reason.RECORDCARD_EXTERNAL_CANCEL


class TestRecordCardExternalCloseView(RecordCardExternalTestMixin):
    path = "/close/{id}/"
    next_external_state_id = RecordState.CLOSED
    external_reason_id = Reason.RECORDCARD_EXTERNAL_CLOSE
