from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_auto_schema

from rest_framework.generics import ListAPIView, get_object_or_404, CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework.response import Response

from iris_masters.models import RecordState
from main.iris_roles import public_iris_roles
from record_cards.models import RecordCard
from surveys.models import Question, SurveyAnswer, Survey
from surveys.serializers import SurveyOptionsSerializer, QuestionAnswerSerializer


class RecordCardSurveyMixin:
    record_card_code_kwarg = "record_id"
    survey_slug_kwarg = "survey"

    @cached_property
    def survey(self):
        return get_object_or_404(Survey, slug=self.kwargs.get(self.survey_slug_kwarg), active=True)

    @cached_property
    def survey_answer(self):
        record_id = self.kwargs.get(self.record_card_code_kwarg, '').upper()
        return SurveyAnswer.objects.filter(record_card__normalized_record_id=record_id).first()

    @cached_property
    def record_card(self):
        return get_object_or_404(
            RecordCard,
            normalized_record_id=self.kwargs.get(self.record_card_code_kwarg, '').upper()
        )

    @property
    def valid_record_card(self):
        return self.record_card.record_state_id in [RecordState.CLOSED, RecordState.CANCELLED]


@method_decorator(name="get", decorator=public_iris_roles)
@method_decorator(name="get", decorator=swagger_auto_schema(
    responses={
        status.HTTP_200_OK: SurveyOptionsSerializer(many=False),
        status.HTTP_404_NOT_FOUND: "",
    }
))
class SurveyQuestionsView(RecordCardSurveyMixin, ListAPIView):
    """
    Recovers the questions for rating the service received within a record card.
    The answer has three parts: questions, ready and closed, which define what questions
     must be answered, if the surveys is answered yet and if the record card is closed.

    *Additional considerations*
    * The survey can be completed when ready = false and closed = true.
    * If the survey cannot be answered, the question list will be empty.
    """
    model = Question
    queryset = Question.objects.filter(active=True).prefetch_related("reasons")
    serializer_class = SurveyOptionsSerializer
    permission_classes = (AllowAny,)
    pagination_class = None

    def get_serializer(self, *args, **kwargs):
        kwargs["many"] = False
        return super().get_serializer(*args, **kwargs)

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["survey_answer"] = self.survey_answer
        ctx["closed"] = self.record_card.record_state_id in [RecordState.CLOSED, RecordState.CANCELLED]
        ctx["min_for_reason"] = self.survey.require_reason_from
        return ctx


@method_decorator(name="post", decorator=public_iris_roles)
class AnswerSurveyView(RecordCardSurveyMixin, CreateAPIView):
    """
    Gives answer to a given survey. It's mandatory to answer all the questions recovered in the surveys read endpoint.
    The survey can be answered if the associated record card is closed and is not rated yet.

    *Additional considerations*
    * If the value of the rating is under a certain number, requires to specify a reason for the bad qualification.
    * The minimum number for requiring a bad rating reason is defined by the survey and returned in the SurveyOptions.
    """
    serializer_class = QuestionAnswerSerializer
    permission_classes = (AllowAny,)

    @method_decorator(name="post", decorator=swagger_auto_schema(
        request_body=QuestionAnswerSerializer(many=True),
        responses={
            status.HTTP_201_CREATED: "Survey answered",
            status.HTTP_404_NOT_FOUND: "Group with profile_ctrl_user_id does not exist",
            status.HTTP_400_BAD_REQUEST: "Bad Request",
            status.HTTP_409_CONFLICT: "You can rate the service only one time per record"
        }
    ))
    def post(self, request, *args, **kwargs):
        if self.survey_answer:
            return Response(
                data=_("You can rate the service only one time per record."),
                status=status.HTTP_409_CONFLICT,
            )
        if not self.valid_record_card:
            return Response(
                data=_("You cannot rate a record in progress."),
                status=status.HTTP_409_CONFLICT,
            )
        return super().post(request, *args, **kwargs)

    def get_serializer(self, *args, **kwargs):
        kwargs["many"] = True
        kwargs["survey"] = self.survey
        kwargs["record_card"] = self.record_card
        return super().get_serializer(*args, **kwargs)
