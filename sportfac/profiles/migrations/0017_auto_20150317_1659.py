# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import localflavor.generic.models
import profiles.ahv


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0016_auto_20150224_1045'),
    ]

    operations = [
        migrations.AddField(
            model_name='familyuser',
            name='ahv',
            field=profiles.ahv.AHVField(max_length=13, verbose_name='AHV number', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='familyuser',
            name='birth_date',
            field=models.DateField(null=True, verbose_name='Birth date'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='familyuser',
            name='iban',
            field=localflavor.generic.models.IBANField(max_length=34, blank=True),
            preserve_default=True,
        ),
    ]
