# Generated by Django 2.1.1 on 2020-02-10 21:50

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('themes', '0062_derivationpolygon_district_mode'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='derivationpolygon',
            options={'ordering': ('polygon_code',)},
        ),
    ]
