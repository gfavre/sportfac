# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0012_zipcodes'),
    ]

    operations = [
        migrations.AddField(
            model_name='teacher',
            name='created',
            field=models.DateTimeField(default=datetime.datetime(2015, 2, 19, 18, 42, 22, 136392, tzinfo=utc), auto_now_add=True, db_index=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='teacher',
            name='modified',
            field=models.DateTimeField(default=datetime.datetime(2015, 2, 19, 18, 42, 31, 886362, tzinfo=utc), auto_now=True, db_index=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='registration',
            name='child',
            field=models.ForeignKey(related_name='registrations', to='profiles.Child'),
            preserve_default=True,
        ),
    ]
