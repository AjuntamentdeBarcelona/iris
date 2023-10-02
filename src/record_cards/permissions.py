from profiles.permission_registry import PERMISSIONS
from django.conf import settings

CATEGORY = "RECARD"
VALIDATE = "RECORD_CARD_VALIDATE"
CANCEL = "RECORD_CARD_CANCEL"
CREATE = "RECORD_CARD_CREATE"
CREATE_TWITTER = "RECORD_CARD_CREATE_TWITTER"
UPDATE = "RECORD_CARD_UPDATE"
MAYORSHIP = "MAYORSHIP"
CITIZENS_CREATE = "CITIZENS_CREATE"
CITIZENS_DELETE = "CITIZENS_DELETE"
NO_REASIGNABLE = "RECORD_CARD_NOREASIGNABLE"
RESP_CHANNEL_UPDATE = "RECARD_RESP_CHANNEL_UPDATE"
THEME_CHANGE = "RECARD_THEME_CHANGE"
RECARD_THEME_CHANGE_AREA = "RECARD_THEME_CHANGE_AREA"
RESP_WORKED = "RECARD_RESP_WORKED"
RESP_WILL_SOLVE = "RECARD_WILL_BE_SOLVED"
RECARD_PENDVALIDATE = "RECARD_PENDVALIDATE"
RECARD_MYTASKS = "RECARD_PENDVALIDATE"
RECARD_SEARCH_NOFILTERS = "RECARD_SEARCH_NOFILTERS"  # todo
RECARD_GUB = "RECARD_GUB"
RECARD_REASIGN = "RECARD_REASIGN"
RECARD_CLAIM = "RECARD_CLAIM"
RECARD_PLAN_RESOL = "RECARD_PLAN_RESOL"
RECARD_ANSWER = "RECARD_ANSWER"
RECARD_SAVE_ANSWER = "RECARD_SAVE_ANSWER"
RECARD_CLOSED_FILES = "RECARD_CLOSED_FILES"
RECARD_SEARCH = "RECARD_SEARCH"
RECARD_HIST = "RECARD_HIST"
RECARD_ANSWER_NOSEND = "RECARD_ANSWER_NOSEND"
RECARD_ANSWER_NO_LETTER = "RECARD_ANSWER_NO_LETTER"
RECARD_LETTER_SICON = "RECARD_LETTER_SICON"
RECARD_ANSWER_RESEND = "RECARD_ANSWER_RESEND"
RECARD_THEME_CHANGE_SYSTEM = "RECARD_THEME_CHANGE_SYSTEM"
RECARD_COORDINATOR_VALIDATION_DAYS = "RECARD_COORDINATOR_VALIDATION_DAYS"
RECARD_VALIDATE_OUTAMBIT = "RECARD_VALIDATE_OUTAMBIT"
RECARD_CHARTS = "RECARD_CHARTS"
RECARD_NOTIFICATIONS = "RECARD_NOTIFICATIONS"
RECARD_MULTIRECORD = "RECARD_MULTIRECORD"
RECARD_REASSIGN_OUTSIDE = "RECARD_REASSIGN_OUTSIDE"


