# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0015_teacher_email'),
    ]

    operations = [
        migrations.AlterField(
            model_name='teacher',
            name='email',
            field=models.EmailField(max_length=255, null=True, verbose_name='Email address', blank=True),
            preserve_default=True,
        ),
    ]
