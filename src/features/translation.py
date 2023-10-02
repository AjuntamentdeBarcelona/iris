from modeltranslation.translator import TranslationOptions, register

from main.translation import DescriptionTranslation
from features import models


@register(models.ValuesType)
class ValuesTypeOptions(DescriptionTranslation):
    pass


@register(models.Values)
class ValuesOptions(DescriptionTranslation):
    pass


@register(models.Mask)
class MaskOptions(DescriptionTranslation):
    pass


@register(models.Feature)
class FeatureOptions(TranslationOptions):
    fields = ("description", "explanatory_text")
