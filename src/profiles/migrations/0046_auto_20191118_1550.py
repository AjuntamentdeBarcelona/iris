# Generated by Django 2.1.1 on 2019-11-18 14:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0045_auto_20191115_1039'),
    ]

    operations = [
        migrations.AlterField(
            model_name='group',
            name='description',
            field=models.CharField(db_index=True, max_length=40, verbose_name='Description'),
        ),
    ]
