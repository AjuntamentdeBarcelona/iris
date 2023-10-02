import json

from django.core.management import call_command

from iris_masters.models import Parameter, InputChannel, Support, ApplicantType


def check_parameters(sender, update_all=True, **kwargs):
    parameters = [
        # create parameters
        {"user_id": "IRIS", "parameter": "ALTA_REPITE_MAIL", "valor": "1",
         "description": "Hacer obligatorio la confirmación del email en el alta de fichas de IRIS."
                        "El valor es 0 o 1."
                        "1- Pedir confirmación del email, 0- No pedir confirmación.",
         "name": "Alta Ficha - Repetir email",
         "original_description": "Hacer obligatorio la confirmación del email en el alta de fichas de IRIS."
                                 "El valor es 0 o 1."
                                 "1- Pedir confirmación del email, 0- No pedir confirmación", "show": True,
         "data_type": False, "visible": True, "category": Parameter.CREATE},
        {"user_id": "IRIS", "parameter": "TEMATICA_NO_BLOQUEJADA", "valor": "392",
         "description": "Código de la temática habilitada para los ciudadanos bloqueados.",
         "name": "Temáticas - Habilitación para ciudadanos bloqueados",
         "original_description": "Código de la temática habilitada para los ciudadanos bloqueados.", "show": True,
         "data_type": False, "visible": True, "category": Parameter.CREATE},
        {"user_id": "IRIS", "parameter": "IRIS_TEXT_VALIDACIO", "valor": "8,2",
         "description": "Validar en IRIS, en quejas y consultas se define el mínimo de letras y el mínimo de palabras "
                        "a introducir. "
                        "En caso de querer validar, el valor de este parámetro son dos enteros separados por una coma: "
                        "'Mínimo de letras','mínimo de palabras'. "
                        "En caso de no querer validar el valor debe ser 0.",
         "name": "Validar - Caracteres Web",
         "original_description": "Validar en IRIS, en quejas y consultas se define el mínimo de letras y el mínimo de "
                                 "palabras a introducir. "
                                 "En caso de querer validar, el valor de este parámetro son dos enteros separados por "
                                 "una coma: "
                                 "'Mínimo de letras','mínimo de palabras'. "
                                 "En caso de no querer validar el valor debe ser 0.", "show": True,
         "data_type": False, "visible": True, "category": Parameter.CREATE},
        {"user_id": "IRIS", "parameter": "IRIS_PDA_TEXT_VALIDACIO", "valor": "0",
         "description": "Validar en la PDA los textos de comentarios,se define el mínimo de letras y el mínimo de "
                        "palabras a introducir. "
                        "En caso de querer validar, el valor de este parámetro son dos enteros separados por una coma: "
                        "'Mínimo de letras','mínimo de palabras'. "
                        "En caso de no querer validar el valor debe ser 0.",
         "name": "Validar - Caracteres PDA",
         "original_description": "Validar en la PDA los textos de comentarios,se define el mínimo de letras y el "
                                 "mínimo de palabras a introducir. "
                                 "En caso de querer validar, el valor de este parámetro son dos enteros separados por "
                                 "una coma: "
                                 "'Mínimo de letras','mínimo de palabras'. "
                                 "En caso de no querer validar el valor debe ser 0.", "show": True,
         "data_type": False, "visible": True, "category": Parameter.CREATE},
        {"user_id": "IRIS", "parameter": "IRIS_ENQUESTA", "valor": "1",
         "description": "Id de Temática por defecto que se utilizará desde IRIS para realizar la Encuesta. "
                        "El valor debe ser un entero que haga referencia al id de la Temática correspondiente.",
         "name": "Encuesta - Id de Temática",
         "original_description": "Id de Temática por defecto que se utilizará desde IRIS para realizar la Encuesta. "
                                 "El valor debe ser un entero que haga referencia al id de la Temática correspondiente.",
         "show": True, "data_type": False, "visible": True, "category": Parameter.CREATE},
        {"user_id": "IRIS", "parameter": "IRIS_ENQUESTA_CANAL", "valor": InputChannel.IRIS,
         "description": "Id de Canal de entrada que se utilizará para la encuesta. "
                        "El valor debe ser un entero que haga referencia al id del Canal de entrada correspondiente.",
         "name": "Encuesta - Canal de entrada",
         "original_description": "Id de Canal de entrada que se utilizará para la encuesta. "
                                 "El valor debe ser un entero que haga referencia al id del Canal de entrada "
                                 "correspondiente.",
         "show": True, "data_type": False, "visible": True, "category": Parameter.CREATE},
        {"user_id": "IRIS", "parameter": "IRIS_ENQUESTA_SUPORT", "valor": Support.IRIS,
         "description": "Id del Soporte que se utilizará para la encuesta. El valor debe ser un entero que haga "
                        "referencia al id del Soporte correspondiente.",
         "name": "Encuesta - Soporte",
         "original_description": "Id del Soporte que se utilizará para la encuesta. El valor debe ser un entero que "
                                 "haga referencia al id del Soporte correspondiente.",
         "show": True, "data_type": False, "visible": True, "category": Parameter.CREATE},
        {"user_id": "IRIS", "parameter": "IRIS_ENQUESTA_APPLICANTTYPE", "valor": ApplicantType.OPERADOR,
         "description": "Id de Tipo de solicitante que se utilizará en la encuesta. "
                        "El valor debe ser un entero que haga referencia al id del Tipo de solicitante correspondiente.",
         "name": "Encuesta - Tipo de solicitante",
         "original_description": "Id de Tipo de solicitante que se utilizará en la encuesta. "
                                 "El valor debe ser un entero que haga referencia al id del Tipo de solicitante "
                                 "correspondiente.",
         "show": True, "data_type": False, "visible": True, "category": Parameter.CREATE},
        {"user_id": "IRIS2", "parameter": "API_MAX_FILES", "valor": "5",
         "description": "Número máximo de ficheros adjuntos a la creación de fichas. "
                        "El valor debe ser un entero que indique el máximo de ficheros adjuntos.",
         "name": "Fichas - Número máximo de ficheros en la creación",
         "original_description": "Número máximo de ficheros adjuntos en la creación de fichas. "
                                 "El valor debe ser un entero que indique el máximo de ficheros adjuntos.",
         "show": True, "data_type": False, "visible": True, "category": Parameter.CREATE},

        # Reports parameters
        {"user_id": "IRIS2", "parameter": "LINK_BI", "valor": "http://w2k3svr14/onvision",
         "description": "Enlace a los informes de BI IRIS. El valor debe ser una URL.",
         "name": "Informes - BI - Enlace a la aplicación",
         "original_description": "Enlace a los informes de BI IRIS. El valor debe ser una URL.",
         "show": True, "data_type": False, "visible": True, "category": Parameter.REPORTS},
        {"user_id": "IRIS2", "parameter": "VISUALITZACIO_BI", "valor": "1",
         "description": "Permitir la visualización del enlace a los Informes de BI. "
                        "El valor es 0 o 1."
                        "1- Permitir, 0- No permitir",
         "name": "Informes - BI - Mostrar enlace",
         "original_description": "Permitir la visualización del enlace a los Informes de BI. "
                                 "El valor es 0 o 1."
                                 "1- Permitir, 0- No permitir",
         "show": True, "data_type": False, "visible": True, "category": Parameter.REPORTS},
        {"user_id": "IRIS2", "parameter": "NUM_REGISTRES_QQC", "valor": "5000",
         "description": "Número de filas en el informe Quequiencomo. El valor debe ser un entero.",
         "name": "Informes - Número de filas en el informe Quequiencomo",
         "original_description": "Número de filas en el informe Quequiencomo. El valor debe ser un entero.",
         "show": True, "data_type": False, "visible": True, "category": Parameter.REPORTS},
        {"user_id": "IRIS", "parameter": "NUMERO_MINIM_INCIDENCIES_CIUTADA", "valor": "4",
         "description": "Número mínimo de incidencias por ciudadano para aparecer en el informe de participación. "
                        "El valor debe ser un entero.",
         "name": "Informes - Número mínimo de incidencias ciudadano",
         "original_description": "Número mínimo de incidencias por ciudadano para aparecer en el informe de "
                                 "participación. El valor debe ser un entero.",
         "show": True, "data_type": False, "visible": True, "category": Parameter.REPORTS},
        {"user_id": "IRIS2", "parameter": "NUM_REGISTRES_REPORTS", "valor": "5000",
         "description": "Número de filas para los informes. El valor debe ser un entero.",
         "name": "Informes - Número de filas",
         "original_description": "Número de filas para los informes. El valor debe ser un entero.",
         "show": True, "data_type": False, "visible": True, "category": Parameter.REPORTS},

        # Management parameters
        {"user_id": "IRIS2", "parameter": "SICONABLE", "valor": "1",
         "description":
             "Permitir el envío de información a SICON. "
             "El valor es 0 o 1."
             "1- Permitir, 0- No permitir",
         "name": "Gestión - Permitir envío SICON",
         "original_description": "Permitir el envío de información a SICON. "
             "El valor es 0 o 1."
             "1- Permitir, 0- No permitir",
         "show": True, "data_type": False, "visible": False, "category": Parameter.MANAGEMENT},
        {"user_id": "IRIS", "parameter": "FITXERS_PERMETRE_ANEXAR", "valor": "1",
         "description": "Permitir anexar archivos desde IRIS. "
             "El valor es 0 o 1."
             "1- Permitir, 0- No permitir",
         "name": "Gestión - Permitir Anexar",
         "original_description": "Permitir anexar archivos desde IRIS. "
             "El valor es 0 o 1."
             "1- Permitir, 0- No permitir",
         "show": True, "data_type": False, "visible": True, "category": Parameter.MANAGEMENT},
        {"user_id": "IRIS2", "parameter": "TEMPS_TREBALL_FITXA", "valor": "10",
         "description": "Margen de tiempo de expiración para el bloqueo de una ficha (en minutos). "
                        "El valor debe ser un entero",
         "name": "Fihas - Margen de tiempo de expiración para el bloqueo",
         "original_description": "Margen de tiempo de expiración para el bloqueo de una ficha (en minutos). "
                        "El valor debe ser un entero", "show": True,
         "data_type": False, "visible": True, "category": Parameter.MANAGEMENT},
        {"user_id": "IRIS", "parameter": "MIDA_MAXIMA_FITXERS", "valor": "10",
         "description": "Tamaño máximo de los archivos (en MB) en IRIS. "
                        "El valor debe ser un entero",
         "name": "Gestión - Tamaño Máximo Archivos",
         "original_description": "Tamaño máximo de los archivos (en MB) en IRIS. "
                        "El valor debe ser un entero", "show": True, "data_type": False,
         "visible": True, "category": Parameter.MANAGEMENT},
        {"user_id": "IRIS2", "parameter": "EXTENSIONS_PERMESES_FITXERS",
         "valor": "jpg,jpeg,png,pdf,docx,xls,odt,xlsx,ods",
         "description": "Listado de extensiones de ficheros permitidos. Los valores deben ir separados por comas.",
         "name": "Gestión - Extensions ficheros permitidos",
         "original_description": "Listado de extensiones de ficheros permitidos. Los valores deben ir separados por "
                                 "comas.", "show": True,
         "data_type": False, "visible": True, "category": Parameter.MANAGEMENT},
        {"user_id": "IRIS", "parameter": "DIES_ANTIGUITAT_RESPOSTA", "valor": "30",
         "description": "Número de días a partir del cual se tendrá que reasignar el coordinador para responder. "
            "El valor debe ser un entero",
         "name": "Fichas - Antigüedad máxima para responder",
         "original_description": "Número de días a partir del cual se tendrá que reasignar el coordinador para "
                                 "responder. "
                                 "El valor debe ser un entero",
         "show": True, "data_type": False, "visible": True, "category": Parameter.MANAGEMENT},
        {"user_id": "AM37621", "parameter": "DIES_CANVI_TEMATICA_FORA_AREA_COORD", "valor": "10",
         "description": "Número de días en el ámbito a partir del cual no se podrá modificar la temática de "
                        "una ficha "
                        "fuera del área (para perfil Coordinador). "
                        "El valor debe ser un entero",
         "name": "Temáticas - Días para cambiar a una temática fuera del área con perfil coordinador",
         "original_description": "Número de días en el ámbito a partir del cual no se podrá modificar la temática de "
                                 "una ficha "
                                 "fuera del área (para perfil Coordinador). "
                                 "El valor debe ser un entero",
         "show": True, "data_type": False, "visible": True, "category": Parameter.MANAGEMENT},
        {"user_id": "AM37621", "parameter": "DIES_CANVI_TEMATICA_FORA_AREA", "valor": "8",
         "description": "Número de días en el ámbito a partir del cual no se podrá modificar la temática de "
                        "una ficha "
                        "fuera del área. "
                        "El valor debe ser un entero",
         "name": "Temáticas - Días para cambiar a una temática fuera del área",
         "original_description": "Número de días en el ámbito a partir del cual no se podrá modificar la temática de "
                                 "una ficha "
                                 "fuera del área. "
                                 "El valor debe ser un entero",
         "show": True, "data_type": False, "visible": True, "category": Parameter.MANAGEMENT},
        {"user_id": "IRIS", "parameter": "DIES_PER_RECLAMAR", "valor": "60",
         "description": "Cantidad máxima de días para poder reclamar una ficha cerrada. "
            "El valor debe ser un entero",
         "name": "Fichas - Días para poder reclamar una ficha cerrada",
         "original_description": "Cantidad máxima de días para poder reclamar una ficha cerrada. "
            "El valor debe ser un entero",
         "show": True, "data_type": False, "visible": True, "category": Parameter.MANAGEMENT},
        {"user_id": "AM37621", "parameter": "DIES_AFEGIR_CIUTADA", "valor": "30",
         "description": "Cantidad máxima de días para poder poder añadir un ciudadano a una ficha no tramitada. "
            "El valor debe ser un entero",
         "name": "Fichas - Días para poder añadir un ciudadano a una ficha no tramitada",
         "original_description": "Cantidad máxima de días para poder poder añadir un ciudadano a una ficha no "
                                 "tramitada. "
            "El valor debe ser un entero",
         "show": True, "data_type": False, "visible": False, "category": Parameter.MANAGEMENT},
        {"user_id": "IRIS", "parameter": "DIES_DISCULPES_RETARD", "valor": "30",
         "description": "Número de días para perdir disculpar por el retraso en la respuesta. "
            "El valor debe ser un entero",
         "name": "Respuestas - Días para pedir disculpas en la respuesta",
         "original_description": "Número de días para perdir disculpar por el retraso en la respuesta. "
            "El valor debe ser un entero",
         "show": True, "data_type": False, "visible": False, "category": Parameter.MANAGEMENT},
        {"user_id": "IRIS", "parameter": "FITXES_PARE_RESPOSTA", "valor": "1",
         "description": "Número de fichas padre a partir del cual una ficha se tendrá que reasignar al coordinador "
                        "para responder (es decir, si una ficha tiene más fichas padre que el valor de este "
                        "parámetro). El valor debe ser un entero",
         "name": "Respuestas - Número máximo de reclamaciones para responder",
         "original_description": "Número de fichas padre a partir del cual una ficha se tendrá que reasignar al "
                                 "coordinador "
                        "para responder (es decir, si una ficha tiene más fichas padre que el valor de este "
                        "parámetro). El valor debe ser un entero",
         "show": True, "data_type": False, "visible": False, "category": Parameter.MANAGEMENT},
        {"user_id": "IRIS", "parameter": "PERFIL_DERIVACIO_ALCALDIA", "valor": "266305",
         "description": "Id del Perfil al que van las fichas cuando se derivan al Gabinete de Alcaldía. "
                        "El valor debe ser un entero que haga referencia al id del Perfil correspondiente.",
         "name": "Gabinete de Alcaldía - Perfil de derivación",
         "original_description": "Id del Perfil al que van las fichas cuando se derivan al Gabinete de Alcaldía. "
                        "El valor debe ser un entero que haga referencia al id del Perfil correspondiente.",
         "show": True, "data_type": False, "visible": True, "category": Parameter.DEVELOPMENT},
        {"user_id": "IRIS", "parameter": "SECTOR_GABINET", "valor": "266240",
         "description": "Id del Sector de los perfiles de Gabinete de Alcaldía. Se usa para mostrar las "
                        "fichas para los perfiles que pertenecen a este sector. "
                        "El valor debe ser un entero que haga referencia al id del Sector correspondiente.",
         "name": "Gabinete de Alcaldía - Sector",
         "original_description": "Id del Sector de los perfiles de Gabinete de Alcaldía. Se usa para mostrar las "
                        "fichas para los perfiles que pertenecen a este sector. "
                        "El valor debe ser un entero que haga referencia al id del Sector correspondiente.",
         "show": True, "data_type": False, "visible": False, "category": Parameter.DEVELOPMENT},
        {"user_id": "AM37621", "parameter": "RESPOSTA_CARTA_FIXA", "valor": "266240",
         "description": "Texto a mostrar en el apartado fijo de respuestas por carta.",
         "name": "Respuestas - Texto respuesta fijo carta",
         "original_description": "Texto a mostrar en el apartado fijo de respuestas por carta.", "show": True,
         "data_type": False, "visible": True, "category": Parameter.TEMPLATES},
        {"user_id": "AM37621", "parameter": "DEMANAR_FITXA", "valor": "1",
         "description": "Código de tipo de anulación. Para este tipo de anulación se pedirá el valor del "
                        "identificador de la ficha en anulación.",
         "name": "Fichas - Anulación que requiere identificador",
         "original_description": "Código de tipo de anulación. Para este tipo de anulación se pedirá el valor del "
                        "identificador de la ficha en anulación.", "show": True,
         "data_type": False, "visible": True, "category": Parameter.MANAGEMENT},
        {"user_id": "IRIS", "parameter": "REABRIR_CADUCIDAD", "valor": "17",
         "description": "Id del código de anulación utilizado para anular por caducidad. El valor debe ser un entero "
                        "que haga referencia al id del Código de anulación correspondiente ",
         "name": "Fichas - Código para anular por caducidad",
         "original_description": "Id del código de anulación utilizado para anular por caducidad. El valor debe ser "
                                 "un entero "
                        "que haga referencia al id del Código de anulación correspondiente ",
         "show": True, "data_type": False, "visible": True, "category": Parameter.MANAGEMENT},
        {"user_id": "AM37621", "parameter": "ANULACION_AMBIT_VALUE", "valor": "10",
         "description": "Número de días naturales hasta el cual en su ámbito se permite anular un proceso por "
                        "validación por error y por caducidad. El valor debe ser un entero. Si el valor es -1 no se "
                        "verifica nunca.",
         "name": "Fichas - Días máximos en el ámbito para anular una ficha",
         "original_description": "Número de días naturales hasta el cual en su ámbito se permite anular un proceso por "
                        "validación por error y por caducidad. El valor debe ser un entero. Si el valor es -1 no se "
                        "verifica nunca.",
         "show": True, "data_type": False, "visible": True, "category": Parameter.MANAGEMENT},
        {"user_id": "AM37621", "parameter": "DIES_PER_VALIDACIO", "valor": "1",
         "description": "Número de días en el ámbito del operador antes del cual se puede anular una ficha por "
                        "caducidad. El valor debe ser un entero. Si el valor es - 1 no se aplica.",
         "name": "Fichas - Días mínimos en el ámbito para poder anular una ficha por caducidad ("
                 "pendientes de validar)",
         "original_description": "Número de días en el ámbito del operador antes del cual se puede anular una ficha "
                                 "por caducidad. El valor debe ser un entero. Si el valor es - 1 no se aplica.",
         "show": True, "data_type": False, "visible": True, "category": Parameter.MANAGEMENT},
        {"user_id": "IRIS2", "parameter": "DIES_REASSIGNACIO_FORA_AMBIT", "valor": "5",
         "description": "Número de días en los que se permite reasignar una ficha fuera del ámbito. "
                        "El valor debe ser un entero",
         "name": "Fichas - Días reasignación ficha fuera del ámbito",
         "original_description": "Número de días en los que se permite reasignar una ficha fuera del ámbito. "
                        "El valor debe ser un entero",
         "show": True, "data_type": False, "visible": True, "category": Parameter.MANAGEMENT},
        {"user_id": "IRIS", "parameter": "PERFIL_DAIR_ERROR", "valor": "356417",
         "description": "Identificador del perfil DAIR al que se derivan las fichas si hay un error en la derivación."
                        "Debe ser un entero y debe estar en la tabla de perfiles.",
         "name": "Perfil - DAIR para errores de derivación",
         "original_description": "Identificador del perfil DAIR al que se derivan las fichas si hay un error en la "
                                 "derivación. "
                                 "Debe ser un entero y debe estar en la tabla de perfiles.",
         "show": True, "data_type": False, "visible": True, "category": Parameter.DEVELOPMENT},
        {"user_id": "IRIS2", "parameter": "PERFIL_DAIR_INICIAL", "valor": "406644",
         "description": "Id del perfil de las fichas inicialmente hasta que se derivan. El valor debe ser un entero "
                        "que haga referencia al id del Perfil correspondiente. En caso de error la ficha se queda en "
                        "el grupo",
         "name": "Perfil - DAIR asignación inicial",
         "original_description": "Id del perfil de las fichas inicialmente hasta que se derivan. El valor debe ser un "
                                 "entero "
                        "que haga referencia al id del Perfil correspondiente. En caso de error la ficha se queda en "
                        "el grupo",
         "show": True, "data_type": False, "visible": True, "category": Parameter.DEVELOPMENT},
        {"user_id": "IRIS", "parameter": "CANVI_DETALL_MOTIU", "valor": "19",
         "description": "Id de reasignación que es corresponde con el cambio de temática de una ficha. El valor debe "
                        "ser un entero que haga referencia al id de Cambio de temática correspondiente",
         "name": "Temáticas - Motivo a mostrar en reasignaciones por cambio de temática",
         "original_description": "Id de reasignación que es corresponde con el cambio de temática de una ficha. El "
                                 "valor debe "
                        "ser un entero que haga referencia al id de Cambio de temática correspondiente",
         "show": True, "data_type": False, "visible": False, "category": Parameter.DEVELOPMENT},
        {"user_id": "AM37621", "parameter": "TERMINI_VALIDACIO_COORD", "valor": "10",
         "description": "Número de días en que se permite reasignar a otro sector una ficha pendiente de validar. "
                        "El valor debe ser un entero. "
                        "Si el valor es 0 entonces no se verifica (Coordinadores)",
         "name": "Fichas - Días para poder reasignar una ficha fuera del ámbito con perfil coordinador (Pendientes de "
                 "validar)",
         "original_description": "Número de días en que se permite reasignar a otro sector una ficha pendiente de "
                                 "validar. "
                        "El valor debe ser un entero. "
                        "Si el valor es 0 entonces no se verifica (Coordinadores)",
         "show": True, "data_type": False, "visible": True, "category": Parameter.MANAGEMENT},
        {"user_id": "IRIS2", "parameter": "REPORTS_DAYS_LIMITS", "valor": "366",
         "description": "Número máximo de días límite entre fechas para los informes. El valor debe ser un entero",
         "name": "Informes - Número máximo de días limite entre fechas",
         "original_description": "Número máximo de días límite entre fechas para los informes. "
                                 "El valor debe ser un entero",
         "show": True, "data_type": False, "visible": True, "category": Parameter.REPORTS},
        {"user_id": "IRIS", "parameter": "MAP_SEARCH_RECORDS", "valor": "150",
         "description": "Número de fichas a mostrar en el mapa. El valor debe ser un entero",
         "name": "Fichas - Número de fichas mapa",
         "original_description": "Número de fichas a mostrar en el mapa. El valor debe ser un entero",
         "show": True, "data_type": False, "visible": True, "category": Parameter.MANAGEMENT},
        {"user_id": "IRIS2", "parameter": "DIES_ANS_DEFECTE", "valor": "30",
         "description": "Número de días por defecto para el límite ANS. El valor debe ser un entero",
         "name": "Fichas - Número de días por defecto para el límite ANS",
         "original_description": "Número de días por defecto para el límite ANS. El valor debe ser un entero",
         "show": True, "data_type": False, "visible": True, "category": Parameter.MANAGEMENT},

        # Web parameters
        {"user_id": "IRIS", "parameter": "ELEMENT_FAVORITS", "valor": "10",
         "description": "Número de elementos favoritos que se muestran en quejas y consultas. "
                        "El valor debe ser un entero",
         "name": "Web - Favoritos - Número Elementos",
         "original_description": "Número de elementos favoritos que se muestran en quejas y consultas. "
                        "El valor debe ser un entero",
         "show": True, "data_type": False, "visible": True, "category": Parameter.WEB},
        {"user_id": "IRIS2", "parameter": "HABILITAR_MAPA", "valor": "1",
         "description": "Habilitar el mapa del sistema de seguimiento de incidencias. "
                        "El valor es 0 o 1."
                        "1- Habilitar, 0- Deshabilitar",
         "name": "Web - Habilitar mapa",
         "original_description": "Habilitar el mapa del sistema de seguimiento de incidencias. "
                        "El valor es 0 o 1."
                        "1- Habilitar, 0- Deshabilitar",
         "show": True, "data_type": False, "visible": True, "category": Parameter.WEB},
        {"user_id": "IRIS2", "parameter": "EN_MANTENIMENT", "valor": "0",
         "description": "La web se encuentra en mantenimiento."
                        "El valor es 0 o 1."
                        "1- En mantenimiento, 0- Operativa",
         "name": "Web - En mantenimiento",
         "original_description": "La web se encuentra en mantenimiento."
                        "El valor es 0 o 1."
                        "1- En mantenimiento, 0- Operativa",
         "show": True, "data_type": False, "visible": True, "category": Parameter.WEB},
        {"user_id": "IRIS", "parameter": "SSI_URL",
         "valor": "0",
         "description": "URL que se muestra al inicio de IRIS para acceder al Sistema de Seguimiento de Incidencias. "
                        "El valor debe ser una URL"
                        "Si el valor introducido es 0 entonces se oculta la tabla.",
         "name": "Web - SSI URL",
         "original_description": "URL que se muestra al inicio de IRIS para acceder al Sistema de Seguimiento de "
                                 "Incidencias. "
                        "El valor debe ser una URL"
                        "Si el valor introducido es 0 entonces se oculta la tabla.",
         "show": True, "data_type": False, "visible": True, "category": Parameter.WEB},
        {"user_id": "IRIS", "parameter": "WEB_LOPD_ANG",
         "valor": "We hereby inform you, under Spain's Act on Data Protection, that your personal data will be stored "
                  "in a Public Information and Care Services file, for the purposes of managing the procedure or "
                  "service requested. Your data may also be stored in other City Council files - under the "
                  "provisions laid down in the current regulations in force - whose list and goals may be consulted on "
                  "the City Council web page."
                  "<br/><br/>Certain data currently gathered from several of the City Council's legal files will also "
                  "be included in the Public Information and Care Service file, to enable us to provide you with a "
                  "better multi-channel and personalised public information and care service. You may consult the "
                  "details of the improvements included in this service as well as the list of data to be collected, "
                  "along with the expected goals, on the City Council web page. No data shall be given out to third "
                  "parties, except where required "
                  "by the procedure itself or expressly authorised by the person concerned. You may exercise your "
                  "rights to access, correct, cancel or challenge these data, by writing to the General Registry of "
                  "the City Council.<br/><br/><strong>Tick the following box if "
                  "you do not want</strong> the detailed list of personal data to be included in the Public "
                  "Information and Care Services, whose purpose is to enable the City Council to provide with a better "
                  "multi-channel and personalised information and care service",
         "description": "Texto LOPD en inglés para Quejas y Consultas. Se pueden incluir links a "
                        "páginas del ayuntamiento mediante el tag <a></a>",
         "name": "Web - Texto LOPD Inglés",
         "original_description": "Texto LOPD en inglés para Quejas y Consultas. Se pueden incluir links a "
                        "páginas del ayuntamiento mediante el tag <a></a>",
         "show": True, "data_type": False, "visible": True, "category": Parameter.WEB},

        {"user_id": "IRIS", "parameter": "WEB_LOPD_CAT",
         "valor": "D'acord amb la Llei de Protecció de Dades, us informem que les vostres dades personals "
                  "s'incorporaran al fitxer Serveis d'Informació i Atenció al Ciutadà, amb la finalitat de gestionar "
                  "el tràmit o servei sol·licitat. També poden ser incorporades en altres fitxers de l'Ajuntament de "
                  "Barcelona, d'acord amb la normativa vigent, la relació dels quals i les seves finalitats poden ser"
                  " consultades a la web de l'Ajuntament.<br/><br/>Per poder-vos prestar un millor servei d'informació "
                  "i atenció ciutadana, multicanal i personalitzat, també s'integrarà al fitxer Serveis d'Informació i"
                  " Atenció al Ciutadà determinades dades actualment recollides en diferents fitxers legals de "
                  "l'Ajuntament. Podeu consultar el detall de les millores que incorpora aquest servei i la relació "
                  "de dades que es recolliran juntament amb la finalitat prevista a la web de l'Ajuntament. "
                  "No es cediran dades a "
                  "tercers excepte quan ho requereixi la pròpia tramitació o la persona ho autoritzi expressament. "
                  "Podeu exercitar els drets d'accés, rectificació, cancel·lació i oposició, adreçant-vos per escrit"
                  " al Registre General de l'Ajuntament.<br/><br/><strong>Marqueu "
                  "la següent casella si no voleu</strong> que la relació detallada de dades personals s'integri al "
                  "fitxer Serveis d'Informació i Atenció al Ciutadà a fi de que l'Ajuntament us pugui oferir un "
                  "servei millorat d'informació i atenció, multicanal i personalitzat test prova",
         "description": "Texto LOPD en catalán para Quejas y Consultas. Se pueden incluir links a "
                        "páginas del ayuntamiento mediante el tag <a></a>", "name": "Web - Text LOPD Catalán",
         "original_description": "Texto LOPD en catalán para Quejas y Consultas. Se pueden incluir links a "
                        "páginas del ayuntamiento mediante el tag <a></a>",
         "show": True, "data_type": False, "visible": True, "category": Parameter.WEB},
        {"user_id": "IRIS", "parameter": "WEB_CONTRAER_VALOR", "valor": "10",
         "description": "Valor entero para mostrar desplegados o no los detalles en la pantalla de selección de áreas "
                        "de consultas y "
                        "quejas. Los valores y su efecto son: 0- Siempre desplegados, 1- Sempre plegados, "
                        "n- Se pliega si tiene n elementos o más",
         "name": "Web - Número mínimo de elementos para plegar",
         "original_description": "Valor entero para mostrar desplegados o no los detalles en la pantalla de selección "
                                 "de áreas "
                        "de consultas y "
                        "quejas. Los valores y su efecto son: 0- Siempre desplegados, 1- Sempre plegados, "
                        "n- Se pliega si tiene n elementos o más",
         "show": True, "data_type": False, "visible": True, "category": Parameter.WEB},
        {"user_id": "IRIS", "parameter": "WEB_EXT_ANNEXOS", "valor": "jpg;jpeg;pdf;zip;rar;",
         "description": "Lista de extensiones permitidas para anexar archivos desde la Web y el móvil. "
                        "Los valores deben estar separados por punto y coma (;)",
         "name": "Web - Extensiones de archivo permitidas",
         "original_description": "Lista de extensiones permitidas para anexar archivos desde la Web y el móvil. "
                        "Los valores deben estar separados por punto y coma (;)",
         "show": True, "data_type": False, "visible": True, "category": Parameter.WEB},
        {"user_id": "IRIS", "parameter": "FITXERS_MIDA_MAXIMA_IMG", "valor": "6145",
         "description": "Tamaño máximo en Kb que puede tener una imagen para subir desde la Web. El valor debe ser "
                        "un entero. "
                        "Las imágenes se intentarán reducir (excepto los GIF)",
         "name": "Web - Tamaño máximo para adjuntos",
         "original_description": "Tamaño máximo en Kb que puede tener una imagen para subir desde la Web. "
                                 "El valor debe ser un entero. "
                        "Las imágenes se intentarán reducir (excepto los GIF)",
         "show": True, "data_type": False, "visible": True, "category": Parameter.WEB},
        {"user_id": "IRIS2", "parameter": "URL_COMMUNICACIONS_EXTERNES",
         "valor": "https://atencioenlinia-int.bcn.cat/fitxa/solicitud-informacio",
         "description": "URL para responder las solicitudes de información de las fichas externas a IRIS. "
                        "El valor debe ser una URL",
         "name": "Web - URL comunicaciones externas",
         "original_description": "URL para responder las solicitudes de información de las fichas externas a IRIS. "
                                 "El valor debe ser una URL",
         "show": True, "data_type": False, "visible": True, "category": Parameter.WEB},
        {"user_id": "IRIS2", "parameter": "CANAL_ENTRADA_ATE", "valor": "7",
         "description": "Id del Canal de entrada para las fichas creadas a partir de la web de ATE. El valor debe ser "
                        "un entero que haga referencia al id del Canal de entrada correspondiente",
         "name": "Web - Canal entrada ATE",
         "original_description": "Id del Canal de entrada para las fichas creadas a partir de la web de ATE. "
                                 "El valor debe ser "
                        "un entero que haga referencia al id del Canal de entrada correspondiente",
         "show": True, "data_type": False, "visible": True, "category": Parameter.WEB},
        {"user_id": "IRIS2", "parameter": "MARIO_PARAULES_CERCA_KEYWORDS", "valor": "4",
         "description": "Número de palabras a partir del cual el proxy de Mario hará una búsqueda por palabras clave. "
                        "El valor debe ser un entero",
         "name": "Web - Búsqueda palabras clave proxy Mario",
         "original_description": "Número de palabras a partir del cual el proxy de Mario hará una búsqueda"
                                 " por palabras clave. "
                        "El valor debe ser un entero",
         "show": True, "data_type": False, "visible": True, "category": Parameter.WEB},

        # RECORDS
        {"user_id": "IRIS", "parameter": "SISTEMES_CERCA_PDA", "valor": "5,6,7,10,17",
         "description": "Lista de ids de sistemas para realizar la búsqueda en PDA y Smartphone. "
                        "Los valores deben ser enteros que hagan referencia a los ids de los Sistemas "
                        "correspondientes. Dichos valores deben ir separados por comas",
         "name": "Búsqueda - Sistemas PDA",
         "original_description": "Lista de ids de sistemas para realizar la búsqueda en PDA y Smartphone. "
                        "Los valores deben ser enteros que hagan referencia a los ids de los Sistemas "
                        "correspondientes. Dichos valores deben ir separados por comas",
         "show": True, "data_type": False, "visible": True, "category": Parameter.INTEGRATIONS},
        {"user_id": "IRIS", "parameter": "CERCA_TEMATICA_PER_DEFECTE", "valor": "1972",
         "description": "Id de la Temática que se utilizará por defecto en caso de no encontrar "
                        "ninguna que coincida con la búsqueda. El valor debe ser un entero"
                        "que haga referencia al id de la Temática correspondiente.",
         "name": "Búsqueda - Temática genérica",
         "original_description": "Id de la Temática que se utilizará por defecto en caso de no encontrar "
                        "ninguna que coincida con la búsqueda. El valor debe ser un entero"
                        "que haga referencia al id de la Temática correspondiente.",
         "show": True, "data_type": False, "visible": True, "category": Parameter.RECORDS},
        {"user_id": "IRIS", "parameter": "CERCA_RESULTATS_IRIS", "valor": "10",
         "description": "Número de resultados de búsqueda en la Intranet de IRIS. El valor debe ser un entero",
         "name": "Búsqueda - Número de resultados a mostrar IRIS",
         "original_description": "Número de resultados de búsqueda en la Intranet de IRIS. El valor debe ser un entero",
         "show": True, "data_type": False, "visible": True, "category": Parameter.RECORDS},
        {"user_id": "IRIS", "parameter": "CERCA_SUBSTRING", "valor": "4",
         "description": "Número de caracteres utilizados para realizar la búsqueda también con esta subcadena. "
                        "El valor debe ser un entero",
         "name": "Búsqueda - Tamaño de subcadena para buscar",
         "original_description": "Número de caracteres utilizados para realizar la búsqueda también con esta "
                                 "subcadena. "
                        "El valor debe ser un entero",
         "show": True, "data_type": False, "visible": True, "category": Parameter.RECORDS},
        {"user_id": "AM37621", "parameter": "CERCA_MINIM_PARAULA", "valor": "4",
         "description": "Número mínimo de caracteres de una palabra para realizar la búsqueda. El valor debe ser "
                        "un entero",
         "name": "Búsqueda - Tamaño mínimo de palabra para buscar",
         "original_description": "Número mínimo de caracteres de una palabra para realizar la búsqueda. "
                                 "El valor debe ser un entero",
         "show": True, "data_type": False, "visible": True, "category": Parameter.INTEGRATIONS},
        {"user_id": "IRIS", "parameter": "PDA_CERCA_TIPUS", "valor": "0,2",
         "description": "Lista de ids de Tipo de temática para búsquedas en la PDA según la tabla de tipos de ficha. "
                        "Los valores deben ser enteros y deben ir separados por comas. En casi que el campo valor esté "
                        "vacío solo se usaran las temáticas del perfil",
         "name": "Búsqueda - Tipo de temática para buscar en la PDA",
         "original_description": "Lista de ids de Tipo de temática para búsquedas en la PDA según la tabla "
                                 "de tipos de ficha. "
                        "Los valores deben ser enteros y deben ir separados por comas. En casi que el campo valor esté "
                        "vacío solo se usaran las temáticas del perfil",
         "show": True, "data_type": False, "visible": True, "category": Parameter.INTEGRATIONS},
        {"user_id": "IRIS", "parameter": "CERCA_FITXA_DIAS", "valor": "30",
         "description": "Número de días para buscar fichas cerradas del ciudadano. El valor debe ser un entero",
         "name": "Búsqueda - Días para buscar fichas cerradas del ciudadano",
         "original_description": "Número de días para buscar fichas cerradas del ciudadano. "
                                 "El valor debe ser un entero",
         "show": True, "data_type": False, "visible": True, "category": Parameter.RECORDS},
        {"user_id": "IRIS", "parameter": "NUMPERPAGPETIT", "valor": "7",
         "description": "Número de líneas que aparecen en los listados cortos, como Pendientes de validar o "
                        "Mis tareas. El valor debe ser un entero",
         "name": "Registros - Número de registros por consulta",
         "original_description": "Número de líneas que aparecen en los listados cortos, como Pendientes de validar o "
                        "Mis tareas. El valor debe ser un entero",
         "show": True, "data_type": False, "visible": True, "category": Parameter.RECORDS},
        {"user_id": "IRIS2", "parameter": "PERCENTATGE_PROPERA_EXPIRACIO", "valor": "10",
         "description": "Porcentaje de días para marcar el límite de próxima expiración. "
                        "El valor debe ser un número real entre 0 y 100",
         "name": "Registros - Porcentaje de días límite de próxima expiración",
         "original_description": "Porcentaje de días para marcar el límite de próxima expiración. "
                        "El valor debe ser un número real entre 0 y 100",
         "show": True, "data_type": False, "visible": True, "category": Parameter.RECORDS},

        # other parameters
        {"user_id": "IRIS", "parameter": "DIES_RESPOSTA_CI", "valor": "1",
         "description": "Número de días que tiene el ciudadano para responder a la comunicación intermedia. "
                        "El valor debe ser un entero",
         "name": "Comunicaciones - Días para responder con una comunicación intermedia",
         "original_description": "Número de días que tiene el ciudadano para responder a la comunicación intermedia. "
                        "El valor debe ser un entero",
         "show": True, "data_type": False, "visible": False, "category": Parameter.OTHERS},
        {"user_id": "IRIS2", "parameter": "IRIS_RECORDS_FRONT_URL",
         "valor": "http://localhost:3000/backoffice/records/",
         "description": "URL de fichas en el front de la aplicación. El valor debe ser una URL",
         "name": "Fichas - URL de fichas en el front de la aplicación",
         "original_description": "URL de fichas en el front de la aplicación. El valor debe ser una URL",
         "show": True, "data_type": False, "visible": False, "category": Parameter.OTHERS},
        {"user_id": "IRIS2", "parameter": "RECOLLIDA_MOBLES_HORARIS", "valor": "20:00 a 22:00 h",
         "description": "Horario recogida de muebles. El valor es un texto de formato libre, se recomienda que la "
                        "estructura sea un rango entre horas con formato 'HH:MM a HH:MM'",
         "name": "Muebles - Horario de recogida de mobles",
         "original_description": "Horario recogida de muebles. El valor es un texto de formato libre, "
                                 "se recomienda que la "
                        "estructura sea un rango entre horas del estilo 'HH:MM a HH:MM'",
         "show": True, "data_type": False, "visible": True, "category": Parameter.OTHERS},
        {"user_id": "IRIS2", "parameter": "RECOLLIDA_MOBLES_HORA", "valor": "20:00",
         "description": "Hora de recogida de muebles. El valor es un texto de formato libre, "
                        "se recomienda que la "
                        "estructura sea una hora con formato 'HH:MM'",
         "name": "Muebles - Hora de recogida de muebles",
         "original_description": "Hora de recogida de muebles. El valor es un texto de formato libre, "
                        "se recomienda que la "
                        "estructura sea una hora con formato 'HH:MM'",
         "show": True, "data_type": False, "visible": True, "category": Parameter.OTHERS},
        {"user_id": "IRIS2", "parameter": "PUBLIC_API_MAX_FILES", "valor": "3",
         "description": "Número máximo de ficheros adjuntos en la creación de fichas en la API pública. "
                        "El valor debe ser un número entero",
         "name": "Fichas - Número máximo de ficheros adjuntos en la creación ficha pública",
         "original_description": "Número máximo de ficheros adjuntos en la creación de fichas en la API pública. "
                        "El valor debe ser un número entero",
         "show": True, "data_type": False, "visible": True, "category": Parameter.OTHERS},
        {"user_id": "IRIS2", "parameter": "TIPUS_SOLICITANT_NO_CARREGA_CIUTADA", "valor": "0/1/2",
         "description": "Ids de los tipos de solicitante para los cuales no se cargará el ciudadano "
                        "por defecto en el alta de las fichas. Los valores deben ser enteros que hagan referencia "
                        "a los ids de Tipo de solicitante correspondientes separados por barras (/)",
         "name": "Solicitante - Tipos que no cargan el ciudadano por defecto",
         "original_description": "Ids de los tipos de solicitante para los cuales no se cargará el ciudadano "
                        "por defecto en el alta de las fichas. Los valores deben ser enteros que hagan referencia "
                        "a los ids de Tipo de solicitante correspondientes separados por barras (/)",
         "show": True, "data_type": False, "visible": True, "category": Parameter.CREATE},
        {"user_id": "IRIS2", "parameter": "WEB_SMARTPHONE_CONFIG", "valor": json.dumps({
            "gub": {"applications": [6], "support": 14, "record_types": [0, 1, 4],
                    "full_tree": False, "applicant_type": 3},
            "aver": {"applications": [10], "support": 14, "record_types": [0, 1, 4],
                     "full_tree": False, "applicant_type": 26},
            "suma": {"applications": [5], "support": 14, "record_types": [0, 1, 4],
                     "full_tree": False, "applicant_type": 3},
            "impj": {"applications": [7], "support": 14, "record_types": [0, 1, 4],
                     "full_tree": False, "applicant_type": 3},
        }),
         "description": "JSON de configuración de aplicaciones de alta móvil en web. (Plan B Gub)"
                        "El valor debe ser un objeto en formato json",
         "name": "Web - JSON Alta Intranet para smartphones",
         "original_description": "JSON de configuración de aplicaciones de alta móvil en web. (Plan B Gub). "
                                 "El valor debe ser un objeto en formato json",
         "show": True, "data_type": False, "visible": True, "category": Parameter.DEVELOPMENT},
        {"user_id": "IRIS2", "parameter": "XALOC_FECHA", "valor": "0",
         "description": "Xaloc - Fecha para la migración de XALOC",
         "name": "XALOC_FECHA", "original_description": "",
         "show": True, "data_type": False, "visible": False, "category": Parameter.INTEGRATIONS},
        {
            "user_id": "IRIS2", "parameter": "HABILITAR_CITYOS", "valor": True,
            "description": "Cityos - habilitar integración. "
                           "El valor es 0 o 1."
                           "1- Habilitar, 0- Deshabilitar",
            "name": "Cityos - habilitar integración",
            "original_description": "Cityos - habilitar integración. "
                           "El valor es 0 o 1."
                           "1- Habilitar, 0- Deshabilitar", "show": True,
            "data_type": False, "visible": False, "category": Parameter.INTEGRATIONS
        },
        {
            "user_id": "IRIS2", "parameter": "AGRUPACIO_PER_DEFECTE", "valor": "IRIS",
            "description": "DNI del ciudadano por defecto",
            "name": "Alta - Solicitante - DNI del ciudadano por defecto",
            "original_description": "DNI del ciudadano por defecto", "show": False,
            "data_type": False, "visible": True, "category": Parameter.CREATE
        },
        {
            "user_id": "IRIS2", "parameter": "DEFAULT_APPLICANT_TYPE", "valor": "0",
            "description": "ID del tipo de solicitante por defecto.",
            "name": "Solicitante - Tipo de solicitante por defecto",
            "original_description": "DNI del ciudadano por defecto", "show": True,
            "data_type": False, "visible": True, "category": Parameter.CREATE
        }
    ]

    call_command("invalidate_cachalot", "iris_masters.Parameter")

    if update_all:
        param_names = []
        for param in parameters:
            param_names.append(param['parameter'])
        create_parameter_list(parameters, update=param_names)
    else:
        create_parameter_list(parameters, update=['IRIS_ENQUESTA_CANAL'])

    create_category = ["MIB_CERCA_DNI", "MIB_DIA_ALTAS_AUTO", "MIB_MAX_INTENTS_ALTA", "MIB_FRECUENCIA_ALTAS_AUTO",
                       "CALL_BROKER"]
    categorize_parameters(create_category, Parameter.CREATE)

    management_category = ["SMSENABLE", "MAILENABLE", "CAMI_SICON", "PLANTILLA_SICON", "PDF_PAGINES"]
    categorize_parameters(management_category, Parameter.INTEGRATIONS)

    # deprecate parameters
    deprecated_category = ["SERVEI_MAPIFICACIO_MAXIM_PETICIONS", "HOSTNAME_SERVIDOR_INTERNET",
                           "HOSTNAME_SERVIDOR_EMAIL", "SSI_NOM_SERVIDOR", "SSI_HABILITA", "SSI_NUMERO_MAXIM_HISTORIC",
                           "SSI_NUMERO_MAXIM_PETICIONS", "CERCA_NO_PER_DEFECTE", "VALID_IPS_ICINGIRIS_WS",
                           "WEB_RESIZE_JPG", "FITXERS_MIN_WIDTH", "WEB_HIDE_MASK", "WEB_MOSTRA_MASK",
                           "FITXERS_MIDA_MAXIMA_PER_FITXA", "CERCA_NO_PER_DEFECTE", "CERCA_COINCIDENCIES", "CERCA",
                           "CERCA_QUEIXES", "CERCA_IRIS", "CERCA_CONSULTES", "CACHE_UP_INTERNET",
                           "CADUCITAT_ANUNCIS_DIES", "DIA_ENVIO_MAIL_AUTO", "LINK_BI_IRIS", "RECLAMA_TIPUS_RESOLUCIO",
                           "DIES_PROPERA_EXPIRACIO", "NUM_TIPUS_RESPOSTA", "MOVIL_NOUS_TAGS", "WEB_CONTRAER_VALOR_ULLS",
                           "SSI_FILTRE_MAX_SUPORTS"]
    categorize_parameters(deprecated_category, Parameter.DEPRECATED)
    Parameter.objects.filter(category=Parameter.DEPRECATED).update(visible=False, show=False)

    warm_up_parameters_cache(parameters)


def create_parameter_list(parameters, update=None):
    for param in parameters:
        parameter, _ = Parameter.objects.get_or_create(parameter=param["parameter"], defaults={
            "user_id": param["user_id"], "valor": param["valor"], "description": param["description"],
            "name": param["name"], "original_description": param["original_description"], "show": param["show"],
            "data_type": param["data_type"], "visible": param["visible"], "category": param["category"]})

        parameter.visible = param["visible"]
        parameter.category = param["category"]
        if update and parameter.parameter in update:
            parameter.description = param["description"]
            parameter.original_description = param["original_description"]
            parameter.name = param["name"]
        parameter.save()


def warm_up_parameters_cache(parameters):
    # make queries in order to set Parameter get on cachalot cache
    for param in parameters:
        Parameter.objects.get(parameter=param["parameter"])


def categorize_parameters(parameters_list, category):
    Parameter.objects.filter(parameter__in=parameters_list).update(category=category)
