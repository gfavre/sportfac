# -*- coding: utf-8 -*-
from __future__ import absolute_import

from django.contrib.auth.models import AnonymousUser
from django.forms.models import model_to_dict
from django.test import RequestFactory, override_settings
from django.urls import reverse

from absences.models import Session
from absences.tests.factories import AbsenceFactory
from activities.models import Activity, Course
from activities.tests.factories import CourseFactory
from backend.utils import AbsencePDFRenderer, AbsencesPDFRenderer
from mock import patch
from profiles.tests.factories import FamilyUserFactory
from registrations.tests.factories import RegistrationFactory

from sportfac.utils import TenantTestCase

from ...views.course_views import (CourseAbsenceView, CourseCreateView, CourseDeleteView,
                                   CourseDetailView, CourseListView, CoursesAbsenceView,
                                   CourseUpdateView)
from .base import fake_registrations_open_middleware


class CourseAbsenceViewTests(TenantTestCase):
    def setUp(self):
        super(CourseAbsenceViewTests, self).setUp()
        self.course = CourseFactory()
        self.absence = AbsenceFactory(session__course=self.course)
        self.login_url = reverse("login")
        self.url = self.course.backend_absences_url
        self.user = FamilyUserFactory(is_manager=True)
        self.view = CourseAbsenceView.as_view()
        self.request = RequestFactory().get(self.url)
        fake_registrations_open_middleware(self.request)
        self.request.user = self.user

    def test_access_forbidden_for_anonymous_users(self):
        self.request.user = AnonymousUser()
        response = self.view(self.request, course=self.course.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "/?next=" + self.url))

    def test_access_forbidden_for_non_backend_users(self):
        self.request.user = FamilyUserFactory(is_manager=False)
        response = self.view(self.request, course=self.course.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "/?next=" + self.url))

    def test_get_is_200(self):
        response = self.view(self.request, course=self.course.pk)
        self.assertEqual(response.status_code, 200)

    @override_settings(
        KEPCHUP_BIB_NUMBERS=True,
        KEPCHUP_REGISTRATION_LEVELS=True,
        KEPCHUP_DISPLAY_CAR_NUMBER=True,
        KEPCHUP_DISPLAY_REGISTRATION_NOTE=True,
    )
    def test_content_is_rendered(self):
        response = self.view(self.request, course=self.course.pk)
        # noinspection PyUnresolvedReferences
        content = response.render().content
        self.assertTrue(len(content) > 0)

    def test_get_pdf(self):
        request = RequestFactory().get(self.url + "?pdf=1")
        request.user = self.user
        fake_registrations_open_middleware(request)
        with patch.object(AbsencePDFRenderer, "render_to_pdf") as mock_render:

            def fill_file(filepath):
                f = open(filepath, "wb")
                f.write(b"PDF")

            mock_render.side_effect = fill_file
            response = self.view(request, course=self.course.pk)
            mock_render.assert_called_once()
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])

    @patch("django.contrib.messages.success")
    def test_post_create_session(self, _):
        data = {
            "date": "01.01.2020",
        }
        request = RequestFactory().post(self.url, data=data)
        request.user = self.user
        fake_registrations_open_middleware(request)
        response = self.view(request, course=self.course.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url)
        self.assertEqual(Session.objects.count(), 2)


