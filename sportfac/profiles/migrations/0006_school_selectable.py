# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2017-02-10 05:55
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0005_auto_20170103_0835'),
    ]

    operations = [
        migrations.AddField(
            model_name='school',
            name='selectable',
            field=models.BooleanField(default=True),
        ),
    ]