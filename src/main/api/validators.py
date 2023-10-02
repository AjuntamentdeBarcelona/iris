from datetime import datetime

from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.utils.translation import ugettext_lazy
from rest_framework import serializers
from rest_framework import validators
from rest_framework.compat import MaxValueValidator


class UniqueRelatedValidator(validators.UniqueTogetherValidator):
    """
    UniqueTogetherValidator based on a main_field that acts as reference for the validation.
    With this validator, the errors are returned per field (associated to the main field) and you can configure the
    lookup for that field.

    The use case example is ensuring that one field is unique inside a subset of model with a custom lookup for
    customizing the definition of "unique".
    """
    def __init__(self, main_field, filter_fields, queryset, main_lookup="iexact", message=None):
        self.filter_fields = filter_fields
        self.main_lookup = main_lookup
        self.main_field = main_field
        super().__init__(queryset, [main_field] + list(filter_fields), message)

    def __call__(self, attrs):
        try:
            return super().__call__(attrs)
        except serializers.ValidationError as e:
            raise serializers.ValidationError({self.main_field: e.detail})

    def filter_queryset(self, attrs, queryset):
        lookup = {filter_attr: attrs.get(filter_attr) for filter_attr in self.filter_fields}
        return self.queryset.filter(**lookup).filter(**{
            f"{self.main_field}__{self.main_lookup}": attrs.get(self.main_field)
        })


class BulkUniqueRelatedValidator(UniqueRelatedValidator):
    """
    UniqueRelatedValidator for validating many fields with the same validator instance.
    """
    def __init__(self, main_fields, filter_fields, queryset, main_lookup="iexact", message=None):
        self.main_fields = main_fields
        super().__init__(main_fields[0], filter_fields, queryset, main_lookup, message)

    def __call__(self, attrs):
        errors = {}
        for field in self.main_fields:
            try:
                self.main_field = field
                super().__call__(attrs)
            except serializers.ValidationError as e:
                errors.update(e.detail)
        if errors:
            raise serializers.ValidationError(errors)


class WordsLengthValidator:
    message = ugettext_lazy("Ensure this value has at least %(words)s words with %(words_length)s characters.")
    code = "min_length"

    def __init__(self, words, words_length, message=None):
        self.words = words
        self.words_length = words_length
        if message:
            self.message = message

    def __call__(self, value):
        cleaned = self.clean(value)
        params = {"words": self.words, "words_length": self.words_length, "value": value}
        if not self.validate(cleaned):
            raise ValidationError(self.message, code=self.code, params=params)

    def validate(self, cleaned_value):
        """

        :param cleaned_value: list of words length
        :return:
        """
        min_length_words = 0
        for word in cleaned_value:
            if len(word) >= self.words_length:
                min_length_words += 1

        return True if min_length_words >= self.words else False

    @staticmethod
    def clean(value):
        """
        :param value: field input value
        :return: words list
        """
        return value.split()


class WordsLengthAllowBlankValidator(WordsLengthValidator):

    """
    Validator that checks the number and length of words. If no words are set, it validates.
    """

    def validate(self, cleaned_value):
        """
        :param cleaned_value: list of words length
        :return: True if value is a valid one, else False
        """
        if not cleaned_value:
            return True

        min_length_words = 0
        for word in cleaned_value:
            if len(word) >= self.words_length:
                min_length_words += 1

        return True if min_length_words >= self.words else False


class MaxYearValidator(MaxValueValidator):
    message = ugettext_lazy("Ensure this value is less than or equal to current year.")
    code = "max_year_value"

    def __init__(self, message=None):
        self.limit_value = datetime.today().year
        if message:
            self.message = message


class EmailCommasSeparatedValidator(EmailValidator):

    message = ugettext_lazy("Check the list of emails (separated by commas).")

    def __call__(self, value):
        for email in value.split(","):
            super().__call__(email)
