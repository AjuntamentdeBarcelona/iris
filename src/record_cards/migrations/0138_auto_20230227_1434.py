# Generated by Django 2.2.28 on 2023-02-27 13:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('record_cards', '0137_workflowresolutionextrafields'),
    ]

    operations = [
        migrations.AddField(
            model_name='ubication',
            name='letterFi',
            field=models.CharField(blank=True, max_length=3, null=True, verbose_name='LetterFi'),
        ),
        migrations.AddField(
            model_name='ubication',
            name='numFi',
            field=models.CharField(blank=True, db_index=True, max_length=60, null=True, verbose_name='NumFi'),
        ),
    ]
