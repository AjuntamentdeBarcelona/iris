# Generated by Django 2.1.1 on 2020-01-08 11:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('record_cards', '0095_recordcard_organization'),
    ]

    operations = [
        migrations.AddField(
            model_name='recordcard',
            name='pend_response_responsible',
            field=models.BooleanField(default=False, verbose_name='Pend Response to Record Responsible'),
        ),
        migrations.AddField(
            model_name='recordcard',
            name='response_to_responsible',
            field=models.BooleanField(default=False, verbose_name='Response to Record Responsible'),
        ),
    ]
