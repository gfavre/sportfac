# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2020-06-08 05:41
from __future__ import unicode_literals

from django.db import migrations
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('registrations', '0031_auto_20200108_1151'),
    ]

    operations = [
        migrations.AddField(
            model_name='child',
            name='status',
            field=model_utils.fields.StatusField(choices=[(0, 'dummy')], default='updated', max_length=100, no_check_for_status=True, verbose_name='status'),
        ),
        migrations.AddField(
            model_name='child',
            name='status_changed',
            field=model_utils.fields.MonitorField(default=django.utils.timezone.now, monitor='status', verbose_name='status changed'),
        ),
    ]