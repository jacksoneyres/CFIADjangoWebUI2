# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('SilentD', '0007_auto_20160316_1155'),
    ]

    operations = [
        migrations.AddField(
            model_name='miseq',
            name='run_info',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='miseq',
            name='run_stats',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='miseq',
            name='sample_sheet',
            field=models.BooleanField(default=False),
        ),
    ]
