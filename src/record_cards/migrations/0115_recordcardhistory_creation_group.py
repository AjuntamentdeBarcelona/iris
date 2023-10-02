# Generated by Django 2.1.1 on 2020-03-03 10:46

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0059_group_tree_levels'),
        ('record_cards', '0114_auto_20200228_1142'),
    ]

    operations = [
        migrations.AddField(
            model_name='recordcardhistory',
            name='creation_group',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='history_create_records', to='profiles.Group', verbose_name='Creation group'),
        ),
    ]
