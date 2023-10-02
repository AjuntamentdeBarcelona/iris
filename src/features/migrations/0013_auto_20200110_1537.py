# Generated by Django 2.1.1 on 2020-01-10 14:37

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('features', '0012_auto_20191030_0846'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='feature',
            unique_together={('description', 'values_type', 'deleted')},
        ),
        migrations.AlterUniqueTogether(
            name='values',
            unique_together={('description', 'values_type', 'deleted')},
        ),
        migrations.AlterUniqueTogether(
            name='valuestype',
            unique_together={('description', 'deleted')},
        ),
    ]