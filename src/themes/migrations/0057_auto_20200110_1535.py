# Generated by Django 2.1.1 on 2020-01-10 14:35

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('themes', '0056_elementdetaildeleteregister'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='themegroup',
            unique_together={('description', 'deleted')},
        ),
    ]