# Generated by Django 2.1.1 on 2019-04-25 14:58

from django.db import migrations, models
import django.db.models.deletion
import iris_masters.models


class Migration(migrations.Migration):

    dependencies = [
        ('iris_masters', '0034_auto_20190412_1159'),
        ('profiles', '0013_auto_20190425_1223'),
        ('record_cards', '0046_auto_20190506_1218'),
    ]

    operations = [
        migrations.CreateModel(
            name='RecordCardReasignation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', iris_masters.models.UserIdField(max_length=20, verbose_name='User ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Creation date')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last update')),
                ('comment', models.TextField(verbose_name='Comment')),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='profiles.Group', verbose_name='User Group')),
                ('next_responsible_profile', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='next_responsible', to='profiles.Group', verbose_name='Next Responsible Group')),
                ('previous_responsible_profile', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='previous_responsible', to='profiles.Group', verbose_name='Previuos Responsible Group')),
                ('reason', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='iris_masters.Reason', verbose_name='Reason')),
                ('record_card', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='record_cards.RecordCard', verbose_name='Record Card')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
