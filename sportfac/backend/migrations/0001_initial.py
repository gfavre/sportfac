# -*- coding: utf-8 -*-
""" Data migration: Create the "sports managers" group, 
                    and give this group proper permissions.
"""
from __future__ import unicode_literals

from backend import GROUP_NAME

from django.db import models, migrations


def create_managers_group(apps, schema_editor):
    """Data migration: Create the "sports managers" group, 
       and give this group proper permissions.
    """
    ContentType = apps.get_app_config('contenttypes').get_model('ContentType')
    Group = apps.get_app_config('auth').get_model('Group')
    Permission = apps.get_app_config('auth').get_model('Permission')
    
    activities_models = list(apps.get_app_config('activities').get_models())
    profiles_models = [apps.get_app_config('profiles').get_model(model) for model in
                       ('FamilyUser', 'Child', 'Registration', 'ExtraInfo', 'Teacher')]
    all_models = activities_models + profiles_models
    
    grp, created = Group.objects.get_or_create(name=GROUP_NAME)
    for model in all_models:
        content_type, created = ContentType.objects.get_or_create(
                        app_label=model._meta.concrete_model._meta.app_label,
                        model=model._meta.concrete_model._meta.model_name
                       )
        permissions = Permission.objects.filter(content_type=content_type)
        for permission in permissions:
            grp.permissions.add(permission)
    grp.save()


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0001_initial'), # for Group and Permission models
        ('contenttypes', '0001_initial'), # for ContentType model
        ('activities', '0001_initial'), # all models: permissions to add/edit/...
        ('profiles', '0001_initial'), # some models: permissions to add/edit/...
    ]

    operations = [
        migrations.RunPython(create_managers_group)
    ]
