# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

from backend import INSTRUCTORS_GROUP, MANAGERS_GROUP


def create_responsible_group(apps, schema_editor):
    """Data migration: Create the "sports managers" group, 
       and give this group proper permissions.
    """
    Group = apps.get_app_config('auth').get_model('Group')
    grp, created = Group.objects.get_or_create(name=INSTRUCTORS_GROUP)
    grp.save()
    grp, created = Group.objects.get_or_create(name=MANAGERS_GROUP)
    grp.save()


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0002_auto_20160506_1200'),
    ]

    operations = [
        migrations.RunPython(create_responsible_group),
    
    ]
