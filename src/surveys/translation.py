from modeltranslation.translator import TranslationOptions, register

from surveys import models


@register(models.Survey)
class SurveyOptions(TranslationOptions):
    fields = ("title", )


@register(models.Question)
class QuestionOptions(TranslationOptions):
    fields = ("text", )


@register(models.QuestionReason)
class ReasonOptions(TranslationOptions):
    fields = ("text", )
