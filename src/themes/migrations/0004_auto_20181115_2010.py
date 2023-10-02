# Generated by Django 2.1.1 on 2018-11-15 19:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('themes', '0003_auto_20181108_1242'),
    ]

    operations = [
        migrations.AlterField(
            model_name='area',
            name='area_code',
            field=models.CharField(blank=True, default='', max_length=12, verbose_name='Area Code'),
        ),
        migrations.AlterField(
            model_name='element',
            name='element_code',
            field=models.CharField(blank=True, default='', max_length=36, verbose_name='Element Code'),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='detail_code',
            field=models.CharField(blank=True, default='', max_length=36, verbose_name='Detail code'),
        ),
    ]
