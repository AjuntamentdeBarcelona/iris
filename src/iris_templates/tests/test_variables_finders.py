import pytest

from iris_masters.models import Parameter
from iris_templates.templates_context.config_vars_finder import ConfigVariableFinder
from iris_templates.templates_context.record_card_vars_finder import RecordCardVariableFinder
from record_cards.tests.utils import CreateRecordCardMixin
from communications.tests.utils import load_missing_data


@pytest.mark.django_db
class TestConfigVariableFinder:

    @pytest.mark.parametrize("variable",
                             ("DIES_RESPOSTA_CI", "DIES_PER_RECLAMAR", "DIES_ANTIGUITAT_RESPOSTA",
                              "PERFIL_DERIVACIO_ALCALDIA"))
    def test_variables_list(self, variable):
        assert variable.lower() in ConfigVariableFinder().get_vars_for_templates()

    @pytest.mark.parametrize("variables", (
            [],
            ["DIES_RESPOSTA_CI"],
            ["DIES_RESPOSTA_CI", "DIES_PER_RECLAMAR"],
            ["DIES_RESPOSTA_CI", "DIES_PER_RECLAMAR", "DIES_ANTIGUITAT_RESPOSTA"],
            ["DIES_RESPOSTA_CI", "DIES_PER_RECLAMAR", "DIES_ANTIGUITAT_RESPOSTA", "PERFIL_DERIVACIO_ALCALDIA"],
    ))
    def test_config_variable_finder(self, variables):
        config_context = {}
        for var in variables:
            Parameter.objects.get_or_create(parameter=var, defaults={"valor": "value", "name": var,
                                                                     "original_description": var})

        config_finder = ConfigVariableFinder()
        config_context = config_finder.get_values(config_context, variables)
        for var in variables:
            assert var.lower() in config_context


@pytest.mark.django_db
class TestRecordCardVariableFinder(CreateRecordCardMixin):

    @pytest.mark.parametrize("variable", ("codi_fitxa", "departament_fitxa", "nombre_reclamacions"))
    def test_variables_list(self, variable):
        assert variable in RecordCardVariableFinder({}).get_vars_for_templates()

    @pytest.mark.parametrize("variables", (
            ["url_reclama_queixes"],
            ["url_reclama_queixes", "codi_fitxa"],
            ["url_reclama_queixes", "codi_fitxa", "departament_fitxa"],
            ["url_reclama_queixes", "codi_fitxa", "departament_fitxa", "nombre_reclamacions"]
    ))
    def test_record_card_variable_finder(self, variables):
        load_missing_data()
        Parameter.objects.get_or_create(parameter='URL_RECLAMA_QUEIXES_CA', defaults={'valor': 'test'})
        Parameter.objects.get_or_create(parameter='URL_RECLAMA_QUEIXES_ES', defaults={'valor': 'test'})
        record_card = self.create_record_card()
        record_finder = RecordCardVariableFinder(record_card)
        record_context = {}
        record_context = record_finder.get_values(record_context, variables)
        for var in variables:
            assert var in record_context

    @pytest.mark.parametrize("send_multirecord_from", (True, False))
    def test_multirecords_codes(self, send_multirecord_from):
        load_missing_data()
        Parameter.objects.get_or_create(parameter='URL_RECLAMA_QUEIXES_CA', defaults={'valor': 'test'})
        Parameter.objects.get_or_create(parameter='URL_RECLAMA_QUEIXES_ES', defaults={'valor': 'test'})
        multi_record_card = self.create_record_card()
        multi_record_card.is_multirecord = True
        multi_record_card.save()
        record_cards = [self.create_record_card(multirecord_from=multi_record_card) for _ in range(5)]
        if send_multirecord_from:
            record_finder = RecordCardVariableFinder(multi_record_card)
        else:
            record_finder = RecordCardVariableFinder(record_cards[0])
        record_context = {}
        variables = ["codis_peticions_ciutada", "url_reclama_queixes"]
        record_context = record_finder.get_values(record_context, variables)
        assert "codis_peticions_ciutada" in record_context
        assert multi_record_card.normalized_record_id in record_context["codis_peticions_ciutada"]
        for record_card in record_cards:
            assert record_card.normalized_record_id in record_context["codis_peticions_ciutada"]
