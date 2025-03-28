# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2019-01-02 06:58
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("activities", "0018_extraneed_price_reduction"),
        ("absences", "0008_auto_20180217_0738"),
    ]

    operations = [
        migrations.AddField(
            model_name="session",
            name="activity",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="sessions",
                to="activities.Activity",
            ),
        ),
    ]
