from iris_templates.data_checks.visible_parameters import CARTA_ICONA
from iris_templates.templates_context.config_vars_finder import ConfigVariableFinder
from iris_templates.templates_context.record_card_vars_finder import RecordCardVariableFinder


class IrisVariableFinder:
    """
    Constructs all the variables available for IRIS templates.
    """
    FINDERS_CLASSES = [ConfigVariableFinder, RecordCardVariableFinder]

    def __init__(self, record_card=None):
        self.finders = [var_finder(record_card) for var_finder in self.FINDERS_CLASSES]

    def get_vars_for_templates(self) -> list:
        """
        :return: List of variables for templates
        """
        variables_list = []
        for var_finder in self.finders:
            variables_list += var_finder.get_vars_for_templates()
        return variables_list + [CARTA_ICONA]

    def get_values(self, ctx, required_variables) -> dict:
        """
        Giving a list of required variables updates the context of a template with variables values

        :param ctx: Dict with the context of the template
        :param required_variables: List of variables to add to the context
        :return: Updated context dict
        """
        for var_finder in self.finders:
            var_finder.get_values(ctx, required_variables)
        return ctx


class IrisApplicantCommunicationsVariableFinder(IrisVariableFinder):

    def get_values(self, ctx, required_variables) -> dict:
        ctx = super().get_values(ctx, required_variables)
        ctx.pop("icona_ajuntament", None)
        return ctx
