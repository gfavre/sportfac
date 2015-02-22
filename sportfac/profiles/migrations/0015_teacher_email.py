# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0014_auto_20150220_2146'),
    ]

    operations = [
        migrations.AddField(
            model_name='teacher',
            name='email',
            field=models.EmailField(max_length=255, unique=True, null=True, verbose_name='Email address', blank=True),
            preserve_default=True,
        ),
    ]
