# Generated by Django 2.1.1 on 2019-01-15 15:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('iris_masters', '0005_application'),
    ]

    operations = [
        migrations.AlterField(
            model_name='parameter',
            name='description',
            field=models.TextField(blank=True),
        ),
    ]
