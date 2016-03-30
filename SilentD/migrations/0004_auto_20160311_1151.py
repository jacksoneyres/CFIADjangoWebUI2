# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('SilentD', '0003_auto_20160226_1333'),
    ]

    operations = [
        migrations.AddField(
            model_name='mlst',
            name='reference',
            field=models.FileField(upload_to=b'', blank=True),
        ),
        migrations.AlterField(
            model_name='primerv',
            name='misses',
            field=models.FileField(upload_to=b'', blank=True),
        ),
        migrations.AlterField(
            model_name='primerv',
            name='result',
            field=models.FileField(upload_to=b'', blank=True),
        ),
    ]
