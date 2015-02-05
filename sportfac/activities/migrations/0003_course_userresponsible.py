# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


def update_userresponsible(apps, schema_editor):
    """Data migration: Create the "sports managers" group, 
       and give this group proper permissions.
    """
    FamilyUser = apps.get_app_config('profiles').get_model('FamilyUser')
    Course = apps.get_app_config('activities').get_model('Course')
    for course in Course.objects.all():
        email = course.responsible.email
        course.userresponsible = FamilyUser.objects.get(email=email)
        course.save()


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('activities', '0002_auto_20150123_1438'),
        ('backend', '0002_responsible_group'),
        ('profiles', '0007_copy_responsibles')
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='userresponsible',
            field=models.ForeignKey(related_name='courses', verbose_name='Responsable', to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.RunPython(update_userresponsible),
      
    ]
