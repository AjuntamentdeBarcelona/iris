# Generated by Django 2.1.1 on 2018-12-05 14:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('themes', '0006_auto_20181210_1154'),
    ]

    operations = [
        migrations.AddField(
            model_name='area',
            name='deleted',
            field=models.DateTimeField(editable=False, null=True),
        ),
    ]
