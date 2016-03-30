# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('SilentD', '0006_auto_20160314_1443'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='miseq',
            name='RunInfo',
        ),
        migrations.RemoveField(
            model_name='miseq',
            name='RunStats',
        ),
        migrations.RemoveField(
            model_name='miseq',
            name='SampleSheet',
        ),
        migrations.RemoveField(
            model_name='miseq',
            name='amr_results',
        ),
        migrations.RemoveField(
            model_name='miseq',
            name='geneseekr_results',
        ),
        migrations.RemoveField(
            model_name='miseq',
            name='mlst_results',
        ),
    ]
