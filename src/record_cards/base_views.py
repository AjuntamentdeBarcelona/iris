import logging

from django.db import transaction
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404
from drf_chunked_upload.exceptions import ChunkedUploadError
from drf_chunked_upload.views import ChunkedUploadView, is_authenticated
from rest_framework.permissions import IsAuthenticated

from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN
from rest_framework.views import APIView

from iris_masters.models import RecordState, Parameter
from main.api.serializers import GetGroupFromRequestMixin
from main.utils import get_user_traceability_id
from profiles.permissions import IrisPermissionChecker
from record_cards.mixins import PermissionActionMixin, RecordCardActionCheckMixin
from record_cards.models import RecordCard, Workflow
from record_cards.permissions import MAYORSHIP
from record_cards.serializers import RecordCardCheckSerializer

logger = logging.getLogger(__name__)


class RecordCardActions(GetGroupFromRequestMixin, PermissionActionMixin, RecordCardActionCheckMixin, APIView):
    permission_classes = (IsAuthenticated,)
    record_card_initial_state = None

    is_check = False

    response_serializer_class = RecordCardCheckSerializer

    def post(self, request, *args, **kwargs):
        restricted_response = self.check_restricted_action(request)
        if restricted_response:
            return restricted_response

        if self.record_card.record_state_id in RecordState.CLOSED_STATES:
            closed_states_response = self.check_closed_states_actions()
            if closed_states_response:
                return closed_states_response

        if self.is_check:
            self.do_check_action()
            return self.send_check_response()
        else:
            response = self._perform_action_transaction()
            if response:
                return response

        return self.send_response()

    def _perform_action_transaction(self):
        with transaction.atomic():
            response = self.do_record_card_action()
            if response:
                return response
        self.do_record_card_extra_action()

    @cached_property
    def record_card(self):
        """
        Get record card instance
        :return: RecordCard
        """
        return get_object_or_404(RecordCard, record_state_id=self.get_record_card_initial_state(),
                                 pk=self.kwargs["pk"], enabled=True)

    def get_record_card_initial_state(self):
        """
        Get record card suposed initial state
        :return:
        """
        if not self.record_card_initial_state and not self.record_card_initial_state == RecordState.PENDING_VALIDATE:
            raise NotImplementedError
        return self.record_card_initial_state

    def check_restricted_action(self, request):
        user_group = self.get_group_from_request(request)
        if not self.record_card.group_can_tramit_record(user_group):
            return Response(_("You don't have permissions to do this actions"), status=HTTP_403_FORBIDDEN)

    def has_mayorship(self, request):
        if not self.record_card.mayorship:
            return False
        user_perms = IrisPermissionChecker.get_for_user(request.user)
        return not user_perms.has_permission(MAYORSHIP)

    def check_closed_states_actions(self):
        """
        If record card is closed or cancelled and action can not be done, return HTTP_409.
        Else, do nothing

        """
        pass

    def do_record_card_action(self):
        """
        Do RecordAction must be implemented in each view
        :return:
        """
        raise NotImplementedError

    def do_record_card_extra_action(self):
        """
        Perform extra actions on RecordCard after the main transaction
        :return:
        """
        pass

    def send_response(self):
        """
        Send view response
        :return: View Response
        """
        return Response(status=HTTP_204_NO_CONTENT)


class RecordStateChangeMixin:

    def do_record_card_extra_action(self):
        """
        Perform extra actions on RecordCard after the main transaction
        :return:
        """

        self.record_card.send_record_card_state_changed()

    def perform_state_change(self, next_state, group=None, automatic=False):
        """
        Register the state change

        :param next_state: new state code
        :param group: optional group
        :param automatic: set to True if the state change has been done automatically
        :return:
        """
        state_change = getattr(self.record_card, self.record_card.get_state_change_method(next_state))
        state_change(next_state, self.request.user, self.request.user.imi_data.get('dptcuser', ''), group=group,
                     automatic=automatic)


class RecordStateChangeAction(RecordStateChangeMixin, RecordCardActions):
    pass


