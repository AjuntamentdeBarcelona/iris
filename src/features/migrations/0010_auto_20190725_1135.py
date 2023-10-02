# Generated by Django 2.1.1 on 2019-07-25 09:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('features', '0009_auto_20190604_1315'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='feature',
            name='enabled',
        ),
        migrations.RemoveField(
            model_name='values',
            name='enabled',
        ),
        migrations.RemoveField(
            model_name='valuestype',
            name='enabled',
        ),
        migrations.AddField(
            model_name='feature',
            name='deleted',
            field=models.DateTimeField(editable=False, null=True),
        ),
        migrations.AddField(
            model_name='values',
            name='deleted',
            field=models.DateTimeField(editable=False, null=True),
        ),
        migrations.AddField(
            model_name='valuestype',
            name='deleted',
            field=models.DateTimeField(editable=False, null=True),
        ),
    ]