from profiles.permission_registry import PERMISSIONS

CATEGORY = "REPORTS"
REPS_OPERATIONS = "REPS_OPERATIONS"
REPS_MANAGEMENT = "REPS_OPERATIONS"
REPS_CITIZEN = "REPS_CITIZEN"
REPS_AUDIT = "REPS_AUDIT"
REPS_USERS = "REPS_USERS"


def register_permissions():
    PERMISSIONS.register(REPS_OPERATIONS, {
        "description": "Informes - Operatius i de gestió",
        "category": CATEGORY,
    })
    PERMISSIONS.register(REPS_CITIZEN, {
        "description": "Informes - Accedir a l'aplicació BI",
        "category": CATEGORY,
    })
    PERMISSIONS.register(REPS_AUDIT, {
        "description": "Informes - Auditoria",
        "category": CATEGORY,
    })
    PERMISSIONS.register(REPS_USERS, {
        "description": "Informes - Activitat de consultes",
        "category": CATEGORY,
    })
