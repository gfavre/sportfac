# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0013_auto_20150219_1942'),
    ]

    operations = [
        migrations.AlterField(
            model_name='schoolyear',
            name='year',
            field=models.PositiveIntegerField(unique=True, verbose_name='School year', choices=[(1, '1st HARMOS'), (2, '2nd HARMOS'), (3, '3rd HARMOS'), (4, '4th HARMOS'), (5, '5th HARMOS'), (6, '6th HARMOS'), (7, '7th HARMOS'), (8, '8th HARMOS'), (9, '9th HARMOS'), (10, '10th HARMOS'), (11, '11th HARMOS')]),
            preserve_default=True,
        ),
    ]
