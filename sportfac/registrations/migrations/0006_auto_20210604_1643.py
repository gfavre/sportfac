# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-06-04 14:43
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("registrations", "0005_auto_20210507_1644"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="child",
            options={
                "ordering": ("last_name", "first_name"),
                "verbose_name": "Child",
                "verbose_name_plural": "Children",
            },
        ),
        migrations.AlterField(
            model_name="registration",
            name="allocation_account",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="registrations",
                to="activities.AllocationAccount",
                verbose_name="Allocation account",
            ),
        ),
        migrations.AlterField(
            model_name="registration",
            name="price",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
