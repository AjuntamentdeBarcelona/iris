"""
List of dynamic Parameters that must exists in order to build the different answers.
Since they generate answers for the citizens, they must be translated and mapped.
"""
from django.utils.timezone import localtime

from iris_masters.models import Parameter
from iris_templates.templates_context.var_filters import date, time

APPOINTMENT_TEMPLATE = 'DATA_HORA_CITA_PREVIA'
URL_RECLAMA_QUEIXES = 'URL_RECLAMA_QUEIXES'
DISCULPES_RETARD = 'DISCULPES_RETARD'
TEXTCARTACAP = 'TEXTCARTACAP'

"""
Old template param mapping. Can be used for migrating to new parameter names.
"""
TEMPLATE_PARAMS = {
    'es': {
        'MAILSUBJECT': 'MAILSUBJECT',
        'TEXTCARTACAP': 'TEXTCARTACAP_CAST',
        'DISCULPES_RETARD': 'DISCULPES_RETARD_CAST',
        'APPOINTMENT_TEMPLATE': 'DATA_HORA_CITA_PREVIA_CAST',
        'TEXTCARTAFI': 'TEXTCARTAFI_CAST',
        'URL_RECLAMA_QUEIXES': 'URL_RECLAMA_QUEIXES_CAST',
        'TEXTCARTASIGNATURA': 'TEXTCARTASIGNATURA',
        'PEU_CONSULTES': 'PEU_CONSULTES_CAST',
        'TEXT_LOPD': 'TEXT_LOPD_CAST',
        'ACUSAMENT_REBUT': 'ACUSAMENT_REBUT_CAST',
        'ACUSAMENT_MULTI': 'ACUSAMENT_MULTI_CAST',
        'PLANTILLA_DERIVACIO_EXTERNA': 'PLANTILLA_DERIVACIO_EXTERNA',
    },
    'ca': {
        'MAILSUBJECT': 'MAILSUBJECT',
        'TEXTCARTACAP': 'TEXTCARTACAP',
        'DISCULPES_RETARD': 'DISCULPES_RETARD_CAT',
        'APPOINTMENT_TEMPLATE': 'DATA_HORA_CITA_PREVIA',
        'TEXTCARTAFI': 'TEXTCARTAFI',
        'URL_RECLAMA_QUEIXES': 'URL_RECLAMA_QUEIXES',
        'TEXTCARTASIGNATURA': 'TEXTCARTASIGNATURA',
        'PEU_CONSULTES': 'PEU_CONSULTES_CAT',
        'TEXT_LOPD': 'TEXT_LOPD_CAT',
        'ACUSAMENT_REBUT': 'ACUSAMENT_REBUT_CAT',
        'ACUSAMENT_MULTI': 'ACUSAMENT_MULTI_CAT',
        'PLANTILLA_DERIVACIO_EXTERNA': 'PLANTILLA_DERIVACIO_EXTERNA',
    },
    'en': {
        'MAILSUBJECT': 'MAILSUBJECT',
        'TEXTCARTACAP': 'TEXTCARTACAP_ANG',
        'DISCULPES_RETARD': 'DISCULPES_RETARD_ANG',
        'APPOINTMENT_TEMPLATE': 'DATA_HORA_CITA_PREVIA_ANG',
        'TEXTCARTAFI': 'TEXTCARTAFI_ANG',
        'URL_RECLAMA_QUEIXES': 'URL_RECLAMA_QUEIXES_ANG',
        'TEXTCARTASIGNATURA': 'TEXTCARTASIGNATURA_ANG',
        'PEU_CONSULTES': 'PEU_CONSULTES_ANG',
        'TEXT_LOPD': 'TEXT_LOPD_ANG',
        'ACUSAMENT_MULTI': 'ACUSAMENT_MULTI_ANG',
        'ACUSAMENT_REBUT': 'ACUSAMENT_REBUT_ANG',
        'PLANTILLA_DERIVACIO_EXTERNA': 'PLANTILLA_DERIVACIO_EXTERNA',
    }
}


def get_parameter_key(lang, name):
    return f"{name.upper()}_{lang.upper()}"


def get_required_param_names(lang, required):
    return {
        var_name: get_parameter_key(lang, param_name)
        for var_name, param_name in required.items()
    }


def get_required_params(lang, required):
    template_vars = get_required_param_names(lang, required)
    params = Parameter.objects.filter(parameter__in=template_vars.values())
    params = {p.parameter: p.valor for p in params}
    return {var_name: params[param_name] for var_name, param_name in template_vars.items()}


def get_template_param(lang, name):
    return Parameter.get_parameter_by_key(get_parameter_key(lang, name))


def get_appointment_text(resolution, appointment_template) -> str:
    resolution_date = localtime(resolution.resolution_date)
    replacements = {
        "data_resolucio": date(resolution_date, "dd/MM/Y"),
        "hora_resol": time(resolution_date, "H"),
        "minuts_resol": time(resolution_date, "i"),
        "persona_encarregada": resolution.service_person_incharge
    }
    for key, value in replacements.items():
        appointment_template = appointment_template.replace(key, value)
    return appointment_template
