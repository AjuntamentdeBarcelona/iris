from django.conf import settings
from django.utils import translation

from iris_masters.models import RecordState


def check_record_states(sender, **kwargs):
    keys = []
    for (record_state_key, record_state_description) in RecordState.STATES:
        defaults = {'acronym': RecordState.ACRONYMS[
                        record_state_key]}
        descriptions = get_state_language(record_state_description)
        defaults.update(descriptions)
        record_state, _ = RecordState.objects.get_or_create(id=record_state_key,
                                                            defaults=defaults)
        keys.append(record_state_key)
        for attr, value in descriptions.items():
            setattr(record_state, attr, value)
        record_state.acronym = RecordState.ACRONYMS[record_state_key]
        record_state.save()
    RecordState.objects.exclude(id__in=keys).delete()


def get_state_language(record_state_description):
    """
    :param state:
    :return: Dict with the state descriptions for all languages as keys following the description_{lang} pattern.
    """
    old_lang = translation.get_language()
    descs = {}
    for lang, _ in settings.LANGUAGES:
        translation.activate(lang)
        descs[f'description_{lang}'] = str(record_state_description).upper()
    translation.activate(old_lang)
    return descs
