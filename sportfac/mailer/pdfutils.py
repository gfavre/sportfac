# -*- coding: utf-8 -*-
from __future__ import absolute_import
import os
import json
import six

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import activate
from django.utils.encoding import smart_text
from django.template import loader

import pypdftk
import requests

from backend.dynamic_preferences_registry import global_preferences_registry
from sportfac.context_processors import kepchup_context


global_preferences = global_preferences_registry.manager()


def get_ssf_decompte_heures(course, instructor):
    pdf_file = os.path.join(settings.STATIC_ROOT, 'pdf', "SSF_decompte_moniteur.pdf")

    fields = {
        u'Établissement': global_preferences['email__SCHOOL_NAME'].decode('utf-8'),
        u'Discipline': course.activity.name,
        u"Groupe délèves no": course.number,
        u"du": course.start_date.strftime('%d/%m/%Y'),
        u"au": course.end_date.strftime('%d/%m/%Y'),
        u'nom': instructor.last_name,
        u'prénom': instructor.first_name,
        u'Adresse': instructor.address,
        u'NPALocalité': '%s %s' % (instructor.zipcode, instructor.city),
        u'Date de naissance': instructor.birth_date and instructor.birth_date.strftime('%d/%m/%Y') or '',
        u'Télnatel': instructor.best_phone.as_national,
        u'IBAN complet': instructor.iban,
        u'No AVS': instructor.ahv,
    }
    # noinspection PyBroadException
    try:
        return pypdftk.fill_form(pdf_path=pdf_file, datas=fields, flatten=False)
    except:  # noqa
        return pdf_file

"""
from mailer.pdfutils import get_ssf_decompte_heures
from activities.models import  Course
course= Course.objects.filter(instructors__isnull=False).first()
instructor=course.instructors.first()
pdf = get_ssf_decompte_heures(course, instructor)
import shutil
shutil.move(pdf, '/Users/grfavre/Desktop/filled.pdf')
"""


class FakeRequest(object):
    pass


class PDFRenderer(object):
    message_template = None
    is_landscape = False

    def __init__(self, context_data, request=None):
        site = Site.objects.all()[0]
        self.fake_request = request is None
        if not request:
            request = FakeRequest()
        request.site = site
        self.request = request
        context_data['request'] = request
        context_data.update(kepchup_context(request))
        self.context = context_data

    @staticmethod
    def resolve_template(template):
        """Accepts a template object, path-to-template or list of paths"""
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

    def get_content(self, template_name):
        initial_static_url = settings.STATIC_URL
        if settings.STATIC_URL.startswith('/'):
            settings.STATIC_URL = u'{}{}{}'.format('https://',#self.context.get('PROTOCOL'),
                                                   self.request.site.domain,
                                                   settings.STATIC_URL)
        if self.fake_request:
            activate(settings.LANGUAGE_CODE)
            template = self.resolve_template(template_name)
            content = smart_text(template.render(self.context))
        else:
            content = loader.render_to_string(template_name=self.message_template,
                                              context=self.context,
                                              request=self.request)
        settings.STATIC_URL = initial_static_url
        return content

    def render_to_pdf(self, output):
        """output: filelike object"""
        content = self.get_content(self.get_message_template())
        payload = json.dumps({
            'content': content,
            'renderType': 'pdf',
            'omitBackground': True,
            "renderSettings": {
                'emulateMedia': 'print',
                'pdfOptions': {
                    'format': 'A4',
                    'landscape': self.is_landscape,
                    'preferCSSPageSize': True,
                }
            }
        })

        pdf = requests.post(
            'https://PhantomJsCloud.com/api/browser/v2/{}/'.format(
                settings.PHANTOMJSCLOUD_APIKEY
            ),
            payload
        )
        f = open(output, 'wb')
        f.write(pdf.content)


class CourseParticipants(PDFRenderer):
    message_template = 'mailer/pdf_participants_list.html'
    is_landscape = True


class CourseParticipantsPresence(PDFRenderer):
    message_template = 'mailer/pdf_participants_presence.html'

    def __init__(self, context_data):
        super(CourseParticipantsPresence, self).__init__(context_data)
        course = context_data['course']
        self.context['sessions'] = range(0, course.number_of_sessions)


class MyCourses(PDFRenderer):
    message_template = 'mailer/pdf_my_courses.html'
    is_landscape = True
