from jsonschema import RefResolver
from jsonschema import validate as validate_json_schema


def validate_obj_dict(obj, schema, full_spec):
    """
    Given a dict and a parameter spec, checks if the dict values are conformant to spec as JSON Schema.
    :param obj:
    :param param_spec:
    :return: True if is a valid object for the spec.
    """
    return validate_json_schema(obj, schema, resolver=RefResolver(base_uri='#', referrer=full_spec,
                                                                  store=full_spec))
