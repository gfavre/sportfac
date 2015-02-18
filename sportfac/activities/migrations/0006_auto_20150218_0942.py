# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('activities', '0005_remove_responsible_model'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Responsible',
        ),
        migrations.AlterField(
            model_name='course',
            name='schoolyear_max',
            field=models.PositiveIntegerField(default=b'8', verbose_name='Ann\xe9e scolaire maximale', choices=[(1, '1p HARMOS'), (2, '2p HARMOS'), (3, '3p HARMOS'), (4, '4p HARMOS'), (5, '5p HARMOS'), (6, '6p HARMOS'), (7, '7p HARMOS'), (8, '8p HARMOS'), (9, '9S HARMOS'), (10, '10S HARMOS'), (11, '11S HARMOS')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='course',
            name='schoolyear_min',
            field=models.PositiveIntegerField(default=b'1', verbose_name='Ann\xe9e scolaire minimale', choices=[(1, '1p HARMOS'), (2, '2p HARMOS'), (3, '3p HARMOS'), (4, '4p HARMOS'), (5, '5p HARMOS'), (6, '6p HARMOS'), (7, '7p HARMOS'), (8, '8p HARMOS'), (9, '9S HARMOS'), (10, '10S HARMOS'), (11, '11S HARMOS')]),
            preserve_default=True,
        ),
    ]
