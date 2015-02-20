# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('activities', '0008_auto_20150220_1938'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='activity',
            options={'ordering': ['name'], 'verbose_name': 'activit\xe9', 'verbose_name_plural': 'activit\xe9s'},
        ),
        migrations.AlterModelOptions(
            name='course',
            options={'ordering': ('activity__name', 'number'), 'verbose_name': 'cours', 'verbose_name_plural': 'cours'},
        ),
        migrations.AlterField(
            model_name='course',
            name='day',
            field=models.PositiveSmallIntegerField(default=1, verbose_name='Day', choices=[(1, 'Monday'), (2, 'Tuesday'), (3, 'Wednesday'), (4, 'Thursday'), (5, 'Friday'), (6, 'Saturday'), (7, 'Sunday')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='course',
            name='schoolyear_max',
            field=models.PositiveIntegerField(default=b'8', verbose_name='Maximal school year', choices=[(1, '1st HARMOS'), (2, '2nd HARMOS'), (3, '3rd HARMOS'), (4, '4th HARMOS'), (5, '5th HARMOS'), (6, '6th HARMOS'), (7, '7th HARMOS'), (8, '8th HARMOS'), (9, '9th HARMOS'), (10, '10th HARMOS'), (11, '11th HARMOS')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='course',
            name='schoolyear_min',
            field=models.PositiveIntegerField(default=b'1', verbose_name='Minimal school year', choices=[(1, '1st HARMOS'), (2, '2nd HARMOS'), (3, '3rd HARMOS'), (4, '4th HARMOS'), (5, '5th HARMOS'), (6, '6th HARMOS'), (7, '7th HARMOS'), (8, '8th HARMOS'), (9, '9th HARMOS'), (10, '10th HARMOS'), (11, '11th HARMOS')]),
            preserve_default=True,
        ),
    ]
