# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('SilentD', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mlst',
            name='result',
            field=models.FileField(upload_to=b'', blank=True),
        ),
        migrations.AlterField(
            model_name='mlst',
            name='rmlst_result',
            field=models.FileField(upload_to=b'', blank=True),
        ),
    ]
