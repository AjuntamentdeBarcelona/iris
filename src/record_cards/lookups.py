import re

from django.db.models import Lookup


class ILike(Lookup):
    lookup_name = 'ilike_contains'

    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        params = lhs_params + rhs_params
        return "%s ~* %s" % (lhs, rhs), self.filter_params(params)

    def filter_params(self, params):
        return [re.escape(p) for p in params]
