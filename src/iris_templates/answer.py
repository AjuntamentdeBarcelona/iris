from django.utils.html import linebreaks

from iris_masters.models import Parameter
from iris_templates.template_params import get_template_param, get_parameter_key


def get_footer(group, lang):
    PARAMS = [
        get_parameter_key(lang, 'TEXTCARTAFI'),
        get_parameter_key(lang, 'TEXTCARTASIGNATURA'),
        get_parameter_key(lang, 'PEU_CONSULTES'),
    ]
    valors = {p.parameter: p.valor for p in Parameter.objects.filter(parameter__in=PARAMS)}
    valors = [linebreaks(valors[p]).replace('\n', '') for p in PARAMS]
    return ''.join(valors[:1] + ['<p>' + group.signature + '</p>']) + '<p></p>'.join(valors[1:])


def get_signature(group, lang):
    PARAMS = [
        get_parameter_key(lang, 'TEXTCARTAFI'),
        get_parameter_key(lang, 'TEXTCARTASIGNATURA'),
    ]
    valors = {p.parameter: p.valor for p in Parameter.objects.filter(parameter__in=PARAMS)}
    valors = [valors[p] for p in PARAMS]
    return ''.join(valors[:1] + ['\n\n' + group.signature + '\n\n'] + valors[1:])


def get_header(group, lang):
    return get_template_param(lang, 'TEXTCARTACAP')
