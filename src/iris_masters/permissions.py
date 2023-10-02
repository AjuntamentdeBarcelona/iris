from profiles.permission_registry import PERMISSIONS

CATEGORY = "MASTER"
ADMIN = "MASTER_ADMIN"
MASTERS_EXCEL = "MASTERS_EXCEL"
ADM_MOTOR = "ADM_MOTOR"
ANNOUNCEMENTS = "MASTER_ANNOUNCEMENT"


def register_permissions():
    PERMISSIONS.register(ADMIN, {
        "description": "Menu - Administrar el sistema",
        "category": CATEGORY,
    })
    PERMISSIONS.register(MASTERS_EXCEL, {
        "description": "Accions - Exportar llistats a Excel",
        "category": CATEGORY,
    })
    PERMISSIONS.register(ANNOUNCEMENTS, {
        "description": "Menu - Administrar els anuncis",
        "category": CATEGORY,
    })
