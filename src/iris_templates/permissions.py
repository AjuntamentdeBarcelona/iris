from profiles.permission_registry import PERMISSIONS

OWN_TEMPLATES = "TEMP_OWN_TEMPLATES"
TEMPLATES = 'TEMP'


def register_permissions():
    PERMISSIONS.register(OWN_TEMPLATES, {
        "description": "Accions - Gestionar plantilles propies",
        "category": TEMPLATES,
    })
