from safedelete.config import DELETED_VISIBLE_BY_PK
from safedelete.managers import SafeDeleteManager

from custom_safedelete.queryset import CustomSafeDeleteQueryset


class CustomSafeDeleteManager(SafeDeleteManager):
    _safedelete_visibility = DELETED_VISIBLE_BY_PK
    _safedelete_visibility_field = "id"
    _queryset_class = CustomSafeDeleteQueryset
