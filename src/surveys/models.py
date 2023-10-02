from django.db import models
from django.utils.translation import gettext_lazy as _

from main.cachalot_decorator import iris_cachalot
from record_cards.models import RecordCard


class SurveysTrack(models.Model):
    created_at = models.DateTimeField(verbose_name=_("Creation date"), auto_now_add=True, null=True)

    class Meta:
        abstract = True


class Survey(SurveysTrack):
    objects = iris_cachalot(models.Manager(), extra_fields=["active"])

    title = models.CharField(max_length=200)
    active = models.BooleanField(default=True)
    slug = models.SlugField()
    # todo: remove when requirement is confirmed
    require_reason_from = models.PositiveSmallIntegerField(default=4)


class Question(SurveysTrack):
    objects = iris_cachalot(models.Manager(), extra_fields=["active"])

    survey = models.ForeignKey(Survey, on_delete=models.PROTECT, related_name="questions")
    text = models.TextField()
    active = models.BooleanField(default=True)


class QuestionReason(SurveysTrack):
    objects = iris_cachalot(models.Manager())

    text = models.TextField()
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="reasons")


class SurveyAnswer(SurveysTrack):
    record_card = models.ForeignKey(RecordCard, on_delete=models.CASCADE)
    survey = models.ForeignKey(Survey, on_delete=models.PROTECT)

    class Meta:
        unique_together = ("record_card", "survey")


class QuestionAnswer(SurveysTrack):
    MAX_VALUE = 10
    MIN_VALUE = 0
    survey_answer = models.ForeignKey(SurveyAnswer, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.PROTECT)
    value = models.SmallIntegerField()
    reason = models.ForeignKey(QuestionReason, on_delete=models.PROTECT, null=True, blank=True)
