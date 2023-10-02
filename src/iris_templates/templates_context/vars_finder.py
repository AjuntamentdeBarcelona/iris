from abc import ABCMeta

from main.utils import rgetattr


class VariableFinder(metaclass=ABCMeta):
    """
    Base class to generate a template context for iris templates
    """
    variables = []

    def __init__(self, *args, **kwargs):
        pass

    def get_vars_for_templates(self) -> list:
        """
        :return: Iterables of variables for templates
        """
        return self.variables

    def get_values(self, ctx, required_variables) -> dict:
        """
        Giving a list of required variables updates the context of a template with variables values

        :param ctx: Dict with the context of the template
        :param required_variables: List of variables to add to the context
        :return: Updated context dict
        """
        return ctx


class MapVariableFinder(VariableFinder, metaclass=ABCMeta):
    """
    Var finder that accepts mapping values by using a dict. In addition, it allows direct mapping or a more complex one,
    by defining a function for processing the output.
    """
    variables = {}

    def __init__(self, obj, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.obj = obj

    def get_vars_for_templates(self) -> list:
        """
        :return: List of variables for templates
        """
        flat_vars = [var for var, value in list(self.variables.items()) if not isinstance(value, type)]
        # Iter nested finders
        for val in self.variables.values():
            if isinstance(val, type):
                flat_vars += val({}).get_vars_for_templates()
        return flat_vars

    def get_values(self, ctx, required_variables) -> dict:
        """
        Giving a list of required variables updates the context of a template with variables values

        :param ctx: Dict with the context of the template
        :param required_variables: List of variables to add to the context
        :return: Updated context dict
        """

        for variable in required_variables:
            if variable in self.variables and variable not in ctx:
                value = self.get_variable_from_mapping(ctx, variable)
                if value is not None and not isinstance(value, type):
                    ctx[variable] = str(value)
        self.get_nested_values(ctx, required_variables)
        return ctx

    def get_nested_values(self, ctx, required_variables) -> dict:
        """
        Adds the nested values to the context, only if they are required.
        :param ctx:
        :param required_variables:
        :return: Context expanded with the nested vars.
        """
        nested = {var_name: vf for var_name, vf in self.variables.items() if isinstance(vf, type)}
        for var_name, nf_class in nested.items():
            # Create an instance without object
            nested_available_vars = nf_class({}).get_vars_for_templates()
            # Try to obtain values only if there is one required
            if set(required_variables).intersection(nested_available_vars):
                nf_class(self.get_variable_value(var_name)).get_values(ctx, required_variables)
        return ctx

    def get_variable_from_mapping(self, ctx, variable):
        """
        There can be two types of mapping: simple getattr or complex. While simple follow a simple mapping structure of
        {dst_attr: origin_attr}, the filtered can add further configurations in this fashion:
        {dst_attr: {attr: orig_attr, filter: date}}

        :param ctx:
        :param variable:
        :return:
        """
        var_config = self.variables[variable]
        attr = var_config['attr'] if isinstance(var_config, dict) else var_config
        if isinstance(attr, str):
            value = self.get_variable_value(attr)
            if isinstance(var_config, dict) and value and var_config.get('filter'):
                return var_config.get('filter')(value)
            return value
        return attr

    def get_variable_value(self, attribute):
        """
        :param attribute: Flat attribute or nested object attribute separated by .
        :return: Attribute value
        """
        if attribute == '':
            return attribute
        return rgetattr(self.obj, attribute, None)
