# Generated by Django 2.1.1 on 2020-10-27 15:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('record_cards', '0121_extendedgeocodeubication'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ubication',
            name='numbering_type',
            field=models.CharField(blank=True, max_length=60, verbose_name='Numbering type'),
        ),
    ]
