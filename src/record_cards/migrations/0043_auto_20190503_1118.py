# Generated by Django 2.1.1 on 2019-05-03 09:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('record_cards', '0042_auto_20190424_1649'),
    ]

    operations = [
        migrations.AlterField(
            model_name='citizen',
            name='sex',
            field=models.CharField(choices=[('m', 'Male'), ('f', 'Female'), ('u', 'Unknown')], default='u', max_length=1, verbose_name='Sex'),
        ),
    ]
