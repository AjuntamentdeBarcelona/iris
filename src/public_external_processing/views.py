from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.status import HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND

from iris_masters.models import RecordState, Reason
from main.iris_roles import public_extern_iris_roles
from public_external_processing.serializers import ExternalProcessedSerializer
from record_cards.base_views import RecordStateChangeAction
from record_cards.mixins import SetRecordStateHistoryMixin
from record_cards.models import RecordCard, Comment
from main.utils import get_user_traceability_id


class ExternalProcessingMixin(SetRecordStateHistoryMixin, RecordStateChangeAction):
    permission_classes = (IsAuthenticated,)

    record_card_initial_state = RecordState.EXTERNAL_PROCESSING
    next_external_state_id = None
    external_reason_id = None

    @cached_property
    def record_card(self):
        """
        Get record card instance
        :return: RecordCard
        """
        return get_object_or_404(RecordCard, record_state_id=self.get_record_card_initial_state(),
                                 pk=self.kwargs["pk"], enabled=True)

    def do_record_card_action(self):
        """
        Register action comment and set record card state to EXTERNAL_RETURNED
        :return:
        """
        serializer = ExternalProcessedSerializer(data=self.request.data)
        if serializer.is_valid(raise_exception=True):
            group = self.request.user.usergroup.group if hasattr(self.request.user, "usergroup") else None
            self.before_state_change()
            self.perform_state_change(self.get_next_external_state(), group)
            Comment.objects.create(record_card=self.record_card, user_id=get_user_traceability_id(self.request.user), group=group,
                                   reason_id=self.get_external_reason_id(), comment=serializer.data["comment"])

    def get_next_external_state(self):
        if not self.next_external_state_id:
            raise Exception("Set next external state id")
        return self.next_external_state_id

    def get_external_reason_id(self):
        if not self.external_reason_id:
            raise Exception("Set external reason id")
        return self.external_reason_id

    def before_state_change(self):
        pass

    def check_restricted_action(self, request):
        """
        :param request:
        :return: OAM is responsible for managing the auth of this zone.
        """
        pass


@method_decorator(name="post", decorator=public_extern_iris_roles)
@method_decorator(name="post", decorator=swagger_auto_schema(
    request_body=ExternalProcessedSerializer,
    responses={
        HTTP_204_NO_CONTENT: "RecordCard to external returned",
        HTTP_400_BAD_REQUEST: "Bad request: Validation Error",
        HTTP_403_FORBIDDEN: "Acces not allowed",
        HTTP_404_NOT_FOUND: "RecordCard is not available to external returning",
    }
))
class RecordCardExternalReturnedView(ExternalProcessingMixin):
    """
    Endpoint to get back a record card sent to External processing that the external service return because it's
    not their business
    """
    next_external_state_id = RecordState.EXTERNAL_RETURNED
    external_reason_id = Reason.RECORDCARD_EXTERNAL_RETURN

    def before_state_change(self):
        self.record_card.closing_date = None


@method_decorator(name="post", decorator=public_extern_iris_roles)
@method_decorator(name="post", decorator=swagger_auto_schema(
    request_body=ExternalProcessedSerializer,
    responses={
        HTTP_204_NO_CONTENT: "RecordCard to external canceled",
        HTTP_400_BAD_REQUEST: "Bad request: Validation Error",
        HTTP_403_FORBIDDEN: "Acces not allowed",
        HTTP_404_NOT_FOUND: "RecordCard is not available to external cancelling",
    }
))
class RecordCardExternalCancelView(ExternalProcessingMixin):
    """
    Endpoint to get back a record card sent to External processing that the external service has cancelled
    """
    next_external_state_id = RecordState.CANCELLED
    external_reason_id = Reason.RECORDCARD_EXTERNAL_CANCEL


@method_decorator(name="post", decorator=public_extern_iris_roles)
@method_decorator(name="post", decorator=swagger_auto_schema(
    request_body=ExternalProcessedSerializer,
    responses={
        HTTP_204_NO_CONTENT: "RecordCard to external closed",
        HTTP_400_BAD_REQUEST: "Bad request: Validation Error",
        HTTP_403_FORBIDDEN: "Acces not allowed",
        HTTP_404_NOT_FOUND: "RecordCard is not available to external closing",
    }
))
class RecordCardExternalCloseView(ExternalProcessingMixin):
    """
    Endpoint to get back a record card sent to External processing that the external service has closed
    """
    external_reason_id = Reason.RECORDCARD_EXTERNAL_CLOSE

    def get_next_external_state(self):
        return self.record_card.next_step_code
