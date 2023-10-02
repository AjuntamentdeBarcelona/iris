"""
Functions for formatting variable values in a consistent way.
"""
from babel.dates import format_date, format_datetime
from django.template.defaultfilters import date as django_date
from django.utils import translation


def date(value, format='long'):
    return format_date(value, format, locale=translation.get_language())


def datetime(value, format='long'):
    return format_datetime(value, format, locale=translation.get_language())


def time(value, format='H:i'):
    return django_date(value, format)
