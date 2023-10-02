# Generated by Django 2.1.1 on 2019-06-03 14:52

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('iris_masters', '0036_externalservice'),
        ('themes', '0039_auto_20190530_1600'),
    ]

    operations = [
        migrations.AddField(
            model_name='elementdetail',
            name='external_service',
            field=models.ForeignKey(blank=True, help_text='Validate and manage by sending the card to an external service', null=True, on_delete=django.db.models.deletion.SET_NULL, to='iris_masters.ExternalService'),
        ),
    ]