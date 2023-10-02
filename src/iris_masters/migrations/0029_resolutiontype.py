# Generated by Django 2.1.1 on 2019-03-18 11:50

from django.db import migrations, models
import iris_masters.models


class Migration(migrations.Migration):

    dependencies = [
        ('iris_masters', '0028_auto_20190315_1729'),
    ]

    operations = [
        migrations.CreateModel(
            name='ResolutionType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', iris_masters.models.UserIdField(max_length=20, verbose_name='User ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Creation date')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last update')),
                ('description', models.CharField(max_length=40, unique=True, verbose_name='Description')),
                ('enabled', models.BooleanField(default=True, verbose_name='Enabled')),
                ('order', models.PositiveIntegerField(db_index=True, default=100)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
