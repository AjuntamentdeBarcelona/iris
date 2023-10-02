from django.db import transaction
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.fields import empty

from surveys.models import Question, QuestionAnswer, QuestionReason, SurveyAnswer


class QuestionReasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionReason
        fields = ("text", "pk")


class QuestionSerializer(serializers.ModelSerializer):
    reasons = QuestionReasonSerializer(many=True)

    class Meta:
        model = Question
        fields = ("text", "pk", "reasons")


class SurveyOptionsSerializer(serializers.Serializer):
    questions = QuestionSerializer(many=True)
    ready = serializers.BooleanField(help_text="If true, the survey has been rated.")
    closed = serializers.BooleanField(help_text="If true, the record card is closed and ready to answer.")
    can_answer = serializers.BooleanField(help_text="If true, the survey can be answered.")
    min_for_reason = serializers.IntegerField(default=4)

    def __init__(self, instance=None, **kwargs):
        context = kwargs.get("context", {})
        can_answer = context.get("closed", False) and context.get("survey_answer") is None
        instance = {
            "questions": instance if can_answer else [],
            "ready": context.get("survey_answer") is not None,
            "closed": context.get("closed", False),
            "can_answer": can_answer,
            "min_for_reason": context.get("min_for_reason", 4),
        }
        super().__init__(instance, **kwargs)


class QuestionAnswerListSerializer(serializers.ListSerializer):
    """
    List of answers for a given survey. It requires to answer each question in the survey.
    """
    ERROR_MSG = _("You should rate this item.")
    CANNOT_RATE = _("You cannot rate this item in this survey.")

    def create(self, validated_data):
        with transaction.atomic():
            survey_answer = SurveyAnswer.objects.create(survey=self.survey, record_card=self.record_card)
            for data in validated_data:
                data["survey_answer"] = survey_answer
            return super().create(validated_data)

    @property
    def data(self):
        return {}

    @property
    def survey(self):
        return self.child.survey

    @property
    def record_card(self):
        return self.child.record_card

    def is_valid(self, raise_exception=False):
        valid = super().is_valid(False)
        errors = self.has_all_answered()
        if errors or not valid:
            self._errors = {
                "missing": errors,
                "invalid": self.errors
            }
            if raise_exception:
                raise serializers.ValidationError(self.errors)
            else:
                return False
        return valid

    def has_all_answered(self):
        answers = {item["question"]: item for item in self.initial_data}
        errors = {}
        for question in self.survey.questions.filter(active=True):
            try:
                answers.pop(question.pk)
            except KeyError:
                errors[question.pk] = self.ERROR_MSG
        for question in answers.keys():
            errors[question] = self.CANNOT_RATE
        return errors


class QuestionAnswerSerializer(serializers.ModelSerializer):
    """
    Represents a valid answer for a survey question. If the value of the rating is under a certain number,
    requires to specify a reason for the bad qualification. The minimum number for requiring a reason is
    defined by the survey and returned with the SurveyOptions.

    The QuestionAnswerListSerializer is responsible of validating the objects as a group, as recommends Django Rest
    Framework.
    """
    value = serializers.IntegerField(max_value=10, min_value=0)

    def __init__(self, survey=None, record_card=None, instance=None, data=empty, **kwargs):
        self.survey = survey
        self.record_card = record_card
        super().__init__(instance, data=data, **kwargs)

    def validate(self, attrs):
        super().validate(attrs)
        errors = {}
        if attrs.get("reason") and attrs.get("reason").question != attrs.get("question"):
            errors["reason"] = [_("You should specify a valid reason for the question.")]
        question = attrs["question"]
        question_reason_count = question.reasons.count()
        if self.survey and question_reason_count > 0 and attrs["value"] <= self.survey.require_reason_from and not attrs.get("reason"):
            missing_reason_error = _(f"Question {question.id} value is below {self.survey.require_reason_from}, you must provide a reason")
            errors["reason"] = errors["reason"].append(missing_reason_error) if "reason" in errors else [missing_reason_error]
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    class Meta:
        model = QuestionAnswer
        fields = ("question", "value", "reason")
        list_serializer_class = QuestionAnswerListSerializer
