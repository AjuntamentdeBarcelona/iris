# Generated by Django 2.1.1 on 2020-02-07 09:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('record_cards', '0108_auto_20200127_1057'),
    ]

    operations = [
        migrations.AddField(
            model_name='applicant',
            name='pend_anonymize',
            field=models.BooleanField(default=False, verbose_name='Pend to anonymize'),
        ),
    ]
