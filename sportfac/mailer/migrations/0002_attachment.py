# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-07-08 13:40
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models

import mailer.models
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ("mailer", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Attachment",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
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
                ("file", models.FileField(upload_to=mailer.models.attachment_path)),
                (
                    "mail",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="mailer.MailArchive"
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
