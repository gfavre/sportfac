# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

from backend import RESPONSIBLE_GROUP

def create_responsible_group(apps, schema_editor):
    """Data migration: Create the "sports managers" group, 
       and give this group proper permissions.
    """
    Group = apps.get_app_config('auth').get_model('Group')
    grp, created = Group.objects.get_or_create(name=RESPONSIBLE_GROUP)
    grp.save()




class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_responsible_group),
    
    ]
