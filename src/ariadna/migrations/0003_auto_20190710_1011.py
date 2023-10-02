# Generated by Django 2.1.1 on 2019-07-10 08:11

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('record_cards', '0058_auto_20190628_1403'),
        ('ariadna', '0002_auto_20190703_1452'),
    ]

    operations = [
        migrations.CreateModel(
            name='AriadnaRecord',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=12)),
                ('fitxa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='record_cards.RecordCard')),
            ],
        ),
        migrations.AddField(
            model_name='ariadna',
            name='code',
            field=models.CharField(default='', max_length=12),
        ),
    ]