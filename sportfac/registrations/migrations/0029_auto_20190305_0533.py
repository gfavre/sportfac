# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2019-03-05 04:33
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("registrations", "0028_auto_20181119_0621"),
    ]

    operations = [
        migrations.AlterField(
            model_name="registration",
            name="transport",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="participants",
                to="registrations.Transport",
                verbose_name="Transport information",
            ),
        ),
    ]
