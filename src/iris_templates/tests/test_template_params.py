import pytest

from iris_templates.template_params import get_required_param_names


class TestTemplateParams:

    @pytest.mark.parametrize('param,lang,translated', (
        ('PEU_CONSULTES', 'es', 'PEU_CONSULTES_ES'),
        ('PEU_CONSULTES', 'ca', 'PEU_CONSULTES_CA'),
        ('PEU_CONSULTES', 'en', 'PEU_CONSULTES_EN'),
    ))
    def test_get_required_param_names(self, param, lang, translated):
        result = get_required_param_names(lang, {'var': param})
        assert result['var'] == translated, f'Expected translated parameter {translated}, received: {param}'
