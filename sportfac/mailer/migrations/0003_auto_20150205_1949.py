# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import sportfac.models


class Migration(migrations.Migration):

    dependencies = [
        ('mailer', '0002_auto_20150124_1651'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mailarchive',
            name='messages',
            field=sportfac.models.ListField(verbose_name='Message'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='mailarchive',
            name='recipients',
            field=sportfac.models.ListField(verbose_name='Destinataires'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='mailarchive',
            name='subject',
            field=models.CharField(max_length=255, verbose_name='Sujet'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='mailarchive',
            name='template',
            field=models.CharField(max_length=255, verbose_name='Mod\xe8le'),
            preserve_default=True,
        ),
    ]
