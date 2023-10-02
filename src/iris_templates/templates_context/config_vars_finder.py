from iris_masters.models import Parameter
from iris_templates.data_checks.visible_parameters import CARTA_ICONA

from iris_templates.templates_context.vars_finder import VariableFinder


class ConfigVariableFinder(VariableFinder):
    """
    Class to add to a template context for iris templates the configuration variables
    """
    variables = ['DIES_RESPOSTA_CI', 'DIES_PER_RECLAMAR', 'DIES_ANTIGUITAT_RESPOSTA', 'PERFIL_DERIVACIO_ALCALDIA',
                 CARTA_ICONA]

    def get_vars_for_templates(self) -> list:
        return [item.lower() for item in super().get_vars_for_templates()]

    def get_values(self, ctx, required_variables):
        """
        Giving a list of required variables updates the context of a template with variables values

        :param ctx: Dict with the context of the template
        :param required_variables: List of variables to add to the context
        :return: Updated context dict
        """
        for variable in required_variables:
            if variable.upper() in self.variables and variable not in ctx:
                value = Parameter.get_parameter_by_key(variable.upper())
                if value is not None:
                    ctx[variable.lower()] = value
        if 'icona_ajuntament' not in ctx and CARTA_ICONA.lower() in ctx:
            ctx['icona_ajuntament'] = '<img src="{}" alt="Ajuntament de Barcelona" />'.format(ctx[CARTA_ICONA.lower()])
        return ctx
