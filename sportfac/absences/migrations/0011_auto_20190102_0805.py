# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2019-01-02 07:05
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('absences', '0010_dm_sessions_activities'),
    ]

    operations = [
        migrations.AlterField(
            model_name='session',
            name='activity',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sessions', to='activities.Activity'),
        ),
    ]