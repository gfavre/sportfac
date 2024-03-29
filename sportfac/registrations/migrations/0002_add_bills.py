# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-05-13 13:01
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("registrations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Bill",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "status",
                    model_utils.fields.StatusField(
                        choices=[
                            ("waiting", "Waiting parent's payment"),
                            ("paid", "Paid by parent"),
                            ("canceled", "Canceled by administrator"),
                        ],
                        default="waiting",
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
                ("created", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("modified", models.DateTimeField(auto_now=True, db_index=True)),
                (
                    "billing_identifier",
                    models.CharField(blank=True, max_length=45, verbose_name="Billing identifier"),
                ),
                ("total", models.PositiveIntegerField(default=0, verbose_name="Total to be paid")),
                (
                    "family",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bills",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.AddField(
            model_name="registration",
            name="paid",
            field=models.BooleanField(default=False, verbose_name="Has paid"),
        ),
        migrations.AddField(
            model_name="registration",
            name="bill",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="registrations",
                to="registrations.Bill",
            ),
        ),
    ]