class CoursesAbsenceViewTests(TenantTestCase):
    def setUp(self):
        super(CoursesAbsenceViewTests, self).setUp()
        self.course1 = CourseFactory()
        self.registration1 = RegistrationFactory(course=self.course1)
        self.absence1 = AbsenceFactory(session__course=self.course1)
        self.course2 = CourseFactory()
        self.registration2 = RegistrationFactory(course=self.course2)
        self.absence2 = AbsenceFactory(session__course=self.course2)
        self.login_url = reverse("login")
        self.url = reverse("backend:courses-absence") + "?c={}&c={}".format(
            self.course1.pk, self.course2.pk
        )
        self.user = FamilyUserFactory(is_manager=True)
        self.view = CoursesAbsenceView.as_view()
        self.request = RequestFactory().get(self.url)
        fake_registrations_open_middleware(self.request)
        self.request.user = self.user

    def test_access_forbidden_for_anonymous_users(self):
        self.request.user = AnonymousUser()
        response = self.view(self.request)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(self.login_url))

    def test_access_forbidden_for_non_backend_users(self):
        self.request.user = FamilyUserFactory(is_manager=False)
        response = self.view(self.request)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(self.login_url))

    def test_get_is_200(self):
        response = self.view(self.request)
        self.assertEqual(response.status_code, 200)

    @override_settings(
        KEPCHUP_BIB_NUMBERS=True,
        KEPCHUP_REGISTRATION_LEVELS=True,
        KEPCHUP_DISPLAY_CAR_NUMBER=True,
        KEPCHUP_DISPLAY_REGISTRATION_NOTE=True,
    )
    def test_content_is_rendered(self):
        response = self.view(self.request)
        # noinspection PyUnresolvedReferences
        content = response.render().content
        self.assertTrue(len(content) > 0)

    def test_get_pdf(self):
        request = RequestFactory().get(self.url + "&pdf=1")
        request.user = self.user
        fake_registrations_open_middleware(request)
        with patch.object(AbsencesPDFRenderer, "render_to_pdf") as mock_render:

            def fill_file(filepath):
                f = open(filepath, "wb")
                f.write(b"PDF")

            mock_render.side_effect = fill_file
            response = self.view(request)
            mock_render.assert_called_once()
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])

    @patch("django.contrib.messages.success")
    def test_post_create_session(self, _):
        data = {
            "date": "01.01.2020",
        }
        request = RequestFactory().post(self.url, data=data)
        request.user = self.user
        fake_registrations_open_middleware(request)
        response = self.view(request)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith, reverse("backend:courses-absence"))
        self.assertEqual(Session.objects.count(), 4)


class CourseCreateViewTests(TenantTestCase):
    def setUp(self):
        super(CourseCreateViewTests, self).setUp()
        self.login_url = reverse("login")
        self.url = reverse("backend:course-create")
        self.user = FamilyUserFactory(is_manager=True)
        self.view = CourseCreateView.as_view()
        self.request = RequestFactory().get(self.url)
        fake_registrations_open_middleware(self.request)
        self.request.user = self.user

    def test_access_forbidden_for_anonymous_users(self):
        self.request.user = AnonymousUser()
        response = self.view(self.request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "/?next=" + self.url))

    def test_access_forbidden_for_non_backend_users(self):
        self.request.user = FamilyUserFactory(is_manager=False)
        response = self.view(self.request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "/?next=" + self.url))

    def test_get_is_200(self):
        response = self.view(self.request)
        self.assertEqual(response.status_code, 200)

    @override_settings(KEPCHUP_EXPLICIT_SESSION_DATES=False)
    def test_content_is_rendered(self):
        response = self.view(self.request)
        # noinspection PyUnresolvedReferences
        content = response.render().content
        self.assertTrue(len(content) > 0)

    @override_settings(KEPCHUP_EXPLICIT_SESSION_DATES=True)
    def test_content_is_rendered_explicit_dates(self):
        response = self.view(self.request)
        # noinspection PyUnresolvedReferences
        content = response.render().content
        self.assertTrue(len(content) > 0)

    @patch("django.contrib.messages.success")
    def test_post_creates_course(self, _):
        course = CourseFactory()
        course_data = model_to_dict(course)
        course_data["instructors"] = [str(self.user.pk)]
        course.delete()
        del course_data["id"]
        self.request.method = "POST"
        self.request.POST = course_data
        response = self.view(self.request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("backend:course-list"))
        self.assertEqual(Activity.objects.count(), 1)


class CourseDeleteViewTests(TenantTestCase):
    def setUp(self):
        self.course = CourseFactory()
        self.data = {"confirm": "True"}
        self.login_url = reverse("login")
        self.url = self.course.get_delete_url()
        self.user = FamilyUserFactory(is_manager=True)
        self.view = CourseDeleteView.as_view()
        self.request = RequestFactory().get(self.url)
        self.request.user = self.user
        fake_registrations_open_middleware(self.request)

    def test_access_forbidden_for_anonymous_users(self):
        self.request.user = AnonymousUser()
        response = self.view(self.request, course=self.course.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "/?next=" + self.url))

    def test_access_forbidden_for_non_backend_users(self):
        self.request.user = FamilyUserFactory(is_manager=False)
        response = self.view(self.request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "/?next=" + self.url))

    def test_get_is_200(self):
        response = self.view(self.request, course=self.course.pk)
        self.assertEqual(response.status_code, 200)

    def test_content_is_rendered(self):
        response = self.view(self.request, course=self.course.pk)
        # noinspection PyUnresolvedReferences
        content = response.render().content
        self.assertTrue(len(content) > 0)

    @patch("django.contrib.messages.success")
    def test_post_is_302(self, _):
        self.request.method = "POST"
        self.request.POST = self.data
        response = self.view(self.request, course=self.course.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("backend:course-list"))
        self.assertEqual(Course.objects.count(), 0)


