# Generated by Django 2.1.1 on 2019-02-25 15:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('record_cards', '0022_auto_20190222_1156'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recordcard',
            name='ans_overcome',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='ANS overcome'),
        ),
    ]
