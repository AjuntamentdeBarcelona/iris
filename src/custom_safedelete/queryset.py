from django.db.models import Q
from safedelete.config import DELETED_VISIBLE_BY_FIELD, DELETED_VISIBLE
from safedelete.queryset import SafeDeleteQueryset


class CustomSafeDeleteQueryset(SafeDeleteQueryset):
    """
    The point of this is that the query filters of a relationship are passed as args arguments, not as kwargs.
    Then to retrieve deleted objects in relationships, we have to check args and set the force visibility
    to DELETED_VISIBLE
    """

    def _check_visibility_field_args(self, args):
        """
        Check if visibility field is included in query args.

        :param args: query args
        :return:
        """
        for arg in args:
            for child in arg.children:
                if self._check_visibility_field_args_for_arg(child):
                    return True
        return False

    def _check_visibility_field_args_for_arg(self, child):
        if isinstance(child, Q):
            for field, _ in child.children:
                if field == self._safedelete_visibility_field:
                    return True
        else:
            field = child[0]
            if field == self._safedelete_visibility_field:
                return True

    def _check_field_filter_args(self, args):
        """
        Check if the visibility for DELETED_VISIBLE_BY_FIELD needs to be put into effect for querysets on relations.

        DELETED_VISIBLE_BY_FIELD is a temporary visibility flag that changes
        to DELETED_VISIBLE once asked for the named parameter defined in
        `_safedelete_force_visibility`. When evaluating the queryset, it will
        then filter on all models.
        """
        if self._safedelete_visibility == DELETED_VISIBLE_BY_FIELD and self._check_visibility_field_args(args):
            self._safedelete_force_visibility = DELETED_VISIBLE

    def filter(self, *args, **kwargs):
        self._check_field_filter_args(args)
        return super(CustomSafeDeleteQueryset, self).filter(*args, **kwargs)

    def get(self, *args, **kwargs):
        self._check_field_filter_args(args)
        return super(CustomSafeDeleteQueryset, self).get(*args, **kwargs)
