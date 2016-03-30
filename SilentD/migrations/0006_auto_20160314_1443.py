# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('SilentD', '0005_auto_20160311_1342'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='profile',
            name='beta_access',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='genome_access',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='title',
        ),
        migrations.AddField(
            model_name='profile',
            name='lab',
            field=models.CharField(blank=True, max_length=100, choices=[(1, b'St-Johns'), (2, b'Dartmouth'), (3, b'Charlottetown'), (4, b'St-Hyacinthe'), (5, b'Longeuil'), (6, b'Fallowfield'), (7, b'Carling'), (8, b'Greater Toronto Area'), (9, b'Winnipeg'), (10, b'Saskatoon'), (11, b'Calgary'), (12, b'Lethbridge'), (13, b'Burnaby'), (14, b'Sidney'), (15, b'Other')]),
        ),
    ]
