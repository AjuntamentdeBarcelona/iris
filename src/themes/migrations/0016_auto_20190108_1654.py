# Generated by Django 2.1.1 on 2019-01-08 15:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('themes', '0015_auto_20190103_1720'),
    ]

    operations = [
        migrations.AddField(
            model_name='elementdetail',
            name='requires_ubication_district',
            field=models.BooleanField(default=False, help_text='If checked, a district will be required as ubication for creating a record card.', verbose_name='Requires District Ubication'),
        ),
        migrations.AddField(
            model_name='elementdetail',
            name='requires_ubication_full_address',
            field=models.BooleanField(default=False, help_text='If checked, a full adress with floor and door will be required as ubication for creating a record card.', verbose_name='Requires full address'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='requires_ubication',
            field=models.BooleanField(default=False, help_text='If checked, an address will be required as ubication for creating a record card.', verbose_name='Requires Ubication'),
        ),
    ]