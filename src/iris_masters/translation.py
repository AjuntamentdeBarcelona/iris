from modeltranslation.translator import TranslationOptions, register

from main.translation import DescriptionTranslation
from iris_masters import models


@register(models.RecordType)
class RecordStateOptions(DescriptionTranslation):
    pass


@register(models.RecordState)
class RecordTypeOptions(DescriptionTranslation):
    pass


@register(models.ResponseType)
class ResponseTypeOptions(TranslationOptions):
    pass


@register(models.Reason)
class ReasonOptions(TranslationOptions):
    pass


@register(models.MediaType)
class MediaTypeOptions(DescriptionTranslation):
    pass


@register(models.InputChannel)
class InputChannelOptions(TranslationOptions):
    pass


@register(models.Application)
class ApplicationOptions(DescriptionTranslation):
    pass


@register(models.Support)
class SupportOptions(TranslationOptions):
    pass


@register(models.ApplicantType)
class ApplicantTypeOptions(TranslationOptions):
    pass


@register(models.ResolutionType)
class ResolutionTypeOptions(TranslationOptions):
    pass


@register(models.Announcement)
class AnnouncementOptions(TranslationOptions):
    pass
