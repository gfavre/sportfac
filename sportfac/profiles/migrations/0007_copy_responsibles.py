# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

from backend import RESPONSIBLE_GROUP


def copy_responsibles(apps, schema_editor):
    """Data migration: Create the "sports managers" group, 
       and give this group proper permissions.
    """
    Group = apps.get_app_config('auth').get_model('Group')
    grp = Group.objects.get(name=RESPONSIBLE_GROUP)
    Responsible = apps.get_app_config('activities').get_model('Responsible')
    FamilyUser = apps.get_app_config('profiles').get_model('FamilyUser')

    for resp in Responsible.objects.all():
        f, created = FamilyUser.objects.get_or_create(
                        email=resp.email,
                        first_name = resp.first,
                        last_name = resp.last,
                        private_phone2 = resp.phone)
        f.is_responsible = True

class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0006_auto_20150205_1710'),
        ('backend', '0002_responsible_group'),
        ('activities', '0002_auto_20150123_1438'),
    ]

    operations = [
        migrations.RunPython(copy_responsibles),
    ]
