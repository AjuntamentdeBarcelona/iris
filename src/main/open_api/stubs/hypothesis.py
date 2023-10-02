from drf_yasg import openapi
from hypothesis import strategies as st


class InvalidReference(Exception):
    pass


DEFAULT_FORMAT = '$DEFAULT$'
ST_KEY = '$strategy$'

ST_DECIMALS = {
    ST_KEY: st.decimals,
    'min_value': 'minimum',
    'max_value': 'maximum',
}

ST_INTEGERS = {
    ST_KEY: st.integers,
    'min_value': 'minimum',
    'max_value': 'maximum',
}

ST_TEXT = {
    ST_KEY: st.text,
    "min_size": "maxLength",
    "max_size": "minLength",
}

HYPOTHESIS_TYPE_MAP = {
    openapi.TYPE_OBJECT: 1,
    openapi.TYPE_STRING: {
        DEFAULT_FORMAT: ST_TEXT,
        openapi.FORMAT_DATE: st.dates,
        openapi.FORMAT_DATETIME: st.datetimes,
        openapi.FORMAT_UUID: st.uuids,
    },
    openapi.TYPE_NUMBER: {
        DEFAULT_FORMAT: ST_DECIMALS,
        openapi.FORMAT_INT32: ST_INTEGERS,
        openapi.FORMAT_INT64: ST_INTEGERS,
        openapi.FORMAT_DOUBLE: ST_DECIMALS,
        openapi.FORMAT_FLOAT: ST_DECIMALS,
        openapi.FORMAT_DECIMAL: ST_DECIMALS,
    },
    openapi.TYPE_INTEGER: {
        DEFAULT_FORMAT: ST_INTEGERS,
        openapi.FORMAT_INT32: ST_INTEGERS,
        openapi.FORMAT_INT64: ST_INTEGERS,
    },
    openapi.TYPE_BOOLEAN: st.booleans,
    openapi.TYPE_ARRAY: st.lists,
    openapi.TYPE_FILE: None,
}


class HypothesisStubGenerator:
    """
    Given an OpenAPI spec dict, generates test data with hypothesis.

    :todo: test
    :todo: Optional data
    :todo: Extend for generate all the test cases following Dijkstra's doctrine
    """
    METHOD_ATTR_MARKER = '$'
    METHOD_DICT = {
        '$ref': 'get_generator_for_ref'
    }
    HYPOTHESIS_STRATEGY = st.dictionaries

    def __init__(self, schema, definitions, type_map=None):
        """
        :param dict schema: Parameters/Response spec
        :param dict definitions: Definition dict for referenced structures.
        """
        self.schema = schema
        self._definitions = definitions
        self._type_map = type_map or HYPOTHESIS_TYPE_MAP.copy()
        self._generator = None
        self.build_generators()

    @property
    def definitions(self):
        return self._definitions

    @definitions.setter
    def definitions(self, definitions):
        self._generator = None
        self._definitions = definitions

    @property
    def type_map(self):
        return self._type_map

    @type_map.setter
    def type_map(self, type_map):
        self._generator = None
        self._type_map = type_map

    def generate(self):
        """
        :return: Dictionary with test data for the given structure.
        """
        if not self._generator:
            self.build_generators()
        return self._generate(self._generator)

    def _generate(self, generator_dict):
        """
        :param generator_dict: Generator dict
        :return: Stub object dict
        """
        final_obj = {}
        for key, generator in generator_dict.items():
            final_obj[key] = self._generate(generator) if isinstance(generator, dict) else generator.example()
        return final_obj

    def build_generators(self):
        """
        Creates the generator structure for the type map and definitions.
        :return:
        """
        self._generator = self.get_generators_for_schema(self.definitions)

    def get_generators_for_schema(self, schema, final_generator=None):
        final_generator = final_generator or {}
        for key, definition in schema:
            if key[0] == self.METHOD_ATTR_MARKER:
                final_generator.update(self.generate_method_attr(schema, method_attr=key, definition=definition))
            if isinstance(definition, dict):
                final_generator[key] = self.get_generator_for_param(definition)
            elif isinstance(definition, str):
                if definition[0] == self.METHOD_ATTR_MARKER:
                    pass
        return final_generator

    def generate_method_attr(self, schema, method_attr, definition):
        return getattr(self, method_attr)(schema, definition)

    def get_generator_for_ref(self, definition):
        """
        Creates the generator for a given reference ($ref).
        :param definition:
        :return: generator dict
        """
        try:
            schema = self._definitions[definition]
            return self.get_generators_for_schema(schema)
        except KeyError:
            raise InvalidReference('Invalid reference to Unknown definition {}'.format(definition))

    def get_generator_for_param(self, parameter):
        """
        Given a parameter, returns a generator for creating test data.
        :param parameter:
        :return: generator
        """
        formats = self._type_map.get(parameter.get('type'))
        format_strategy_spec = formats.get(parameter.get('format', DEFAULT_FORMAT))
        strategy = format_strategy_spec.get(ST_KEY)
        return strategy(**self.get_generator_kwargs(parameter, format_strategy_spec))

    def get_generator_kwargs(self, parameter, format_spec):
        """
        Given a format, returns a generator for creating test data.
        :param dict parameter: OpenAPI parameter dict
        :param dict format_spec: Format dict
        :return: generator
        """
        if isinstance(format, dict):
            return {kwarg: parameter.get(param_conf)
                    for kwarg, param_conf in format_spec.items() if kwarg != ST_KEY}
        return {}
