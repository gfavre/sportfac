# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

def country_to_code(apps, schema_editor):
    FamilyUser = apps.get_model('profiles', 'FamilyUser')
    for user in FamilyUser.objects.all():
        user.country = 'CH'
        user.save()

class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0010_add_nationality_and_language_fields'),
    ]

    operations = [
        migrations.RunPython(country_to_code),
        migrations.AlterField(
            model_name='familyuser',
            name='country',
            field=models.CharField(default=b'CH', max_length=2, verbose_name='Country', choices=[(b'CH', 'Switzerland'), (b'FL', 'Liechtenstein'), (b'D', 'Germany'), (b'F', 'France'), (b'I', 'Italy'), (b'A', 'Austria')]),
            preserve_default=True,
        ),
    ]
