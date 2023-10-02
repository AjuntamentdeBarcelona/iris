# Generated by Django 2.1.1 on 2019-03-14 15:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('record_cards', '0028_auto_20190313_1813'),
    ]

    operations = [
        migrations.AlterField(
            model_name='citizen',
            name='language',
            field=models.CharField(choices=[('es', 'Spanish'), ('en', 'English'), ('ca', 'Catalan')], default='ca', max_length=2, verbose_name='Language'),
        ),
        migrations.AlterField(
            model_name='socialentity',
            name='language',
            field=models.CharField(choices=[('es', 'Spanish'), ('en', 'English'), ('ca', 'Catalan')], default='ca', max_length=2, verbose_name='Language'),
        ),
    ]