class RecordCardGetBaseView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = None
    return_many = False

    def get(self, request, *args, **kwargs):
        return Response(self.get_serializer_class()(instance=self.get_response_objects(), many=self.return_many).data,
                        status=HTTP_200_OK)

    def get_serializer_class(self):
        if not self.serializer_class:
            raise Exception("serializer_class attribute has not been set")
        return self.serializer_class

    def get_response_objects(self):
        raise NotImplementedError


class WorkflowActions(GetGroupFromRequestMixin, PermissionActionMixin, RecordCardActionCheckMixin, APIView):
    permission_classes = (IsAuthenticated,)
    workflow_initial_state = None

    is_check = False

    def post(self, request, *args, **kwargs):

        restricted_response = self.check_restricted_action(request)
        if restricted_response:
            return restricted_response

        if self.is_check:
            self.do_check_action()
            return self.send_check_response()
        else:
            response = self._perform_action_transaction()
            if response:
                return response

        return self.send_response()

    def _perform_action_transaction(self):
        with transaction.atomic():
            resp = self.do_workflow_action()
            if resp:
                return resp
        self.do_workflow_extra_action()

    @cached_property
    def workflow(self):
        """
        Get record card instance
        :return: Worflow
        """
        return get_object_or_404(Workflow.objects.select_related("main_record_card"),
                                 state_id=self.get_workflow_initial_state(), pk=self.kwargs["pk"])

    @cached_property
    def record_card(self):
        """
        Get record card instance
        :return: Worflow
        """
        return self.workflow.main_record_card

    def get_workflow_initial_state(self):
        """
        Get workflow suposed initial state
        :return:
        """
        if not self.workflow_initial_state:
            raise NotImplementedError
        return self.workflow_initial_state

    def check_restricted_action(self, request):
        user_group = self.get_group_from_request(request)
        if not self.record_card.group_can_tramit_record(user_group) and not self.has_mayorship(request):
            return Response(_("You don't have permissions to do this actions"), status=HTTP_403_FORBIDDEN)

    def has_mayorship(self, request):
        if not self.record_card.mayorship:
            return False
        user_perms = IrisPermissionChecker.get_for_user(request.user)
        return not user_perms.has_permission(MAYORSHIP)

    def do_workflow_action(self):
        """
        Do Workflow action must be implemented in each view
        :return:
        """
        raise NotImplementedError

    def do_workflow_extra_action(self):
        """
        Perform extra actions on workflow after the main transaction
        :return:
        """
        pass

    def send_response(self):
        """
        Send view response
        :return: View Response
        """
        return Response(status=HTTP_204_NO_CONTENT)

    def check_valid(self):
        """
        Check data validity
        :return: Return response data
        """
        confirmation_info = {}
        serializer = self.get_serializer_class()(data=self.request.data,
                                                 context={"record_card": self.record_card})
        if serializer.is_valid():
            confirmation_info["can_confirm"] = True
            confirmation_info["reason"] = None
        else:
            confirmation_info["can_confirm"] = False
            confirmation_info["reason"] = _("Post data are invalid")
        return confirmation_info, serializer.errors

    def get_record_next_group(self):
        """
        :return: Next RecordCard group
        """
        derivate_group = self.record_card.derivate(user_id=get_user_traceability_id(self.request.user), is_check=True,
                                                   next_state_id=self.record_card.next_step_code)
        return derivate_group if derivate_group else self.record_card.responsible_profile


class WorkflowStateChangeAction(WorkflowActions):

    def do_workflow_extra_action(self):
        """
        Perform extra actions on workflow after the main transaction
        :return:
        """
        for record_card in self.workflow_records:
            record_card.send_record_card_state_changed()

    def perform_state_change(self, next_state, group=None, automatic=False):
        """
        Register the state change

        :param next_state: new state code
        :param group: optional group
        :param automatic: set to True if the state change has been done automatically
        :return:
        """
        for record_card in self.workflow_records:
            state_change = getattr(record_card, record_card.get_state_change_method(next_state))
            state_change(next_state, self.request.user, self.request.user.imi_data.get('dptcuser', ''), group=group,
                         automatic=automatic)

        self.workflow.state_change(next_state)

    @cached_property
    def workflow_records(self):
        return self.workflow.recordcard_set.all()


