# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2020-10-29 14:24
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('appointments', '0003_auto_20201014_1203'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appointment',
            name='slot',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='appointments', to='appointments.AppointmentSlot'),
        ),
    ]