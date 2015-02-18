# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0008_initial_templates'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='familyuser',
            options={'ordering': ('last_name', 'first_name'), 'get_latest_by': 'date_joined'},
        ),
        migrations.AlterField(
            model_name='schoolyear',
            name='year',
            field=models.PositiveIntegerField(unique=True, verbose_name='School year', choices=[(1, '1p HARMOS'), (2, '2p HARMOS'), (3, '3p HARMOS'), (4, '4p HARMOS'), (5, '5p HARMOS'), (6, '6p HARMOS'), (7, '7p HARMOS'), (8, '8p HARMOS'), (9, '9S HARMOS'), (10, '10S HARMOS'), (11, '11S HARMOS')]),
            preserve_default=True,
        ),
    ]
