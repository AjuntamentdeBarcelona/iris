from modeltranslation.translator import register

from modeltranslation.translator import TranslationOptions
from profiles.models import Group, Profile


@register(Group)
class GroupOptions(TranslationOptions):
    pass


@register(Profile)
class ProfileOptions(TranslationOptions):
    pass
