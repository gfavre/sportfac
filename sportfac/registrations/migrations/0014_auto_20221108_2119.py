# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2022-11-08 20:19
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('registrations', '0013_auto_20221028_1740'),
    ]

    operations = [
        migrations.AlterField(
            model_name='child',
            name='avs',
            field=models.CharField(blank=True, default='', max_length=16, verbose_name='AVS'),
        ),
    ]