# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2017-01-13 08:51
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('registrations', '0014_data_add_transport'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='registration',
            name='transport_info',
        ),
    ]