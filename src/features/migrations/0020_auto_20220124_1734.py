# Generated by Django 2.2 on 2022-01-24 16:34

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('features', '0019_auto_20211122_1441'),
    ]

    operations = [
        migrations.RenameField(
            model_name='feature',
            old_name='description_ca',
            new_name='description_gl',
        ),
        migrations.RenameField(
            model_name='feature',
            old_name='explanatory_text_ca',
            new_name='explanatory_text_gl',
        ),
        migrations.RenameField(
            model_name='mask',
            old_name='description_ca',
            new_name='description_gl',
        ),
        migrations.RenameField(
            model_name='values',
            old_name='description_ca',
            new_name='description_gl',
        ),
        migrations.RenameField(
            model_name='valuestype',
            old_name='description_ca',
            new_name='description_gl',
        ),
    ]