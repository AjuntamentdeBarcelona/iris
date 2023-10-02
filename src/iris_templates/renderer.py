import re
from abc import abstractmethod, ABCMeta

from iris_templates.templates_context.context import IrisVariableFinder


class BaseTemplateRenderer(metaclass=ABCMeta):
    """
    Renderers are responsible for creating the final version of the template, by replacing all the variable marks with
    the according value.
    """

    def __init__(self, record_card, var_finder_cls=IrisVariableFinder):
        self.record_card = record_card
        self.var_finder = var_finder_cls(record_card)
        self.context = {}

    @property
    def record_card(self):
        return self._record_card

    @record_card.setter
    def record_card(self, record_card):
        self._record_card = record_card
        self.context = {}

    @abstractmethod
    def render(self, template):
        return template

    def get_context(self, template):
        used_vars = self.get_used_vars(template)
        self.var_finder.get_values(self.context, used_vars)
        # Fill the missing vars with its own var name, wrap the key name
        return {self.wrap_var_key(used_var): self.context.get(used_var, self.wrap_var_key(used_var))
                for used_var in used_vars}

    def wrap_var_key(self, var_key):
        return var_key

    def get_used_vars(self, template):
        """
        :return: A list of vars used in template.
        :rtype: list
        """
        return self.var_finder.get_vars_for_templates()


def render_iris_1(template, ctx):
    """
    Backward compatible IRIS1 template render system.
    :param template: Template to render
    :param ctx: Vars
    :type: dict
    :return: Rendered templates.
    """
    if template is None:
        rendered = 'No template text to be rendered, this is a non desired behavior in production. ' \
                   'This is intended when running tests.'
    else:
        rendered = template
    for key, value in ctx.items():
        rendered = re.sub(r'\b{}\b'.format(key), str(value).replace("\\", ""), rendered)
    return rendered.replace('<p><br></p>', '<p></p>')


class Iris1TemplateRenderer(BaseTemplateRenderer):
    """
    Backward compatible with IRIS1 template renderer.
    """

    def render(self, template):
        if not self.context:
            self.context = self.get_context(template)
        return render_iris_1(template, self.context)


class RegexpTemplateRenderer(BaseTemplateRenderer):
    """
    Renders a template which vars are wrapped between two delimiters.
    """
    DEFAULT_OPEN_DELIMITER = '_'
    DEFAULT_CLOSE_DELIMITER = '_'

    def __init__(self, record_card, open_delimiter=None, close_delimiter=None, regexp=None,
                 var_finder_cls=IrisVariableFinder):
        super().__init__(record_card)
        self.record_card = record_card
        self.open_delimiter = open_delimiter or self.DEFAULT_OPEN_DELIMITER
        self.close_delimiter = close_delimiter or self.DEFAULT_CLOSE_DELIMITER
        if regexp:
            self.regexp = re.compile(regexp)
        else:
            self.regexp = re.compile(r'({}\w+{})'.format(self.open_delimiter, self.close_delimiter))
        self.var_finder = var_finder_cls(record_card)
        self.context = {}

    def render(self, template):
        ctx = self.get_context(template)

        def replacement(match):
            return '{' + match.group(1)[1:-1].lower() + '}'

        python_template = self.regexp.sub(replacement, template)
        return python_template.format(**ctx)

    def get_context(self, template):
        used_vars = self.get_used_vars(template)
        self.var_finder.get_values(self.context, used_vars)
        # Fill the missing vars with its own var name
        return {used_var: self.context.get(used_var, '') for used_var in used_vars}

    def wrap_var_key(self, var_key):
        return f'{self.open_delimiter}{var_key}{self.close_delimiter}'

    def get_used_vars(self, template):
        """
        :return: A list of vars used in template.
        :rtype: list
        """
        return [used_var[1:-1].lower() for used_var in self.regexp.findall(template)]


class DelimitedVarsTemplateRenderer(RegexpTemplateRenderer):
    """
    External management email follows an special template pattern, different from the one defined by
    IRIS1TemplateRenderer. The vars are defined as #variable#, so the # acts a delimiter, while the other templates
    don't even have delimiters.

    At the top of the template a set of vars are placed. They must be processed and removed from the text before
    rendering the final text. For example:

        #CAPSALERA=Consultes a webs de l'Ajuntament#
    """
    DEFAULT_OPEN_DELIMITER = '#'
    DEFAULT_CLOSE_DELIMITER = '#'

    def render(self, template):
        """
        Override for removing the vars before rendering the template
        :param template: String template
        :return: Rendered template
        """
        return super().render(self.get_template_without_vars(template))

    def get_context(self, template):
        """
        Adds the template defined vars to the context
        :param template: Template string
        :return: Context vars for rendering the template
        """
        ctx = super().get_context(template)
        ctx.update(self.get_header_context(template))
        return ctx

    def get_template_without_vars(self, template):
        """
        :param template: Template string
        :return: Template without vars
        """
        if not template:
            return ''
        return re.sub('#(\w*)=([^#]*)#', '', template).strip()  # noqa W605

    def get_header_context(self, template):
        """
        :return: Template defined vars as dict. Each var follows this patter [DELIMITER]var_name=var_value[DELIMITER]
        :rtype: dict
        """
        if not template:
            return {}
        matches = re.findall(r'#(\w*)=([^#]*)#', template)  # noqa W605
        return dict([group for group in matches])
