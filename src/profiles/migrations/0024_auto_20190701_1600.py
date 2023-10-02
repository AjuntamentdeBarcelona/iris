# Generated by Django 2.1.1 on 2019-07-01 14:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0023_auto_20190701_1547'),
    ]

    operations = [
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.CharField(max_length=80)),
                ('permissions', models.ManyToManyField(to='profiles.Permission')),
            ],
        ),
        migrations.AddField(
            model_name='group',
            name='profiles',
            field=models.ManyToManyField(to='profiles.Profile'),
        ),
    ]