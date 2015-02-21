# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models, migrations
from django.template import loader
from django.contrib.sites.models import Site

from dbtemplates.models import Template


TEMPLATES = ('mailer/need_confirmation.txt', 'mailer/need_confirmation_subject.txt',
             'mailer/notpaid.txt', 'mailer/notpaid_subject.txt',
             'mailer/responsible.txt', 'mailer/responsible_subject.txt',
             'mailer/course_begin.txt', 'mailer/course_begin_subject.txt')

def load_templates(apps, schema_editor):
    try:
        current_site = Site.objects.get(pk=settings.SITE_ID)
    except Site.DoesNotExist:
        current_site = Site(pk=settings.SITE_ID,
                            domain='example.com',
                            name='example.com')
        current_site.save()
    settings.TEMPLATE_DEBUG = True
    for template_name in TEMPLATES:
        template = loader.get_template(template_name)
        template_file = template.origin.name
        try:
            template_obj, created = Template.objects.get_or_create(
                                        name=template_name,
                                        content=open(template_file).read(),
                                    )
            template_obj.sites.add(current_site)
            template_obj.save()

        except IOError:
            pass
        
class Migration(migrations.Migration):

    dependencies = [
        ('mailer', '0003_auto_20150205_1949'),
    ]

    operations = [
        migrations.RunPython(load_templates)
    ]
