# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import ckeditor.fields


class Migration(migrations.Migration):

    dependencies = [
        ('activities', '0007_auto_20150220_1046'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='activity',
            options={'ordering': ['name'], 'verbose_name': 'activity', 'verbose_name_plural': 'activities'},
        ),
        migrations.AlterModelOptions(
            name='course',
            options={'ordering': ('activity__name', 'number'), 'verbose_name': 'course', 'verbose_name_plural': 'courses'},
        ),
        migrations.AlterField(
            model_name='activity',
            name='informations',
            field=ckeditor.fields.RichTextField(help_text='Specific informations like outfit.', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='activity',
            name='name',
            field=models.CharField(unique=True, max_length=50, verbose_name='Name', db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='activity',
            name='number',
            field=models.IntegerField(db_index=True, unique=True, null=True, verbose_name='Number', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='activity',
            name='slug',
            field=models.SlugField(help_text='Part of the url. Cannot contain punctuation, spaces or accentuated letters', unique=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='course',
            name='activity',
            field=models.ForeignKey(related_name='courses', verbose_name='Activity', to='activities.Activity'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='course',
            name='day',
            field=models.PositiveSmallIntegerField(default=1, verbose_name='Day', choices=[(1, 'Lundi'), (2, 'Mardi'), (3, 'Mercredi'), (4, 'Jeudi'), (5, 'Vendredi'), (6, 'Samedi'), (7, 'Dimanche')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='course',
            name='end_date',
            field=models.DateField(verbose_name='End date'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='course',
            name='end_time',
            field=models.TimeField(verbose_name='End time'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='course',
            name='max_participants',
            field=models.PositiveSmallIntegerField(verbose_name='Maximal number of participants'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='course',
            name='min_participants',
            field=models.PositiveSmallIntegerField(verbose_name='Minimal number of participants'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='course',
            name='number',
            field=models.IntegerField(db_index=True, unique=True, null=True, verbose_name='Identifier', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='course',
            name='number_of_sessions',
            field=models.PositiveSmallIntegerField(verbose_name='Number of sessions'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='course',
            name='place',
            field=models.TextField(verbose_name='Place'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='course',
            name='price',
            field=models.DecimalField(verbose_name='Price', max_digits=5, decimal_places=2),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='course',
            name='responsible',
            field=models.ForeignKey(related_name='courses', verbose_name='Responsible', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='course',
            name='schoolyear_max',
            field=models.PositiveIntegerField(default=b'8', verbose_name='Maximal school year', choices=[(1, '1p HARMOS'), (2, '2p HARMOS'), (3, '3p HARMOS'), (4, '4p HARMOS'), (5, '5p HARMOS'), (6, '6p HARMOS'), (7, '7p HARMOS'), (8, '8p HARMOS'), (9, '9S HARMOS'), (10, '10S HARMOS'), (11, '11S HARMOS')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='course',
            name='schoolyear_min',
            field=models.PositiveIntegerField(default=b'1', verbose_name='Minimal school year', choices=[(1, '1p HARMOS'), (2, '2p HARMOS'), (3, '3p HARMOS'), (4, '4p HARMOS'), (5, '5p HARMOS'), (6, '6p HARMOS'), (7, '7p HARMOS'), (8, '8p HARMOS'), (9, '9S HARMOS'), (10, '10S HARMOS'), (11, '11S HARMOS')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='course',
            name='start_date',
            field=models.DateField(verbose_name='Start date'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='course',
            name='start_time',
            field=models.TimeField(verbose_name='Start time'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='course',
            name='uptodate',
            field=models.BooleanField(default=True, verbose_name='Course up to date'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='extraneed',
            name='question_label',
            field=models.CharField(help_text='e.g. Shoes size?', max_length=255, verbose_name='Question'),
            preserve_default=True,
        ),
    ]
