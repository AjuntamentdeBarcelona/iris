# Generated by Django 2.1.1 on 2019-07-05 10:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('protocols', '0005_auto_20190705_1209'),
    ]

    operations = [
        migrations.AlterField(
            model_name='protocols',
            name='short_description',
            field=models.TextField(default=' ', verbose_name='Short description'),
        ),
    ]