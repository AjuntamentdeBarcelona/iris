# Generated by Django 2.1.1 on 2019-01-22 09:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('themes', '0019_auto_20190115_1648'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='area',
            options={'ordering': ('order',)},
        ),
        migrations.AlterModelOptions(
            name='element',
            options={'ordering': ('order',)},
        ),
        migrations.AlterModelOptions(
            name='elementdetail',
            options={'ordering': ('order',)},
        ),
        migrations.AlterField(
            model_name='area',
            name='order',
            field=models.PositiveIntegerField(db_index=True, default=0),
        ),
        migrations.AlterField(
            model_name='element',
            name='order',
            field=models.PositiveIntegerField(db_index=True, default=0),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='order',
            field=models.PositiveIntegerField(db_index=True, default=0),
        ),
    ]
