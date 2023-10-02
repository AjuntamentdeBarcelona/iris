# Generated by Django 2.1.1 on 2018-12-12 10:33

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('themes', '0008_auto_20181210_1227'),
    ]

    operations = [
        migrations.AddField(
            model_name='element',
            name='deleted',
            field=models.DateTimeField(editable=False, null=True),
        ),
        migrations.AlterField(
            model_name='elementdetail',
            name='element',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='elements', to='themes.Element'),
        ),
    ]