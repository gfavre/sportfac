# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2017-07-31 13:33
from __future__ import unicode_literals

from django.db import migrations
import sportfac.models


class Migration(migrations.Migration):

    dependencies = [
        ('mailer', '0003_auto_20160711_1800'),
    ]

    operations = [
        migrations.AddField(
            model_name='mailarchive',
            name='bcc_recipients',
            field=sportfac.models.ListField(null=True, verbose_name='BCC recipients'),
        ),
    ]