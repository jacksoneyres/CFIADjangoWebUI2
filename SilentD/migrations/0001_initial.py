# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings
import SilentD.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AMR',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('user', models.CharField(default=b' ', max_length=200)),
                ('job_id', models.CharField(max_length=200, blank=True)),
                ('tag', models.CharField(max_length=200, blank=True)),
                ('type', models.CharField(default=False, max_length=50)),
                ('organism', models.CharField(default=False, max_length=50)),
                ('error', models.CharField(max_length=200, blank=True)),
                ('result', models.FileField(upload_to=b'', blank=True)),
                ('result2', models.FileField(upload_to=b'', blank=True)),
                ('result3', models.FileField(upload_to=b'', blank=True)),
                ('result4', models.FileField(upload_to=b'', blank=True)),
                ('result5', models.FileField(upload_to=b'', blank=True)),
                ('gene_count', models.CharField(max_length=200, blank=True)),
                ('data_id', models.CharField(default=False, max_length=100)),
                ('genome', models.FileField(upload_to=b'', blank=True)),
                ('identity', models.IntegerField(default=80)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Data',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('user', models.CharField(default=b' ', max_length=200)),
                ('description', models.CharField(max_length=200, blank=True)),
                ('file', models.FileField(upload_to=SilentD.models.generate_path, blank=True)),
                ('name', models.CharField(max_length=200, blank=True)),
                ('type', models.CharField(max_length=20, blank=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Galaxy',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('user', models.CharField(default=b' ', max_length=200)),
                ('job_id', models.CharField(max_length=200, blank=True)),
                ('tag', models.CharField(max_length=200, blank=True)),
                ('type', models.CharField(default=False, max_length=50)),
                ('organism', models.CharField(default=False, max_length=50)),
                ('error', models.CharField(max_length=200, blank=True)),
                ('result', models.FileField(default=False, upload_to=b'', blank=True)),
                ('profile', models.CharField(max_length=200, blank=True)),
                ('data_id', models.CharField(default=False, max_length=100)),
                ('genome', models.FileField(upload_to=SilentD.models.generate_path, blank=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='GeneS',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('user', models.CharField(default=b' ', max_length=200)),
                ('job_id', models.CharField(max_length=200, blank=True)),
                ('tag', models.CharField(max_length=200, blank=True)),
                ('type', models.CharField(default=False, max_length=50)),
                ('organism', models.CharField(default=False, max_length=50)),
                ('error', models.CharField(max_length=200, blank=True)),
                ('result', models.FileField(upload_to=b'', blank=True)),
                ('genes', models.CharField(default=False, max_length=50)),
                ('targets', models.FileField(upload_to=SilentD.models.generate_targetpath, blank=True)),
                ('cutoff', models.CharField(default=0.8, max_length=50)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='MiSeq',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('user', models.CharField(default=b' ', max_length=200)),
                ('description', models.CharField(max_length=200, blank=True)),
                ('type', models.CharField(max_length=20, blank=True)),
                ('missing', models.BooleanField(default=False)),
                ('RunInfo', models.FileField(upload_to=SilentD.models.generate_path, blank=True)),
                ('SampleSheet', models.FileField(upload_to=SilentD.models.generate_path, blank=True)),
                ('RunStats', models.FileField(upload_to=SilentD.models.generate_path, blank=True)),
                ('mlst_results', models.CharField(default=False, max_length=50)),
                ('amr_results', models.CharField(default=False, max_length=50)),
                ('geneseekr_results', models.CharField(default=False, max_length=50)),
                ('job_id', models.CharField(max_length=20, blank=True)),
                ('assemblies', models.FileField(upload_to=b'', blank=True)),
                ('reports', models.FileField(upload_to=b'', blank=True)),
                ('error', models.CharField(max_length=200, blank=True)),
                ('files', models.ManyToManyField(to='SilentD.Data')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='MLST',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('user', models.CharField(default=b' ', max_length=200)),
                ('job_id', models.CharField(max_length=200, blank=True)),
                ('tag', models.CharField(max_length=200, blank=True)),
                ('type', models.CharField(default=False, max_length=50)),
                ('organism', models.CharField(default=False, max_length=50)),
                ('error', models.CharField(max_length=200, blank=True)),
                ('result', models.FileField(default=False, upload_to=b'', blank=True)),
                ('rmlst_result', models.FileField(default=False, upload_to=b'', blank=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='PrimerV',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('user', models.CharField(default=b' ', max_length=200)),
                ('job_id', models.CharField(max_length=200, blank=True)),
                ('tag', models.CharField(max_length=200, blank=True)),
                ('type', models.CharField(default=False, max_length=50)),
                ('organism', models.CharField(default=False, max_length=50)),
                ('error', models.CharField(max_length=200, blank=True)),
                ('result', models.FileField(default=False, upload_to=b'', blank=True)),
                ('forward', models.CharField(default=False, max_length=50)),
                ('reverse', models.CharField(default=False, max_length=50)),
                ('forward_gc', models.CharField(default=False, max_length=50)),
                ('reverse_gc', models.CharField(default=False, max_length=50)),
                ('target', models.CharField(default=False, max_length=50)),
                ('mism', models.CharField(default=False, max_length=50)),
                ('hits', models.CharField(default=False, max_length=50)),
                ('misses', models.FileField(default=False, upload_to=b'', blank=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('rank', models.CharField(default=b'Diagnostic', max_length=100, choices=[(b'Diagnostic', b'Diagnostic'), (b'Research', b'Research'), (b'Manager', b'Manager'), (b'Quality', b'Quality'), (b'Super', b'Super')])),
                ('cfia_access', models.BooleanField(default=False)),
                ('beta_access', models.BooleanField(default=False)),
                ('genome_access', models.BooleanField(default=False)),
                ('title', models.CharField(default=b'Default', max_length=100)),
                ('user', models.OneToOneField(to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('user', models.CharField(default=b' ', max_length=200)),
                ('description', models.CharField(max_length=200, blank=True)),
                ('num_files', models.IntegerField(default=0)),
                ('organism', models.CharField(max_length=200, blank=True)),
                ('type', models.CharField(max_length=20, blank=True)),
                ('mlst_results', models.CharField(default=False, max_length=50)),
                ('amr_results', models.CharField(default=False, max_length=50)),
                ('geneseekr_results', models.CharField(default=False, max_length=50)),
                ('spades_results', models.CharField(default=False, max_length=50)),
                ('spades_results_file', models.FileField(upload_to=b'', blank=True)),
                ('spades_log_file', models.FileField(upload_to=b'', blank=True)),
                ('files', models.ManyToManyField(to='SilentD.Data')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='SNP',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('user', models.CharField(default=b' ', max_length=200)),
                ('job_id', models.CharField(max_length=200, blank=True)),
                ('tag', models.CharField(max_length=200, blank=True)),
                ('type', models.CharField(default=False, max_length=50)),
                ('organism', models.CharField(default=False, max_length=50)),
                ('error', models.CharField(max_length=200, blank=True)),
                ('result', models.FileField(default=False, upload_to=b'', blank=True)),
                ('tree', models.FileField(default=False, upload_to=b'', blank=True)),
                ('upload', models.FileField(upload_to=SilentD.models.generate_path, blank=True)),
                ('snps', models.IntegerField(null=True, blank=True)),
                ('data_id', models.CharField(default=False, max_length=100)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='mlst',
            name='project',
            field=models.ForeignKey(to='SilentD.Project'),
        ),
        migrations.AddField(
            model_name='amr',
            name='project',
            field=models.ForeignKey(to='SilentD.Project'),
        ),
    ]
