# Generated by Django 2.1.1 on 2019-08-07 13:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('iris_masters', '0046_auto_20190724_1732'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='parameter',
            options={'ordering': ('category',)},
        ),
        migrations.AddField(
            model_name='parameter',
            name='category',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
