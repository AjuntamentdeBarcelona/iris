# Generated by Django 2.1.1 on 2020-01-21 15:01

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0055_auto_20200116_0919'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='profile',
            options={'ordering': ('description',)},
        ),
        migrations.AlterModelOptions(
            name='usergroup',
            options={'ordering': ('user__username',)},
        ),
    ]
