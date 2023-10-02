from iris_masters.data_checks.parameters import create_parameter_list
from iris_masters.models import Parameter
from django.conf import settings

from iris_templates.data_checks.migrate_old_params import migrate_old_params

TEXT_CIM = 'TEXTCIMAIL'
TEXT_CIM_ANSWER = 'TEXTCIMAIL_SOLICITA'
CARTA_ICONA = 'IRIS_CARTA_ICONO'


def check_template_parameters(sender, update_all=False, **kwargs):
    translatable_parameters = [
        {"user_id": "IRIS2", "parameter": "ACUSAMENT_REBUT",
         "valor": "SET",
         "description": "Texto acuse de recibo del alta de ficha en {lang}",
         "name": "Fichas - Acuse de recibo - {lang}",
         "original_description": "Texto acuse de recibo del alta de ficha en {lang}", "show": True,
         "data_type": False, "visible": False, "category": Parameter.CREATE
         },
        {"user_id": "IRIS2", "parameter": "ACUSAMENT_MULTI",
         "valor": "SET",
         "description": "Acuse de recibo de fichas creadas como multificha ({lang})",
         "name": "Multifichas - Acuse de recibo de multifichas - {lang}",
         "original_description": "Acuse de recibo de fichas creadas como multificha ({lang})", "show": True,
         "data_type": False, "visible": False, "category": Parameter.CREATE,
         },
        {"user_id": "IRIS2", "parameter": "PLANTILLA_DERIVACIO_EXTERNA",
         "valor": "SET",
         "description": "Plantilla de email de notificación de la tramitación externa.",
         "name": "Plantilla tramitación externa",
         "original_description": "Plantilla de tramitación externa", "show": True,
         "data_type": False, "visible": False, "category": Parameter.CREATE,
         },
        {"user_id": "IRIS2", "parameter": TEXT_CIM,
         "valor": "SET",
         "description": "Texto de la comunicación intermedia (Mail {lang})",
         "name": "Comunicaciones - Comunicación Intermedia - {lang}",
         "original_description": "Texto de la comunicación intermedia (Mail {lang})", "show": True,
         "data_type": False, "visible": False, "category": Parameter.TEMPLATES,
         },
        {"user_id": "IRIS2", "parameter": TEXT_CIM_ANSWER,
         "valor": "SET",
         "name": "Comunicaciones - Comunicación intermedia con Link para datos - {lang}",
         "description": "Comunicación intermedia con Link para datos {lang}",
         "original_description": "Comunicación intermedia con Link para datos {lang}", "show": True,
         "data_type": False, "visible": False, "category": Parameter.TEMPLATES,
         },
        {"user_id": "IRIS2", "parameter": "TEXTCARTAFI",
         "valor": "SET",
         "description": "Texto de despedida de los mensajes en {lang}",
         "name": "Comunicaciones - Texto de despedida para las cartas - {lang}",
         "original_description": "Texto de despedida de los mensajes en {lang}", "show": True,
         "data_type": False, "visible": False, "category": Parameter.TEMPLATES
         },
        {"user_id": "IRIS2", "parameter": "TEXTCARTASIGNATURA",
         "valor": "SET",
         "description": "Texto de firma de los mensajes en {lang}",
         "name": "Comunicaciones - Texto de la firma para las cartas - {lang}",
         "original_description": "Texto de firma de los mensajes en {lang}", "show": True,
         "data_type": False, "visible": False, "category": Parameter.TEMPLATES
         },
        {"user_id": "IRIS2", "parameter": "URL_RECLAMA_QUEIXES",
         "valor": "SET",
         "description": "Texto del enlace para reclamar una ficha. Incluye la URL que redirige a la página de "
                        "consulta del estado de una ficha en Quejas ({lang})",
         "name": "Fichas - Enlace reclamación ficha - {lang}",
         "original_description": "Texto del enlace para reclamar una ficha. Incluye la URL que redirige a la página de "
                                 "consulta del estado de una ficha en Quejas ({lang})", "show": True,
         "data_type": False, "visible": False, "category": Parameter.TEMPLATES
         },
        {"user_id": "IRIS2", "parameter": "PEU_CONSULTES",
         "valor": "SET",
         "description": "Pie de mail para consultas {lang}",
         "name": "Comunicaciones - Pie de mail para consultas - {lang}",
         "original_description": "Pie de mail para consultas {lang}", "show": True,
         "data_type": False, "visible": False, "category": Parameter.TEMPLATES
         },
        {"user_id": "IRIS2", "parameter": "TEXTCARTACAP",
         "valor": "SET",
         "description": "Texto de cabecera para las cartas ciudadano/ciudadana {lang}",
         "name": "Comunicaciones - Texto de cabecera para las cartas ciudadano/ciudadana - {lang}",
         "original_description": "Texto de cabecera para las cartas ciudadano/ciudadana {lang}", "show": True,
         "data_type": False, "visible": False, "category": Parameter.TEMPLATES
         },
        {"user_id": "IRIS", "parameter": "MAILSUBJECT",
         "translations": {
             "ca": "Resolució",
             "es": "Resolución",
             "en": "Resolution",
             "gl": "Resolución",
         },
         "description": "Asunto del mail de respuesta - {lang}",
         "name": "Comunicaciones - Texto del asunto del e-mail en {lang}",
         "original_description": "Asunto del mail de respuesta en {lang}", "show": True,
         "data_type": False, "visible": True, "category": Parameter.TEMPLATES
         },
        {"user_id": "IRIS", "parameter": "DISCULPES_RETARD",
         "translations": {
             "ca": "En primer lloc, ens volem disculpar pel retard en la resposta.",
             "es": "En primer lugar, queremos disculparnos por el retraso en la respuesta.",
             "en": "In first place, we apologize for the delay in the response.",
             "gl": "En primeiro lugar, queremos pedir desculpas pola tardanza na resposta.",
         },
         "description": "Texto de disculpa cuando la respuesta ser retarda más de los días establecidos en {lang}",
         "name": "Comunicaciones - Texto de disculpa por el retraso  - {lang}",
         "original_description": "Texto de disculpa cuando la respuesta ser retarda más de los días establecidos "
                                 " {lang}",
         "show": True, "data_type": False, "visible": True, "category": Parameter.TEMPLATES
         },
        {"user_id": "IRIS", "parameter": "DATA_HORA_CITA_PREVIA",
         "translations": {
             "ca": "Dia: data_resolucio a les hora_resol:minuts_resol amb el tècnic Sr/a. persona_encarregada",
             "es": "Dia: data_resolucio a las hora_resol:minuts_resol con el técnico Sr/a. persona_encarregada",
             "en": "Day: data_resolucio at hora_resol:minuts_resol with the technician Mr/s. persona_encarregada.",
             "gl": "SET",
         },
         "description": "Texto de fecha y hora para las citas previas {lang}. "
                        "Se recomienda el formato de fecha: DD/MM/YYYY y hora:HH:MM",
         "name": "Comunicaciones - Texto de fecha y hora para las citar previas - {lang}",
         "original_description": "Texto de fecha y hora para las citas previas {lang}. "
                                 "Se recomienda el formato de fecha: DD/MM/YYYY y hora:HH:MM",
         "show": True, "data_type": False, "visible": True, "category": Parameter.TEMPLATES
         },
        {"user_id": "IRIS", "parameter": "TEXT_LOPD",
         "translations": {
             "ca": "Les seves dades personals s'incorporaran en un fitxer titularitat de la Direcció d'Atenció al "
                   "Ciutadà de l'Ajuntament, amb la finalitat de gestionar el tractament de la seva "
                   "petició i utilitzar-les com a contacte amb els ciutadans i per la millora dels canals. Vostè "
                   "podrà exercir els drets d'accés, rectificació, cancel·lació i oposició en els termes establerts "
                   "a la normativa sobre protecció de dades, adreçant-se per escrit al Registre General de "
                   "l'Ajuntament, indicant en l'assumpte: Exercici de Drets",
             "es": "Sus datos personales se incorporarán a un fichero titularidad de la Dirección de Atención al "
                   "Ciudadano del Ayuntamiento, con la finalidad de gestionar el tratamiento de su petición y usarlos "
                   "como contacto con los ciudadanos y por la mejora de los canales. Usted podrá ejercer los derechos "
                   "de acceso, rectificación, cancelación y oposición en los términos establecidos en la normativa "
                   "sobre protección de datos, dirigiéndose por escrito al Registro General del Ayuntamiento "
                   ", indicando en el asunto: Ejercicio de Derechos",
             "en": "Your personal data will be added to a file owned by the City Council's Attention to the Citizen "
                   "Direction. Thus your request will be managed and your data will be used as a contact and to improve "
                   "the channels. You can exercise your access, rectification, cancellation and protection data term "
                   "opposition rights by addressing the City Council's General Registry, specifying the subject: Right "
                   "Exercise",
             "gl": "SET",
         },
         "description": "Texto LOPD {lang}",
         "name": "Comunicaciones - Texto LOPD - {lang}",
         "original_description": "Texto LOPD {lang}",
         "show": True, "data_type": True, "visible": True, "category": Parameter.TEMPLATES
         },
        {"user_id": "IRIS2", "parameter": "TEXT_LOPD",
         "description": "Texto LOPD ({lang} incorporado en los emails.",
         "translations": {},
         "name": "LOPD - LOPD Mensajes - {lang}",
         "original_description": "",
         "show": True, "data_type": False, "visible": False, "category": Parameter.TEMPLATES,
         },
    ]
    parameters = [
        {"user_id": "IRIS", "parameter": "TEMP_MAX_GROUP",
         "valor": "10",
         "description": "Número de respuestas que se pueden guardar por grupo. El valor debe ser un entero",
         "name": "Respuestas - Máximo número de respuestas por grupo",
         "original_description": "Número de respuestas que se pueden guardar por grupo. El valor debe ser un entero",
         "show": True, "data_type": True, "visible": True, "category": Parameter.TEMPLATES
         },
        {"user_id": "IRIS", "parameter": "TIPUS_RESPOSTA_DEFECTE",
         "valor": "1",
         "description": "Respuestas - Id de tipo de respuesta por defecto. "
                        "El valor debe ser un entero que haga referencia al id de Tipo de respuesta correspondiente.",
         "name": "Id de tipo de respuesta por defecto",
         "original_description": "Id de tipo de respuesta por defecto. "
                                 "El valor debe ser un entero que haga referencia al id de Tipo de respuesta correspondiente.",
         "show": True, "data_type": True, "visible": True, "category": Parameter.TEMPLATES
         },
        {"user_id": "IRIS2", "parameter": CARTA_ICONA,
         "valor": "http://w10.bcn.es/StpQueixesWEB/imatges/AJSignatura.gif",
         "description": "URL del icono del ayuntamiento que se muestra en el pie de firma de las cartas. "
                        "El valor debe ser una URL",
         "name": "IRIS - Carta - Icono",
         "original_description": "URL del icono del ayuntamiento que se muestra en el pie de firma de las cartas. "
                                 "El valor debe ser una URL",
         "show": True, "data_type": False, "visible": False, "category": Parameter.TEMPLATES,
         },
    ]
    NON_VAL = 'SET'
    migrate_old_params()
    for param in translatable_parameters:
        values = param.pop("translations", {})
        for lang, label in settings.LANGUAGES:
            tparam = param.copy()
            tparam['parameter'] = f"{param['parameter']}_{lang.upper()}"
            for key, value in tparam.items():
                if isinstance(value, str):
                    tparam[key] = value.replace('{lang}', str(label))
            tparam["valor"] = values.get(lang, NON_VAL)
            parameters.append(tparam)
    if update_all:
        param_names = []
        for param in parameters:
            param_names.append(param['parameter'])
        create_parameter_list(parameters, update=param_names)
    else:
        create_parameter_list(parameters, ['TEXTCARTAFI_ANG', 'DATA_HORA_CITA_PREVIA_ANG'])
