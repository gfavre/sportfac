# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2020-07-13 15:27
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('activities', '0022_instructors_uuid'),
        ('profiles', '0014_switch_pk_to_uuid'),
    ]

    operations = [
        migrations.AlterField(
            model_name='coursesinstructors',
            name='instructor',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterUniqueTogether(
            name='coursesinstructors',
            unique_together=set([('course', 'instructor')]),
        ),
        migrations.AddField(
            model_name='course',
            name='instructors',
            field=models.ManyToManyField(related_name='course', through='activities.CoursesInstructors',
                                         to=settings.AUTH_USER_MODEL, verbose_name='Instructors'),
        ),

    ]