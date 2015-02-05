# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('activities', '0004_course_responsible'),
    ]

    operations = [
        #migrations.DeleteModel(
        #    name='Responsible',
        #),
        migrations.AlterField(
            model_name='course',
            name='responsible',
            field=models.ForeignKey(related_name='courses', verbose_name='Responsable', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
    ]
