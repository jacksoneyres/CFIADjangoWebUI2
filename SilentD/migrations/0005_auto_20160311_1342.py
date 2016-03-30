# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('SilentD', '0004_auto_20160311_1151'),
    ]

    operations = [
        migrations.AlterField(
            model_name='amr',
            name='organism',
            field=models.CharField(default=False, max_length=200),
        ),
        migrations.AlterField(
            model_name='galaxy',
            name='organism',
            field=models.CharField(default=False, max_length=200),
        ),
        migrations.AlterField(
            model_name='genes',
            name='organism',
            field=models.CharField(default=False, max_length=200),
        ),
        migrations.AlterField(
            model_name='mlst',
            name='organism',
            field=models.CharField(default=False, max_length=200),
        ),
        migrations.AlterField(
            model_name='primerv',
            name='organism',
            field=models.CharField(default=False, max_length=200),
        ),
        migrations.AlterField(
            model_name='snp',
            name='organism',
            field=models.CharField(default=False, max_length=200),
        ),
    ]
