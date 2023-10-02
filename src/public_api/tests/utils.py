from django.utils import translation


def wrap_with_text(func, text):
    def new_func(*args, **kwargs):
        output = func(*args, **kwargs)
        return f"{text}{output}"
    return new_func


def set_custom_translations(text: str, language: str):
    old_lang = translation.get_language()

    # Method adapted from https://www.technomancy.org/python/django-i18n-test-translation-by-manually-setting-translations/
    # Used to mock translations

    translation.activate(language)

    language_translation = translation.trans_real._active.value

    language_translation.gettext = wrap_with_text(language_translation.gettext, text)
    language_translation.ngettext = wrap_with_text(language_translation.ngettext, text)

    translation.activate(old_lang)
