# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-04-08 03:39
import uuid

import django.contrib.postgres.fields.jsonb
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models

import model_utils.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("registrations", "0002_add_bills"),
    ]

    operations = [
        migrations.CreateModel(
            name="DatatransTransaction",
            fields=[
                (
                    "created",
                    model_utils.fields.AutoCreatedField(
                        default=django.utils.timezone.now, editable=False, verbose_name="created"
                    ),
                ),
                (
                    "modified",
                    model_utils.fields.AutoLastModifiedField(
                        default=django.utils.timezone.now, editable=False, verbose_name="modified"
                    ),
                ),
                (
                    "status",
                    model_utils.fields.StatusField(
                        choices=[
                            ("initialized", "Initialized"),
                            ("challenge_required", "Challenge required"),
                            ("challenge_ongoing", "Challenge ongoing"),
                            ("authenticated", "Authenticated"),
                            ("authorized", "Authorized"),
                            ("settled", "Settled"),
                            ("canceled", "Canceled"),
                            ("transmitted", "Transmitted"),
                            ("failed", "Failed"),
                        ],
                        default="initialized",
                        max_length=100,
                        no_check_for_status=True,
                        verbose_name="status",
                    ),
                ),
                (
                    "status_changed",
                    model_utils.fields.MonitorField(
                        default=django.utils.timezone.now,
                        monitor="status",
                        verbose_name="status changed",
                    ),
                ),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                ("transaction_id", models.IntegerField()),
                ("webhook", django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ("expiration", models.DateTimeField(null=True)),
                (
                    "invoice",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="registrations.Bill"
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
