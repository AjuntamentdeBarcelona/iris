from django.db import connection
from django.db.backends.postgresql.base import DatabaseWrapper


def reset_sequences(sender, **kwargs):

    tables_name = ['iris_masters_reason', 'iris_masters_inputchannel', 'iris_masters_application',
                   'iris_masters_support', 'iris_masters_applicanttype', 'profiles_groupinputchannel',
                   'iris_masters_resolutiontype', 'iris_masters_parameter', 'iris_templates_iristemplate',
                   'iris_templates_iristemplaterecordtypes']

    for table_name in tables_name:
        # Reset Reasons ids sequence because of ids that we insert
        sql = f"""SELECT setval(pg_get_serial_sequence('"{table_name}"', 'id'), coalesce(max("id"), 1), max("id")
        IS NOT null) FROM "{table_name}";"""  # noqa W291
        with connection.cursor() as cursor:
            if isinstance(cursor.db, DatabaseWrapper):
                cursor.execute(sql)
