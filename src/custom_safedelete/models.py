from safedelete.models import SafeDeleteModel

from custom_safedelete.managers import CustomSafeDeleteManager


class CustomSafeDeleteModel(SafeDeleteModel):
    objects = CustomSafeDeleteManager()

    class Meta:
        abstract = True