def register_permissions():
    PERMISSIONS.register(VALIDATE, {
        "description": "Acciones - Validar fichas",
        "category": CATEGORY,
    })
    PERMISSIONS.register(CANCEL, {
        "description": "Acciones - Anular fichas",
        "category": CATEGORY,
    })
    PERMISSIONS.register(CREATE, {
        "description": "Menu - Acceder al alta de fichas",
        "category": CATEGORY,
    })
    if settings.TWITTER_ENABLED:
        PERMISSIONS.register(CREATE_TWITTER, {
            "description": "Menu - Acceder al alta de twitter",
            "category": CATEGORY,
        })
    PERMISSIONS.register(UPDATE, {
        "description": "Acciones - Modificar fichas",
        "category": CATEGORY,
    })
    PERMISSIONS.register(MAYORSHIP, {
        "description": "Acciones - Activar Gabinete de Alcaldia",
        "category": CATEGORY,
    })
    PERMISSIONS.register(CITIZENS_CREATE, {
        "description": "Menu - Administrar ciudadanos (alta de solicitantes)",
        "category": CATEGORY,
    })
    PERMISSIONS.register(CITIZENS_DELETE, {
        "description": "Acciones - Eliminar ciudadanos",
        "category": CATEGORY,
    })
    PERMISSIONS.register(NO_REASIGNABLE, {
        "description": "Acciones - Bloquear reasignar fichas",
        "category": CATEGORY,
    })
    PERMISSIONS.register(RESP_CHANNEL_UPDATE, {
        "description": "Acciones - Cambiar canal de respuesta",
        "category": CATEGORY,
    })
    PERMISSIONS.register(THEME_CHANGE, {
        "description": "Acciones - Modificar temática fichas",
        "category": CATEGORY,
    })
    PERMISSIONS.register(RECARD_THEME_CHANGE_AREA, {
        "description": "Acciones - Modificar la temàtica de una fitxa fuera del àrea",
        "category": CATEGORY,
    })
    PERMISSIONS.register(RESP_WORKED, {
        "description": "Acciones - Marcar respuesta trabajada",
        "category": CATEGORY,
    })
    PERMISSIONS.register(RESP_WILL_SOLVE, {
        "description": "Acciones - Tramitar ficha en estado no tramitada.",
        "category": CATEGORY,
    })
    PERMISSIONS.register(RECARD_PENDVALIDATE, {
        "description": "Menu - Acceder a tareas pendientes",
        "category": CATEGORY,
    })
    PERMISSIONS.register(RECARD_SEARCH_NOFILTERS, {
        "description": "Acciones - Consultas de fichas sin el filtro (al listado de todas)",
        "category": CATEGORY,
    })
    PERMISSIONS.register(RECARD_GUB, {
        "description": "Menu - Alta versión mòbil - PDA",
        "category": CATEGORY,
    })
    PERMISSIONS.register(RECARD_REASIGN, {
        "description": "Acciones - Reasignar fichas",
        "category": CATEGORY,
    })
    PERMISSIONS.register(RECARD_CLAIM, {
        "description": "Acciones - Reclamar fichas",
        "category": CATEGORY,
    })
    PERMISSIONS.register(RECARD_PLAN_RESOL, {
        "description": "Acciones - Planificar y resolver fichas",
        "category": CATEGORY,
    })
    PERMISSIONS.register(RECARD_ANSWER, {
        "description": "Acciones - Responder fichas",
        "category": CATEGORY,
    })
    PERMISSIONS.register(RECARD_SAVE_ANSWER, {
        "description": "Acciones: guardar el borrador de respuesta de una ficha",
        "category": CATEGORY,
    })
    PERMISSIONS.register(RECARD_CLOSED_FILES, {
        "description": "Acciones - Adjuntar en fichas cerradas",
        "category": CATEGORY,
    })
    PERMISSIONS.register(RECARD_SEARCH, {
        "description": "Menu - Acceder a la búsqueda de fichas",
        "category": CATEGORY,
    })
    PERMISSIONS.register(RECARD_ANSWER_NOSEND, {
        "description": "Acciones - No enviar respuesta",
        "category": CATEGORY,
    })
    PERMISSIONS.register(RECARD_ANSWER_NO_LETTER, {
        "description": "Acciones - No enviar al SICON",
        "category": CATEGORY,
    })
    PERMISSIONS.register(RECARD_LETTER_SICON, {
        "description": "Acciones - Enviar cartas SICON",
        "category": CATEGORY,
    })
    PERMISSIONS.register(RECARD_ANSWER_RESEND, {
        "description": "Acciones - Reenviar respuesta",
        "category": CATEGORY,
    })
    PERMISSIONS.register(RECARD_THEME_CHANGE_SYSTEM, {
        "description": "Validacions - Mostrar temáticas ocultas",
        "category": CATEGORY,
    })
    PERMISSIONS.register(RECARD_COORDINATOR_VALIDATION_DAYS, {
        "description": "Validacions - Dias de validación coordinador",
        "category": CATEGORY,
    })
    PERMISSIONS.register(RECARD_VALIDATE_OUTAMBIT, {
        "description": "Acciones - Validar fichas contra processos fora del àmbito",
        "category": CATEGORY,
    })
    PERMISSIONS.register(RECARD_CHARTS, {
        "description": "Visualización - Mi actividad",
        "category": CATEGORY,
    })
    PERMISSIONS.register(RECARD_NOTIFICATIONS, {
        "description": "Visualización - Notificaciones",
        "category": CATEGORY,
    })
    PERMISSIONS.register(RECARD_MULTIRECORD, {
        "description": "Acciones - Dar de alta multificha",
        "category": CATEGORY,
    })
    PERMISSIONS.register(RECARD_REASSIGN_OUTSIDE, {
        "description": "Acciones - Reasignar fuera del àmbito",
        "category": CATEGORY,
    })
