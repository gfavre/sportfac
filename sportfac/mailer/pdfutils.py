# -*- coding: utf-8 -*-
from __future__ import absolute_import
import os
import re
import subprocess
import six
from tempfile import NamedTemporaryFile

from django.conf import settings
from django.contrib.sites.models import Site
from django.utils.translation import activate
from django.utils.encoding import smart_text
from django.template import loader, Context, RequestContext

import pypdftk

from backend.dynamic_preferences_registry import global_preferences_registry


global_preferences = global_preferences_registry.manager()



def get_ssf_decompte_heures(course, instructor):
    pdf_file = os.path.join(settings.STATIC_ROOT, 'pdf',
                            "E_SSF_decompte_heures_moniteur.pdf")

    fields = {
        u'Etablissement': global_preferences['email__SCHOOL_NAME'].decode('utf-8'),
        u'Discipline': course.activity.name,
        u"Groupe d'éléve": course.number,
        u"Période du": course.start_date.strftime('%d/%m/%Y'),
        u"période au": course.end_date.strftime('%d/%m/%Y'),
        u'Nom': instructor.last_name,
        u'Prénom': instructor.first_name,
        u'Adresse': instructor.address,
        u'localité': '%s %s' % (instructor.zipcode,
                                instructor.city),
        u'date de naissance': instructor.birth_date and instructor.birth_date.strftime('%d/%m/%Y') or '',
        u'iban': instructor.iban,
        u'No avs': instructor.ahv,
    }
    try:
        return pypdftk.fill_form(pdf_path=pdf_file, datas=fields)
    except:
        return pdf_file


class PDFRenderer(object):
    message_template = None

    def __init__(self, context_data):
        site = Site.objects.all()[0]
        request = {'site': site}
        context_data['request'] = request
        self.context = context_data

    def resolve_template(self, template):
        "Accepts a template object, path-to-template or list of paths"
        if isinstance(template, (list, tuple)):
            return loader.select_template(template)
        elif isinstance(template, six.string_types):
            return loader.get_template(template)
        else:
            return template

    def get_message_template(self):
        if self.message_template is None:
            raise ImproperlyConfigured(
                "PDFRenderer requires either a definition of "
                "'message_template' or an implementation of 'get_message_template'")
        else:
            return self.resolve_template(self.message_template)

    def render_to_temporary_file(self, template_name, mode='w+b', bufsize=-1,
                                 suffix='.html', prefix='tmp', dir=None,
                                 delete=True):
        activate(settings.LANGUAGE_CODE)
        template = self.resolve_template(template_name)
        content = smart_text(template.render(self.context))
        try:
            # Python3 has 'buffering' arg instead of 'bufsize'
            tempfile = NamedTemporaryFile(mode=mode, buffering=bufsize,
                                          suffix=suffix, prefix=prefix,
                                          dir=dir, delete=delete)
        except TypeError:
            tempfile = NamedTemporaryFile(mode=mode, bufsize=bufsize,
                                          suffix=suffix, prefix=prefix,
                                          dir=dir, delete=delete)
        try:
            tempfile.write(content.encode('utf-8'))
            tempfile.flush()
            return tempfile
        except:
            # Clean-up tempfile if an Exception is raised.
            tempfile.close()
            raise

    def render_to_pdf(self, output):
        "output: filelike object"
        filelike = self.render_to_temporary_file(self.get_message_template())

        try:
            phandle = subprocess.Popen([
                settings.PHANTOMJS,
                os.path.join(os.path.dirname(settings.SITE_ROOT), 'bin', 'rasterize.js'),
                filelike.name.encode(), output,
                'A4'
            ], close_fds=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            phandle.communicate()

        finally:
            filelike.close()


class CourseParticipants(PDFRenderer):
    message_template = 'mailer/pdf_participants_list.html'


class CourseParticipantsPresence(PDFRenderer):
    message_template = 'mailer/pdf_participants_presence.html'

    def __init__(self, context_data):
        course = context_data['course']
        context_data['sessions'] = range(0, course.number_of_sessions)
        self.context = context_data


class MyCourses(PDFRenderer):
    message_template = 'mailer/pdf_my_courses.html'
