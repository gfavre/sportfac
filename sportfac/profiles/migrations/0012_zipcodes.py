# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0011_country_code'),
    ]

    operations = [
        migrations.AlterField(
            model_name='familyuser',
            name='zipcode',
            field=models.CharField(default='', max_length=5, verbose_name='NPA', blank=True),
            preserve_default=False,
        ),
    ]
