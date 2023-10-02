from features.models import Mask
from django.conf import settings


def check_masks(sender, **kwargs):
    """
    :todo: adapt to N languages
    """
    masks_data = {
        Mask.ANY_CHAR: {"es": "Text", "default": "Text", "en": "Text", "type": Mask.TEXT},
        Mask.ONLY_LETTERS: {"es": "A-Z", "default": "A-Z", "en": "A-Z", "type": Mask.TEXT},
        Mask.ANY_NUMBER: {"es": "Número", "default": "Nombre", "en": "Number", "type": Mask.NUMBER},
        Mask.INTEGER: {"es": "0-9", "default": "0-9", "en": "0-9", "type": Mask.NUMBER},
        Mask.PHONE_NUMBER: {"es": "9 dígitos", "default": "9 dígits", "en": "9 digits", "type": Mask.NUMBER},
        Mask.POSTAL_CODE: {"es": "5 dígitos", "default": "5 dígits", "en": "5 digits", "type": Mask.NUMBER},
        Mask.DATE_FORMAT: {"es": "dd/mm/YYYY", "default": "dd/mm/YYYY", "en": "dd/mm/YYYY", "type": Mask.DATE},
        Mask.HOUR_FORMAT: {"es": "hh:mm", "default": "hh:mm", "en": "hh:mm", "type": Mask.TIME}
    }

    for (mask_id, _) in Mask.MASKS:
        mask_data = masks_data[mask_id]
        mask, _ = Mask.objects.get_or_create(id=mask_id, defaults={
            "description": mask_data["es"], "description_es": mask_data["es"]
        })
        for lang, _ in settings.LANGUAGES:
            setattr(mask, f'description_{lang}', mask_data.get(lang, mask_data['default']))
        mask.type = mask_data["type"]
        mask.save()
