# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

from registrations.models import Registration as RegistrationModel

def fix_status(apps, schema_editor):
    Registration = apps.get_model('profiles', 'Registration')
    for registration in Registration.objects.all():
        if registration.validated == True:
            registration.status = RegistrationModel.STATUS.valid
            registration.save()


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0002_registration_status'),
    ]

    operations = [
        migrations.RunPython(fix_status)
    ]
