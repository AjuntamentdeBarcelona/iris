import pytest
from integrations.services.gcod.services import GcodServices


@pytest.mark.django_db
class TestHooks:

    @pytest.mark.external_integration_test
    def test_districts(self):
        result = GcodServices().districts()
        assert result['ReturnCode'] == 1

    @pytest.mark.external_integration_test
    def test_streets(self):
        result = GcodServices().streets()
        assert result['ReturnCode'] == 1

    @pytest.mark.external_integration_test
    def test_streets_variable(self):
        result = GcodServices().streets(variable='x')
        assert result['ReturnCode'] == 1

    @pytest.mark.external_integration_test
    def test_type_streets(self):
        result = GcodServices().type_streets()
        assert result['ReturnCode'] == 1

    @pytest.mark.external_integration_test
    def test_neighborhood(self):
        result = GcodServices().neighborhood()
        assert result['ReturnCode'] == 1

    @pytest.mark.external_integration_test
    def test_neighborhood_district(self):
        result = GcodServices().neighborhood_district('01')
        assert result['ReturnCode'] == 1