class CustomChunkedUploadView(ChunkedUploadView):
    """
    Override class in order to change the serializer call
    """

    def get_max_bytes(self, request):
        """
        Used to limit the max amount of data that can be uploaded. `None` means
        no limit.
        You can override this to have a custom `max_bytes`, e.g. based on
        logged user.
        """
        mb_max_size = int(Parameter.get_parameter_by_key("MIDA_MAXIMA_FITXERS", 10))
        return mb_max_size * (1024 ** 2)

    def _put_chunk(self, request, pk=None, whole=False, *args, **kwargs):
        logger.info('FILE UPLOAD | PUT Chunk start')
        try:
            chunk = request.data[self.field_name]
        except KeyError:
            raise ChunkedUploadError(status=HTTP_400_BAD_REQUEST, detail="No chunk file was submitted")

        if whole:
            start = 0
            total = chunk.size
            end = total - 1
        else:
            content_range = request.META.get("HTTP_CONTENT_RANGE", "")
            match = self.content_range_pattern.match(content_range)
            if not match:
                raise ChunkedUploadError(status=HTTP_400_BAD_REQUEST, detail="Error in request headers")

            start = int(match.group("start"))
            end = int(match.group("end"))
            total = int(match.group("total"))

        chunk_size = end - start + 1
        max_bytes = self.get_max_bytes(request)
        if max_bytes is not None and total > max_bytes:
            raise ChunkedUploadError(status=HTTP_400_BAD_REQUEST,
                                     detail="Size of file exceeds the limit (%s bytes)" % max_bytes)

        if chunk.size != chunk_size:
            raise ChunkedUploadError(status=HTTP_400_BAD_REQUEST,
                                     detail="File size doesn't match headers: file size is {} but {} reported".format(
                                         chunk.size, chunk_size))

        if pk:
            return self._put_new_chunk(pk, start, chunk, chunk_size)
        else:
            return self._put_first_chunk(request, chunk)

    def _put_first_chunk(self, request, chunk):
        user = request.user if is_authenticated(request.user) else None
        chunked_upload = self.serializer_class(data=request.data, context={"request": request})
        if not chunked_upload.is_valid():
            raise ChunkedUploadError(status=HTTP_400_BAD_REQUEST, detail=chunked_upload.errors)
        # chunked_upload is currently a serializer;
        # save returns model instance
        chunked_upload = chunked_upload.save(user=user, offset=chunk.size)
        # If only one chunk, fast forward
        if int(request.data.get('total', 1)) == 1:
            chunked_upload.completed()
            self.on_completion(chunked_upload, request)
        return chunked_upload

    def _put_new_chunk(self, pk, start, chunk, chunk_size):
        upload_id = pk
        chunked_upload = get_object_or_404(self.get_queryset(),
                                           pk=upload_id)
        self.is_valid_chunked_upload(chunked_upload)
        if chunked_upload.offset != start:
            raise ChunkedUploadError(status=HTTP_400_BAD_REQUEST,
                                     detail="Offsets do not match",
                                     offset=chunked_upload.offset)
        logger.info('FILE UPLOAD | PUT Chunk before append')
        chunked_upload.append_chunk(chunk, chunk_size=chunk_size)

    def md5_check(self, chunked_upload, md5):
        logger.info('FILE UPLOAD | MD5 bypass')

    def put(self, request, pk=None, *args, **kwargs):
        try:
            logger.info('FILE UPLOAD | PUT Chunk')
            return self._put(request, pk=pk, *args, **kwargs)
        except ChunkedUploadError as error:
            return Response(error.data, status=error.status_code)

    def post(self, request, pk=None, *args, **kwargs):
        try:
            logger.info('FILE UPLOAD | Post Chunk')
            return self._post(request, pk=pk, *args, **kwargs)
        except ChunkedUploadError as error:
            return Response(error.data, status=error.status_code)
