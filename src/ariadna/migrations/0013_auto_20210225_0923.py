# Generated by Django 2.1.1 on 2021-02-25 08:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ariadna', '0012_auto_20200914_0838'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ariadna',
            name='social_reason',
            field=models.CharField(blank=True, max_length=60, null=True, verbose_name='social_reason'),
        ),
    ]
