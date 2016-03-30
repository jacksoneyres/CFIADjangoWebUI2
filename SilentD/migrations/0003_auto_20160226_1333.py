# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('SilentD', '0002_auto_20160225_1049'),
    ]

    operations = [
        migrations.AlterField(
            model_name='project',
            name='amr_results',
            field=models.CharField(max_length=50, blank=True),
        ),
        migrations.AlterField(
            model_name='project',
            name='geneseekr_results',
            field=models.CharField(max_length=50, blank=True),
        ),
        migrations.AlterField(
            model_name='project',
            name='mlst_results',
            field=models.CharField(max_length=50, blank=True),
        ),
        migrations.AlterField(
            model_name='project',
            name='spades_results',
            field=models.CharField(max_length=50, blank=True),
        ),
    ]
