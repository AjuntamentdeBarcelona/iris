# Generated by Django 2.1.1 on 2018-10-29 11:07

from django.db import migrations, models
import django.db.models.deletion
import iris_masters.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ExternalApplication',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=30)),
            ],
        ),
        migrations.CreateModel(
            name='InputChannel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.CharField(max_length=40)),
            ],
        ),
        migrations.CreateModel(
            name='RecordType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', iris_masters.models.UserIdField(max_length=20, verbose_name='User ID')),
                ('created_at', models.DateField(auto_now_add=True, verbose_name='Creation date')),
                ('updated_at', models.DateField(auto_now=True, verbose_name='Last update')),
                ('description', models.CharField(max_length=40, verbose_name='Description')),
                ('tri', models.SmallIntegerField(verbose_name='TRI')),
                ('trt', models.SmallIntegerField(verbose_name='TRT')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ResponseChannel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=20)),
            ],
        ),
        migrations.CreateModel(
            name='Support',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('input_channel', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='iris_masters.InputChannel')),
            ],
        ),
    ]
