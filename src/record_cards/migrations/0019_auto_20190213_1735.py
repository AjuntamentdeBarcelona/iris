# Generated by Django 2.1.1 on 2019-02-13 16:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('record_cards', '0018_recordcardresponse'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ubication',
            name='numbering_type',
            field=models.CharField(blank=True, max_length=1, verbose_name='Numbering type'),
        ),
    ]
