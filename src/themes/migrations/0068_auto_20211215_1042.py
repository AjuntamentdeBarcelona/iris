# Generated by Django 2.2 on 2021-12-15 09:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('themes', '0067_auto_20211215_1036'),
    ]

    operations = [
        migrations.AlterField(
            model_name='zone',
            name='codename',
            field=models.CharField(db_index=True, max_length=20, unique=True, verbose_name='Codename'),
        ),
    ]