# Generated by Django 2.1.1 on 2020-09-14 06:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ariadna', '0010_auto_20200910_1108'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ariadna',
            name='contact',
            field=models.CharField(blank=True, default='Ariadna', max_length=10, verbose_name='contact'),
        ),
    ]