class CourseDetailViewTests(TenantTestCase):
    def setUp(self):
        super(CourseDetailViewTests, self).setUp()
        self.user = FamilyUserFactory(is_manager=True)
        self.course = CourseFactory(instructors=[self.user])
        self.registrations = RegistrationFactory.create_batch(3, course=self.course)
        self.login_url = reverse("login")
        self.url = self.course.get_backend_url()
        self.view = CourseDetailView.as_view()
        self.request = RequestFactory().get(self.url)
        fake_registrations_open_middleware(self.request)
        self.request.user = self.user

    def test_access_forbidden_for_anonymous_users(self):
        self.request.user = AnonymousUser()
        response = self.view(self.request, course=self.course.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "/?next=" + self.url))

    def test_access_forbidden_for_non_backend_users(self):
        self.request.user = FamilyUserFactory(is_manager=False)
        response = self.view(self.request, course=self.course.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "/?next=" + self.url))

    def test_get_is_200(self):
        response = self.view(self.request, course=self.course.pk)
        self.assertEqual(response.status_code, 200)

    @override_settings(
        KEPCHUP_BIB_NUMBERS=True,
        KEPCHUP_REGISTRATION_LEVELS=True,
        KEPCHUP_DISPLAY_CAR_NUMBER=True,
        KEPCHUP_DISPLAY_REGISTRATION_NOTE=True,
        KEPCHUP_EMERGENCY_NUMBER_MANDATORY=True,
        KEPCHUP_LIMIT_BY_SCHOOL_YEAR=True,
        KEPCHUP_USES_ABSENCES=True,
    )
    def test_content_is_rendered(self):
        response = self.view(self.request, course=self.course.pk)
        # noinspection PyUnresolvedReferences
        content = response.render().content
        self.assertTrue(len(content) > 0)


class CourseListViewTests(TenantTestCase):
    def setUp(self):
        super(CourseListViewTests, self).setUp()
        self.course = CourseFactory()
        self.login_url = reverse("login")
        self.url = reverse("backend:activity-list")
        self.user = FamilyUserFactory(is_manager=True)
        self.view = CourseListView.as_view()
        self.request = RequestFactory().get(self.url)
        fake_registrations_open_middleware(self.request)
        self.request.user = self.user

    def test_access_forbidden_for_anonymous_users(self):
        self.request.user = AnonymousUser()
        response = self.view(self.request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "/?next=" + self.url))

    def test_access_forbidden_for_non_backend_users(self):
        self.request.user = FamilyUserFactory(is_manager=False)
        response = self.view(self.request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "/?next=" + self.url))

    def test_get_is_200(self):
        response = self.view(self.request)
        self.assertEqual(response.status_code, 200)

    def test_content_is_rendered(self):
        response = self.view(self.request)
        # noinspection PyUnresolvedReferences
        content = response.render().content
        self.assertTrue(len(content) > 0)

    def test_content_is_rendered_phase_1(self):
        self.request.PHASE = 1
        response = self.view(self.request)
        # noinspection PyUnresolvedReferences
        content = response.render().content
        self.assertTrue(len(content) > 0)


class CourseUpdateViewTests(TenantTestCase):
    def setUp(self):
        super(CourseUpdateViewTests, self).setUp()
        self.course = CourseFactory()
        self.login_url = reverse("login")
        self.url = self.course.get_update_url()
        self.user = FamilyUserFactory(is_manager=True)
        self.view = CourseUpdateView.as_view()
        self.request = RequestFactory().get(self.url)
        fake_registrations_open_middleware(self.request)
        self.request.user = self.user
        self.data = model_to_dict(self.course)
        self.data["instructors"] = [str(self.user.pk)]

    def test_access_forbidden_for_anonymous_users(self):
        self.request.user = AnonymousUser()
        response = self.view(self.request, course=self.course.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "/?next=" + self.url))

    def test_access_forbidden_for_non_backend_users(self):
        self.request.user = FamilyUserFactory(is_manager=False)
        response = self.view(self.request, course=self.course.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "/?next=" + self.url))

    def test_get_is_200(self):
        response = self.view(self.request, course=self.course.pk)
        self.assertEqual(response.status_code, 200)

    def test_content_is_rendered(self):
        response = self.view(self.request, course=self.course.pk)
        # noinspection PyUnresolvedReferences
        content = response.render().content
        self.assertTrue(len(content) > 0)

    @patch("django.contrib.messages.success")
    def test_post_is_302(self, _):
        self.request.method = "POST"
        self.request.POST = self.data
        response = self.view(self.request, course=self.course.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("backend:course-list"))
