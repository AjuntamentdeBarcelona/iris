from modeltranslation.translator import TranslationOptions, register

from record_cards.models import RecordCard, WorkflowResolution


@register(RecordCard)
class RecordCardOptions(TranslationOptions):
    pass


@register(WorkflowResolution)
class WorkflowResolutionOptions(TranslationOptions):
    pass
