# -*- coding: utf-8 -*-
from __future__ import absolute_import
from datetime import date
from django.test import RequestFactory, override_settings
from django.urls import reverse

from sportfac.utils import TenantTestCase as TestCase

from mock import patch

from activities.tests.factories import CourseFactory
from backend.utils import AbsencePDFRenderer
from profiles.tests.factories import FamilyUserFactory
from registrations.tests.factories import RegistrationFactory
from ..models import Session
from ..views import AbsenceCourseView
from .factories import AbsenceFactory, SessionFactory


class AbsenceCourseViewTest(TestCase):
    def setUp(self):
        super(AbsenceCourseViewTest, self).setUp()
        self.instructor = FamilyUserFactory()
        self.course = CourseFactory(instructors=(self.instructor,))
        self.url = reverse('activities:course-absence', kwargs={'course': self.course.pk})
        self.view = AbsenceCourseView.as_view()
        self.request = RequestFactory().get(self.url)
        self.request.user = self.instructor

    def test_access_forbidden_for_non_instructors(self):
        self.request.user = FamilyUserFactory()
        response = self.view(self.request, course=self.course.pk)
        self.assertEqual(response.status_code, 302)

    def test_access_forbidden_for_non_instructors_of_this_course(self):
        other_instructor = FamilyUserFactory()
        CourseFactory(instructors=[other_instructor])
        self.request.user = other_instructor
        response = self.view(self.request, course=self.course.pk)
        self.assertEqual(response.status_code, 302)

    def test_get(self):
        response = self.view(self.request, course=self.course.pk)
        self.assertEqual(response.status_code, 200)

    def test_get_pdf(self):
        request = RequestFactory().get(self.url + '?pdf=1')
        request.user = self.instructor
        with patch.object(AbsencePDFRenderer, 'render_to_pdf') as mock_render:
            def fill_file(filepath):
                f = open(filepath, 'wb')
                f.write(b'PDF')
            mock_render.side_effect = fill_file
            response = self.view(request, course=self.course.pk)
            mock_render.assert_called_once()
        self.assertEqual(response.status_code, 200)
        self.assertIn('attachment', response['Content-Disposition'])

    def test_post_creates_session(self):
        data = {
            'date': '2018-01-01',
        }
        request = RequestFactory().post(self.url, data=data)
        request.user = self.instructor
        response = self.view(request, course=self.course.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Session.objects.count(), 1)

    @override_settings(KEPCHUP_EXPLICIT_SESSION_DATES=True)
    def test_post_updates_course_dates(self):
        data = {
            'date': '2031-01-01',
        }
        request = RequestFactory().post(self.url, data=data)
        request.user = self.instructor
        self.view(request, course=self.course.pk)
        self.course.refresh_from_db()
        self.assertEqual(self.course.end_date, date(2031, 1, 1))

    @override_settings(
        KEPCHUP_BIB_NUMBERS=True,
        KEPCHUP_REGISTRATION_LEVELS=True,
        KEPCHUP_DISPLAY_CAR_NUMBER=True,
        KEPCHUP_DISPLAY_REGISTRATION_NOTE=True,
    )
    def test_template(self):
        registrations = RegistrationFactory.create_batch(5, course=self.course)
        sessions = SessionFactory.create_batch(3, course=self.course)
        for reg in registrations:
            for session in sessions:
                AbsenceFactory(session=session, child=reg.child)
        self.client.force_login(user=self.instructor)
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, 'absences/absences.html')
