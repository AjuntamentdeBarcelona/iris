# Generated by Django 2.1.1 on 2020-01-27 09:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('record_cards', '0105_auto_20200123_1113'),
    ]

    operations = [
        migrations.AddField(
            model_name='applicant',
            name='deleted',
            field=models.DateTimeField(editable=False, null=True),
        ),
        migrations.AddField(
            model_name='citizen',
            name='deleted',
            field=models.DateTimeField(editable=False, null=True),
        ),
        migrations.AddField(
            model_name='socialentity',
            name='deleted',
            field=models.DateTimeField(editable=False, null=True),
        ),
    ]
