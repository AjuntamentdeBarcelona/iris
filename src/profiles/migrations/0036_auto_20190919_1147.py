# Generated by Django 2.1.1 on 2019-09-19 09:47

from django.db import migrations, models
import main.api.validators


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0035_auto_20190918_1024'),
    ]

    operations = [
        migrations.AlterField(
            model_name='group',
            name='notifications_emails',
            field=models.TextField(blank=True, help_text='List of emails (separated by commas) to send notifications', validators=[main.api.validators.EmailCommasSeparatedValidator()], verbose_name='Notifications emails list'),
        ),
    ]