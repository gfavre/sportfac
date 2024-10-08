# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-07-11 16:00
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mailer", "0002_attachment"),
    ]

    operations = [
        migrations.AlterField(
            model_name="attachment",
            name="mail",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="attachments",
                to="mailer.MailArchive",
            ),
        ),
    ]
