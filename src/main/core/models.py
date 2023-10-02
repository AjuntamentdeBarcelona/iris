from django.core.exceptions import ValidationError
from django.forms.utils import ErrorDict
from django.utils.translation import gettext_lazy as _

DEFAULT_ERROR_MESSAGE = _('There is another registry with an equivalent value and must be unique')


class CaseInsensitiveUniqueMixin:
    """
    Mixin class for performing case-insensitive unique on Django model fields.  The unique fields are defined on
    model class as:
    - unique_case_insensitive: list of fields that must be unique
    - unique_case_insensitive_msg: custom unique error messages as dict per field
    - unique_case_insensitive_default_msg: default message for errors

    The use of this class only makes sense with char fields.

    Example:
        class MyModel(models.Model):
            class Meta:
                unique_case_insensitive = ['description']
                unique_case_insensitive_msg = {
                    'description': 'Another MyModel with an equivalent description exists'
                }

    A second unique_case_insensitive format allows to define togethers:

        unique_case_insensitive = [('description', ('areas',))]

    In this form, the field is described as a tuple, being the first index the field and the second a list of fields
    for the together. In the previous example, the description must be unique respect to Area.

    The current version of this class is fully implemented on python and doesn't perform any changes on DB schema.
    This a database independent approach, as an alternative you could create a unique index on PostgreSQL as follows:
        CREATE UNIQUE INDEX my_idx ON mytbl(lower(name));
    """
    unique_case_insensitive_default_msg = DEFAULT_ERROR_MESSAGE

    def validate_unique(self, exclude=None):
        """
        Check unique constraints on the model and raise ValidationError if any
        failed.
        """
        errors = ErrorDict()
        try:
            super().validate_unique(exclude)
        except ValidationError as e:
            errors += e.error_dict
        casei_unique = self._get_case_insensitive_unique()
        for field in casei_unique:
            if isinstance(field, tuple):
                field, together = field
            else:
                together = []
            if self._check_case_insensitive_field(field, together):
                errors.setdefault(field, []).append(self._get_case_insensitive_error_message(field))
        if errors:
            raise ValidationError(errors)

    def _get_case_insensitive_unique(self):
        """
        :return: A list of fields which must be checked case insensitive.
        """
        casei_unique = [] + getattr(self, 'unique_case_insensitive', [])
        for parent_class in self._meta.get_parent_list():
            casei_unique += getattr(parent_class, 'unique_case_insensitive', [])
        return casei_unique

    def _check_case_insensitive_field(self, field, together):
        """
        :param field: field name (must be defined)
        :return: True if there is another registry with the same value
        """
        lookup = {'{}__iexact'.format(field): getattr(self, field)}
        for related in together:
            if hasattr(self, related):
                lookup[related] = getattr(self, related)
        qs = self.__class__.objects.filter(**lookup)
        if self.pk:
            qs = qs.exclude(pk=self._get_pk_val(self._meta))
        return qs.exists()

    def _get_case_insensitive_error_message(self, field):
        msgs = {}
        for parent_class in self._meta.get_parent_list():
            msgs.update(getattr(parent_class, 'unique_case_insensitive_msg', {}))
        msgs.update(getattr(self, 'unique_case_insensitive_msg', {}))
        return msgs.get(field, self.unique_case_insensitive_default_msg)
