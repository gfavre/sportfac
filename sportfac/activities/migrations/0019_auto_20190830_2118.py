# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2019-08-30 19:18
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('activities', '0018_extraneed_price_reduction'),
    ]

    operations = [
        migrations.AlterField(
            model_name='course',
            name='day',
            field=models.PositiveSmallIntegerField(blank=True, choices=[(1, 'Monday'), (2, 'Tuesday'), (3, 'Wednesday'), (4, 'Thursday'), (5, 'Friday'), (6, 'Saturday'), (7, 'Sunday')], default=1, verbose_name='Day'),
        ),
    ]