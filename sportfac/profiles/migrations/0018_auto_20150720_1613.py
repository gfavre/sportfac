# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import profiles.ahv


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0017_auto_20150317_1659'),
    ]

    operations = [
        migrations.AlterField(
            model_name='familyuser',
            name='ahv',
            field=profiles.ahv.AHVField(help_text='New AHV number, e.g. 756.1234.5678.90', max_length=16, verbose_name='AHV number', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='familyuser',
            name='birth_date',
            field=models.DateField(null=True, verbose_name='Birth date', blank=True),
            preserve_default=True,
        ),
    ]
