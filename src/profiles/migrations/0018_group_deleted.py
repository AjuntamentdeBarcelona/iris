# Generated by Django 2.1.1 on 2019-06-03 07:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0017_auto_20190508_1143'),
    ]

    operations = [
        migrations.AddField(
            model_name='group',
            name='deleted',
            field=models.DateTimeField(editable=False, null=True),
        ),
        migrations.AlterUniqueTogether(
            name='group',
            unique_together={('description', 'profile_ctrl_user_id', 'deleted')},
        ),
    ]
