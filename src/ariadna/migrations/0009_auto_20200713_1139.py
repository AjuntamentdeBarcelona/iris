# Generated by Django 2.1.1 on 2020-07-13 09:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ariadna', '0008_ariadna_deleted'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='ariadna',
            unique_together={('year', 'input_number', 'deleted')},
        ),
    ]
