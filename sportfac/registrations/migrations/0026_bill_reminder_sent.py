# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-10-15 19:09
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("registrations", "0025_auto_20180808_1112"),
    ]

    operations = [
        migrations.AddField(
            model_name="bill",
            name="reminder_sent",
            field=models.BooleanField(default=False, verbose_name="Reminder sent"),
        ),
    ]
