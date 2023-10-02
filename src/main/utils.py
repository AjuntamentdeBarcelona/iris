import functools
import unicodedata

from django.conf import settings
from django.utils.translation import gettext_lazy as _

LIST_ACTION = "list"
CREATE_ACTION = "create"
UPDATE_ACTIONS = ["update", "partial_update"]
DELETE_ACTION = "delete"

SPANISH = "es"
ENGLISH = "en"
GALICIAN = "gl"

LANGUAGES = (
    (SPANISH, _("Spanish")),
    (ENGLISH, _("English")),
    (GALICIAN, _("Galician")),
)


def get_default_lang():
    return SPANISH


def get_translated_fields(field):
    return [f"{field}_{lang}" for lang, name in settings.LANGUAGES]


def rgetattr(obj, attr, *args):
    def _getattr(obj, attr):
        return getattr(obj, attr, *args)
    return functools.reduce(_getattr, [obj] + attr.split("."))


def strip_accents(s):
    if not s:
        return s
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def get_user_traceability_id(user):
    if user.is_anonymous:
        return ""
    return f"{user.email}-{user.username[:8]}"
