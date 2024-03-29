# Generated by Django 2.1.1 on 2019-07-11 13:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ariadna', '0004_auto_20190710_1405'),
    ]

    operations = [
        migrations.RenameField(
            model_name='ariadnarecord',
            old_name='fitxa',
            new_name='record_card',
        ),
        migrations.AlterField(
            model_name='ariadna',
            name='code',
            field=models.CharField(max_length=12),
        ),
        migrations.AlterField(
            model_name='ariadna',
            name='id',
            field=models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='ariadna',
            name='used',
            field=models.BooleanField(default=False, verbose_name='Used'),
        ),
    ]
