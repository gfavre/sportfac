# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('activities', '0003_course_userresponsible'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='course',
            name='responsible',
        ),
        migrations.RenameField(
            model_name='course',
            old_name = 'userresponsible',
            new_name='responsible',
        ),

    ]
