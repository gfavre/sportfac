# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2022-08-18 15:38
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('activities', '0016_auto_20220811_0849'),
    ]

    operations = [
        migrations.AddField(
            model_name='activity',
            name='type',
            field=models.CharField(choices=[(b'activity', 'Activities')], db_index=True, default=b'activity', max_length=50, verbose_name='Type'),
        ),
    ]