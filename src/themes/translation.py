from modeltranslation.translator import TranslationOptions, register
from main.translation import DescriptionTranslation

from themes import models


@register(models.Area)
class AreaOptions(DescriptionTranslation):
    pass


@register(models.Element)
class ElementOptions(DescriptionTranslation):
    fields = DescriptionTranslation.fields + ("alternative_text", )


@register(models.ElementDetail)
class ElementDetailOptions(TranslationOptions):
    fields = ("description", "short_description", "email_template", "sms_template", "lopd", "links", "head_text",
              "footer_text", "app_description")


@register(models.ThemeGroup)
class ThemeGroupOptions(TranslationOptions):
    pass
