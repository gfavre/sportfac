# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('activities', '0006_auto_20150218_0942'),
    ]

    operations = [
        migrations.AddField(
            model_name='activity',
            name='created',
            field=models.DateTimeField(default=datetime.datetime(2015, 2, 20, 9, 46, 36, 105062, tzinfo=utc), auto_now_add=True, db_index=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='activity',
            name='modified',
            field=models.DateTimeField(default=datetime.datetime(2015, 2, 20, 9, 46, 39, 780649, tzinfo=utc), auto_now=True, db_index=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='course',
            name='created',
            field=models.DateTimeField(default=datetime.datetime(2015, 2, 20, 9, 46, 44, 280312, tzinfo=utc), auto_now_add=True, db_index=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='course',
            name='modified',
            field=models.DateTimeField(default=datetime.datetime(2015, 2, 20, 9, 46, 46, 624035, tzinfo=utc), auto_now=True, db_index=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='extraneed',
            name='created',
            field=models.DateTimeField(default=datetime.datetime(2015, 2, 20, 9, 46, 51, 318561, tzinfo=utc), auto_now_add=True, db_index=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='extraneed',
            name='modified',
            field=models.DateTimeField(default=datetime.datetime(2015, 2, 20, 9, 46, 54, 490370, tzinfo=utc), auto_now=True, db_index=True),
            preserve_default=False,
        ),
    ]
