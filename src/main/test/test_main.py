import pytest
from io import StringIO

from django.db.migrations.loader import MigrationLoader
from django.core.management import BaseCommand, call_command
from django.db import DEFAULT_DB_ALIAS, connections
from django_migration_checker import get_conflicts


@pytest.mark.unit_test
def test_true():
    assert True


@pytest.mark.integration_test
@pytest.mark.django_db
def test_system_check():
    """
    Performs the Django system check.
    """
    base_command = BaseCommand()
    system_check_errors = base_command.check()
    assert not system_check_errors


@pytest.mark.django_db
def test_migrations_check(settings):
    """
    Check that the migrations are correct.
    """
    base_command = BaseCommand()
    migrations_check_errors = base_command.check_migrations()
    assert not migrations_check_errors


@pytest.mark.skip(reason="settings.LOCAL_APPS not defined")
@pytest.mark.django_db
def test_make_migrations_check(settings):
    """
    Check that somebody missed to run makemigrations command.
    """
    out = StringIO()
    err = StringIO()
    call_command('makemigrations', '--dry-run', *settings.LOCAL_APPS, stdout=out, stderr=err)
    if err.getvalue() != '':
        pytest.fail(err.getvalue())
    if 'No changes detected' not in out.getvalue().strip('\n'):
        pytest.fail(out.getvalue())


@pytest.mark.skip(reason="settings.LOCAL_APPS not defined")
@pytest.mark.django_db
def test_check_duplicated_migrations(settings):
    """
    Check that there are not migrations with the same prefix for each app.
    """
    connection = connections[DEFAULT_DB_ALIAS]
    loader = MigrationLoader(connection, ignore_no_migrations=True)
    graph = loader.graph
    for app in settings.LOCAL_APPS:
        shown = set()
        for node in graph.leaf_nodes(app):
            for plan_node in graph.forwards_plan(node):
                if plan_node not in shown and plan_node[0] == app:
                    shown.add(plan_node)
        # Convert the migrations set to a list of prefixes:
        # {('inventory', '0001_initial'), ('inventory', '0002_add_field')} -> ['0001', '0002']
        migrations_prefix = [migration[1].split('_')[0] for migration in shown]
        if len(set(migrations_prefix)) != len(migrations_prefix):
            pytest.fail('There are migrations in app "{}" with the same prefix'.format(app))


@pytest.mark.django_db
def test_migrations():
    """
    Checks there are no migration conflicts. (#71771)
    """
    conflicts = get_conflicts()
    assert not conflicts
