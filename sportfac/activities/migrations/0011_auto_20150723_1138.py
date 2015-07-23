# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('activities', '0010_auto_20150317_1025'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activity',
            name='number',
            field=models.CharField(null=True, max_length=30, blank=True, unique=True, verbose_name='Identifier', db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='course',
            name='number',
            field=models.CharField(null=True, max_length=30, blank=True, unique=True, verbose_name='Identifier', db_index=True),
            preserve_default=True,
        ),
    ]
