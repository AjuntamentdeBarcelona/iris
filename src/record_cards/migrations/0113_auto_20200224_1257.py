# Generated by Django 2.1.1 on 2020-02-24 11:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('record_cards', '0112_auto_20200218_1650'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recordcardresponse',
            name='floor',
            field=models.CharField(blank=True, max_length=50, verbose_name='Floor'),
        ),
        migrations.AlterField(
            model_name='workflowplan',
            name='responsible_profile',
            field=models.CharField(blank=True, max_length=400, verbose_name='Service or person in charge'),
        ),
        migrations.AlterField(
            model_name='workflowresolution',
            name='service_person_incharge',
            field=models.CharField(blank=True, max_length=400, verbose_name='Service or person in charge'),
        ),
    ]