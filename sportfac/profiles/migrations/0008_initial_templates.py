# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models, migrations
from django.template import loader
from django.contrib.sites.models import Site

from dbtemplates.models import Template

TEMPLATES = ('profiles/billing_partial.html', )

def load_templates(apps, schema_editor):
    current_site = Site.objects.get(pk=settings.SITE_ID)
    for template_name in TEMPLATES:
        template = loader.get_template(template_name)
        template_file = template.origin.name
        template_obj, created = Template.objects.get_or_create(
                                    name=template_name,
                                    content=open(template_file).read(),
                                )
        template_obj.sites.add(current_site)
        template_obj.save()


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0007_copy_responsibles'),
    ]

    operations = [
         migrations.RunPython(load_templates)

    ]
