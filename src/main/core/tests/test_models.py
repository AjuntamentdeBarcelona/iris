import pytest
from django.core.exceptions import ValidationError
from django.db import models
from mock import Mock

from main.core.models import CaseInsensitiveUniqueMixin


class ModelA(CaseInsensitiveUniqueMixin, models.Model):
    description_a = models.CharField(max_length=30)
    description_b = models.CharField(max_length=30)
    unique_case_insensitive = []
    unique_case_insensitive_msg = []


class ModelB(ModelA):
    description_c = models.CharField(max_length=30)
    unique_case_insensitive = []
    unique_case_insensitive_msg = []


class TestCaseInsensitiveUniqueMixin:
    DEFAULT_MSG = 'Test message for default'

    def given_a_dummy_class(self, parent_casei, dummy_casei, parent_errors={}, dummy_errors={}):
        ModelA.unique_case_insensitive = parent_casei
        ModelA.unique_case_insensitive_msg = parent_errors
        ModelB.unique_case_insensitive = dummy_casei
        ModelB.unique_case_insensitive_msg = dummy_errors
        return ModelB

    def test_validate_unique_when_is_unique(self):
        dummy_class = self.given_a_dummy_class(parent_casei=[], dummy_casei=['description_a'])
        self.when_equivalent_dont_exists(dummy_class)
        dummy_class().validate_unique()

    def test_validate_unique_when_another_exists(self):
        dummy_class = self.given_a_dummy_class(parent_casei=[], dummy_casei=['description_a'])
        self.when_equivalent_exists(dummy_class)
        with pytest.raises(ValidationError):
            dummy_class().validate_unique()

    @pytest.mark.parametrize('parent_casei,dummy_casei,expected', (
        ([], [], []),
        (['description_a', 'description_b'], [], ['description_a', 'description_b']),
        ([], ['description_c'], ['description_c']),
        (['description_a', 'description_b'], ['description_c'], ['description_a', 'description_b', 'description_c']),
    ))
    def test_get_unique_case_insensitive(self, parent_casei, dummy_casei, expected):
        dummy_class = self.given_a_dummy_class(parent_casei, dummy_casei)
        casei_unique = dummy_class()._get_case_insensitive_unique()
        self.should_have_unique_fields(casei_unique, expected)

    @pytest.mark.parametrize('field,parent,dummy, expected', (
        ('description_a', {'description_a': 'Test msg'}, {}, 'Test msg'),
        ('description_a', {}, {'description_a': 'Test msg'}, 'Test msg'),
        ('description_a', {'description_a': 'Test parent msg'}, {'description_a': 'Test msg'}, 'Test msg'),
        ('description_b', {'description_a': 'Test parent msg'}, {'description_b': 'Test msg b'}, 'Test msg b'),
    ))
    def test_error_messages(self, field, parent, dummy, expected):
        dummy_class = self.given_a_dummy_class(['description_a'], ['description_b'], parent, dummy)
        msg = dummy_class()._get_case_insensitive_error_message(field)
        assert msg == expected

    def test_default_error_message(self):
        dummy_class = self.given_a_dummy_class(['description_a'], ['description_b'])
        self.when_default_message_is(dummy_class, self.DEFAULT_MSG)
        assert dummy_class()._get_case_insensitive_error_message('description_a') == self.DEFAULT_MSG

    def test_default_error_without_specified_message(self):
        dummy_class = self.given_a_dummy_class(['description_a'], ['description_b'])
        assert dummy_class()._get_case_insensitive_error_message('description_a') != ''

    def when_equivalent_exists(self, cls):
        cls.objects = Mock()
        cls.objects.filter.return_value = Mock(exists=Mock(return_value=True))

    def when_equivalent_dont_exists(self, cls):
        cls.objects = Mock()
        cls.objects.filter.return_value = Mock(exists=Mock(return_value=False))

    def when_default_message_is(self, cls, message):
        cls.unique_case_insensitive_default_msg = message

    def should_have_unique_fields(self, fields, expected):
        assert len(fields) == len(expected)
        for field in fields:
            assert field in expected
