# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

from backend import RESPONSIBLE_GROUP
from django.contrib.auth.models import Group
from activities.models import Course

def copy_responsibles(apps, schema_editor):
    """Data migration: Create the "sports managers" group, 
       and give this group proper permissions.
    """
    grp = Group.objects.get(name=RESPONSIBLE_GROUP)
    for course in Course.objects.all():
        grp.user_set.add(course.responsible)




class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0006_auto_20150205_1710'),
        ('backend', '0002_responsible_group'),
        ('activities', '0002_auto_20150123_1438'),
    ]

    operations = [
        migrations.RunPython(copy_responsibles),
    ]
