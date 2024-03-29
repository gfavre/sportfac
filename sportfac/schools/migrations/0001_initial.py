# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-05-05 16:09
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("profiles", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Teacher",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("modified", models.DateTimeField(auto_now=True, db_index=True)),
                (
                    "number",
                    models.IntegerField(
                        blank=True, db_index=True, null=True, unique=True, verbose_name="Number"
                    ),
                ),
                ("first_name", models.CharField(max_length=50, verbose_name="First name")),
                (
                    "last_name",
                    models.CharField(db_index=True, max_length=50, verbose_name="Last name"),
                ),
                (
                    "email",
                    models.EmailField(
                        blank=True, max_length=255, null=True, verbose_name="Email address"
                    ),
                ),
                (
                    "years",
                    models.ManyToManyField(to="profiles.SchoolYear", verbose_name="School years"),
                ),
            ],
            options={
                "ordering": ("last_name", "first_name"),
                "verbose_name": "teacher",
                "verbose_name_plural": "teachers",
            },
        ),
    ]
