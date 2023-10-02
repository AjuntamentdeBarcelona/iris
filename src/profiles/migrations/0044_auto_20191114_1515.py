# Generated by Django 2.1.1 on 2019-11-14 14:15

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0043_auto_20191030_1744'),
        ('iris_masters', '0062_lettertemplate'),
    ]

    operations = [
        migrations.AlterField(
            model_name='group',
            name='letter_template_id',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='iris_masters.LetterTemplate', verbose_name='Letter template id'),
        ),
    ]