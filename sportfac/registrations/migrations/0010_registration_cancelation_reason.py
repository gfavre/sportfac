# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-12-03 14:00
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('registrations', '0009_auto_20211008_1656'),
    ]

    operations = [
        migrations.AddField(
            model_name='registration',
            name='cancelation_reason',
            field=models.CharField(blank=True, choices=[('expired', 'Expired'), ('admin', 'Admin')], max_length=20, null=True, verbose_name='Cancelation reason'),
        ),
    ]