# Generated by Django 2.1.1 on 2019-11-15 12:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('iris_masters', '0063_auto_20191115_1233'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lettertemplate',
            name='name',
            field=models.CharField(max_length=100),
        ),
    ]
