import pytest

from iris_masters.models import Parameter
from iris_templates.data_checks.migrate_old_params import migrate_old_params


@pytest.mark.django_db
class TestMigrateOldParams:
    VALUE = 'TEST_MIGRATE'

    @pytest.mark.parametrize('param,rename', (
        ('URL_RECLAMA_QUEIXES_ANG', 'URL_RECLAMA_QUEIXES_EN'),
        ('TEXT_LOPD_CAT', 'TEXT_LOPD_CA'),
        ('DISCULPES_RETARD_CAT', 'DISCULPES_RETARD_CA'),
        ('DISCULPES_RETARD_CAST', 'DISCULPES_RETARD_ES'),
        ('PEU_CONSULTES_CAST', 'PEU_CONSULTES_ES'),
    ))
    def test_migrate_params(self, param, rename):
        self.when_parameter_exists(param)
        migrate_old_params()
        new_p = self.should_be_normalized(new_name=rename)
        self.should_keep_value(new_p)

    def when_parameter_exists(self, param):
        Parameter.objects.create(parameter=param, valor=self.VALUE, description='Desc')

    def should_be_normalized(self, new_name):
        try:
            return Parameter.objects.get(parameter=new_name)
        except Parameter.DoesNotExist:
            assert False, f'New parameter {new_name} should exist'

    def should_keep_value(self, param):
        assert param.valor == self.VALUE, 'Parameter value changed during renaming'
