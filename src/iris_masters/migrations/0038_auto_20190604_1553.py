# Generated by Django 2.1.1 on 2019-06-04 13:53

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('iris_masters', '0037_auto_20190604_1537'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='inputchannel',
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name='inputchannelapplicanttype',
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name='inputchannelsupport',
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name='recordstate',
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name='responsechannelsupport',
            unique_together=set(),
        ),
    ]
