from profiles.permission_registry import PERMISSIONS

CATEGORY = "SUPPORT"
SUPPORT_ADMIN = "SUPPORT_ADMIN"


def register_permissions():
    PERMISSIONS.register(SUPPORT_ADMIN, {
        "description": "Accions - Administrar el suport",
        "category": CATEGORY,
    })
