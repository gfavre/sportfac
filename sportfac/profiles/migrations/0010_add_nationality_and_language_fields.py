# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0009_auto_20150218_0942'),
    ]

    operations = [
        migrations.AddField(
            model_name='child',
            name='language',
            field=models.CharField(default=b'F', max_length=2, choices=[(b'D', b'Deutsch'), (b'E', b'English'), (b'F', 'Fran\xe7ais'), (b'I', b'Italiano')]),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='child',
            name='nationality',
            field=models.CharField(default=b'CH', max_length=3, choices=[(b'CH', 'Swiss'), (b'FL', 'Liechtenstein'), (b'DIV', 'Other')]),
            preserve_default=True,
        ),
    ]
