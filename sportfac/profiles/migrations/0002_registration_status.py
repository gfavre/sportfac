# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='registration',
            name='status',
            field=models.CharField(default=b'waiting', max_length=20, choices=[(b'waiting', "Waiting parent's confirmation"), (b'validated', 'Validated by parent'), (b'canceled', 'Canceled by administrator'), (b'confirmed', 'Confirmed by administrator')]),
            preserve_default=True,
        ),
    ]
