# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-08-15 14:25
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('activities', '0006_copy_instructors'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='course',
            name='responsible',
        ),
    ]