# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('activities', '0011_auto_20150723_1138'),
    ]

    operations = [
        migrations.AlterField(
            model_name='course',
            name='price',
            field=models.DecimalField(null=True, verbose_name='Price', max_digits=5, decimal_places=2, blank=True),
            preserve_default=True,
        ),
    ]
