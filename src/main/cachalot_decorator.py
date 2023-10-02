from django.db.models import Q
from django.utils.decorators import method_decorator

from cachalot.api import cachalot_disabled


def check_no_cacheable_args(fields, args):
    for arg in args:
        if isinstance(arg, Q) or arg not in fields:
            return True


def check_no_cacheable_kwargs(fields, kwargs):
    for field, _ in kwargs.items():
        if field not in fields:
            return True


def cacheable(fields, *args, **kwargs):
    if check_no_cacheable_args(fields, args):
        return False

    if check_no_cacheable_kwargs(fields, kwargs):
        return False

    return True


def cacheable_query_decorator(method, fields):
    def cachalot_cacheable(*args, **kwargs):
        if cacheable(fields, *args, **kwargs):
            return method(*args, **kwargs)
        with cachalot_disabled():
            return method(*args, **kwargs)

    return cachalot_cacheable


def iris_cachalot(manager, extra_fields=None):
    fields = ["pk", "order", "deleted", "enabled", *(extra_fields or [])]

    manager.filter = cacheable_query_decorator(manager.filter, fields)
    manager.get = cacheable_query_decorator(manager.get, fields)

    class CachalotClass(manager._queryset_class):
        pass

    def decorator_factory(method):
        return cacheable_query_decorator(method, fields)

    method_decorator(decorator_factory, name='filter')(CachalotClass)
    method_decorator(decorator_factory, name='get')(CachalotClass)
    manager._queryset_class = CachalotClass
    return manager
