# Generated by Django 2.1.1 on 2019-06-12 10:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('record_cards', '0053_auto_20190604_1632'),
    ]

    operations = [
        migrations.AddField(
            model_name='recordcardfeatures',
            name='is_theme_feature',
            field=models.BooleanField(db_index=True, default=True, help_text='Shows if the related feature is from the current record theme', verbose_name='Is theme feature'),
        ),
        migrations.AddField(
            model_name='recordcardspecialfeatures',
            name='is_theme_feature',
            field=models.BooleanField(db_index=True, default=True, help_text='Shows if the related feature is from the current record theme', verbose_name='Is theme feature'),
        ),
    ]
