# Generated by Django 2.1.1 on 2019-06-25 07:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('protocols', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='protocols',
            name='short_description',
            field=models.CharField(default=' ', max_length=50, verbose_name='Short description'),
        ),
    ]
