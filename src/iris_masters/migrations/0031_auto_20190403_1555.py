# Generated by Django 2.1.1 on 2019-04-03 13:55
from django.conf import settings
from django.core.signing import Signer
from django.db import migrations


def set_description_hash(apps, schema_editor):
    Application = apps.get_model('iris_masters', 'Application')
    for app in Application.objects.all():
        signer = Signer(salt=settings.APPLICATION_HASH_SALT)
        if app.description_ca:
            app.description_hash = signer.signature(app.description_ca)
        else:
            app.description_hash = signer.signature(app.description)
        app.save()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('iris_masters', '0030_application_description_hash'),
    ]

    operations = [
        migrations.RunPython(set_description_hash, noop),
    ]