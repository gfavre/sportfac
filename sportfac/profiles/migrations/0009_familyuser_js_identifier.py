# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2018-07-23 13:53
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0008_auto_20180126_1722"),
    ]

    operations = [
        migrations.AddField(
            model_name="familyuser",
            name="js_identifier",
            field=models.CharField(blank=True, max_length=30, verbose_name="J+S identifier"),
        ),
    ]
