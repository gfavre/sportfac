# -*- coding: utf-8 -*-
from django.contrib.auth.models import AnonymousUser
from django.forms.models import model_to_dict
from django.test import RequestFactory, override_settings
from django.urls import reverse

from absences.models import Session
from absences.tests.factories import AbsenceFactory
from activities.models import Activity
from activities.tests.factories import ActivityFactory, CourseFactory
from backend.utils import AbsencePDFRenderer
from mock import patch
from profiles.tests.factories import FamilyUserFactory

from sportfac.utils import TenantTestCase

from ...views.activity_views import (
    ActivityAbsenceView,
    ActivityCreateView,
    ActivityDeleteView,
    ActivityDetailView,
    ActivityListView,
    ActivityUpdateView,
)
from .base import fake_registrations_open_middleware


class ActivityAbsenceViewTests(TenantTestCase):
    def setUp(self):
        super(ActivityAbsenceViewTests, self).setUp()
        self.activity = ActivityFactory()
        self.course = CourseFactory(activity=self.activity)
        self.absence = AbsenceFactory(session__course=self.course, session__activity=self.activity)
        self.login_url = reverse("profiles:auth_login")
        self.url = self.activity.backend_absences_url
        self.user = FamilyUserFactory(is_manager=True)
        self.view = ActivityAbsenceView.as_view()
        self.request = RequestFactory().get(self.url)
        fake_registrations_open_middleware(self.request)
        self.request.user = self.user

    def test_access_forbidden_for_anonymous_users(self):
        self.request.user = AnonymousUser()
        response = self.view(self.request, pk=self.activity.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "?next=" + self.url))

    def test_access_forbidden_for_non_backend_users(self):
        self.request.user = FamilyUserFactory(is_manager=False)
        response = self.view(self.request, pk=self.activity.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "?next=" + self.url))

    def test_get_is_200(self):
        response = self.view(self.request, pk=self.activity.pk)
        self.assertEqual(response.status_code, 200)

    def test_c_param(self):
        request = RequestFactory().get(self.url + "?c={}&c=9999".format(self.course.pk))
        request.user = self.user
        response = self.view(request, pk=self.activity.pk)
        self.assertEqual(response.status_code, 200)

    @override_settings(
        KEPCHUP_BIB_NUMBERS=True,
        KEPCHUP_REGISTRATION_LEVELS=True,
        KEPCHUP_DISPLAY_CAR_NUMBER=True,
        KEPCHUP_DISPLAY_REGISTRATION_NOTE=True,
    )
    def test_content_is_rendered(self):
        response = self.view(self.request, pk=self.activity.pk)
        # noinspection PyUnresolvedReferences
        content = response.render().content
        self.assertTrue(len(content) > 0)

    def test_get_pdf(self):
        request = RequestFactory().get(self.url + "?pdf=1")
        request.user = self.user
        with patch.object(AbsencePDFRenderer, "render_to_pdf") as mock_render:

            def fill_file(filepath):
                f = open(filepath, "wb")
                f.write(b"PDF")

            mock_render.side_effect = fill_file
            response = self.view(request, pk=self.activity.pk)
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
        response = self.view(request, pk=self.activity.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url)
        self.assertEqual(Session.objects.count(), 2)


class ActivityCreateViewTests(TenantTestCase):
    def setUp(self):
        super(ActivityCreateViewTests, self).setUp()
        self.login_url = reverse("profiles:auth_login")
        self.url = reverse("backend:activity-create")
        self.user = FamilyUserFactory(is_manager=True)
        self.view = ActivityCreateView.as_view()
        self.request = RequestFactory().get(self.url)
        fake_registrations_open_middleware(self.request)
        self.request.user = self.user

    def test_access_forbidden_for_anonymous_users(self):
        self.request.user = AnonymousUser()
        response = self.view(self.request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "?next=" + self.url))

    def test_access_forbidden_for_non_backend_users(self):
        self.request.user = FamilyUserFactory(is_manager=False)
        response = self.view(self.request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "?next=" + self.url))

    def test_get_is_200(self):
        response = self.view(self.request)
        self.assertEqual(response.status_code, 200)

    def test_content_is_rendered(self):
        response = self.view(self.request)
        # noinspection PyUnresolvedReferences
        content = response.render().content
        self.assertTrue(len(content) > 0)

    @patch("django.contrib.messages.success")
    def test_post_creates_activity(self, _):
        activity = ActivityFactory()
        activity_data = model_to_dict(activity)
        activity.delete()
        del activity_data["id"]
        self.request.method = "POST"
        self.request.POST = activity_data
        response = self.view(self.request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("backend:activity-list"))
        self.assertEqual(Activity.objects.count(), 1)


class ActivityDeleteViewTests(TenantTestCase):
    def setUp(self):
        self.activity = ActivityFactory()
        self.data = {"confirm": "True"}
        self.login_url = reverse("profiles:auth_login")
        self.url = self.activity.get_delete_url()
        self.user = FamilyUserFactory(is_manager=True)
        self.view = ActivityDeleteView.as_view()
        self.request = RequestFactory().get(self.url)
        self.request.user = self.user
        fake_registrations_open_middleware(self.request)

    def test_access_forbidden_for_anonymous_users(self):
        self.request.user = AnonymousUser()
        response = self.view(self.request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "?next=" + self.url))

    def test_access_forbidden_for_non_backend_users(self):
        self.request.user = FamilyUserFactory(is_manager=False)
        response = self.view(self.request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "?next=" + self.url))

    def test_get_is_200(self):
        response = self.view(self.request, pk=self.activity.pk)
        self.assertEqual(response.status_code, 200)

    def test_content_is_rendered(self):
        response = self.view(self.request, pk=self.activity.pk)
        # noinspection PyUnresolvedReferences
        content = response.render().content
        self.assertTrue(len(content) > 0)

    @patch("django.contrib.messages.success")
    def test_post_is_302(self, _):
        self.request.method = "POST"
        self.request.POST = self.data
        response = self.view(self.request, pk=self.activity.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("backend:activity-list"))
        self.assertEqual(Activity.objects.count(), 0)


class ActivityDetailViewTests(TenantTestCase):
    def setUp(self):
        super(ActivityDetailViewTests, self).setUp()
        self.activity = ActivityFactory()
        self.course = CourseFactory(activity=self.activity)
        self.login_url = reverse("profiles:auth_login")
        self.url = self.activity.get_backend_url()
        self.user = FamilyUserFactory(is_manager=True)
        self.view = ActivityDetailView.as_view()
        self.request = RequestFactory().get(self.url)
        fake_registrations_open_middleware(self.request)
        self.request.user = self.user

    def test_access_forbidden_for_anonymous_users(self):
        self.request.user = AnonymousUser()
        response = self.view(self.request, pk=self.activity.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "?next=" + self.url))

    def test_access_forbidden_for_non_backend_users(self):
        self.request.user = FamilyUserFactory(is_manager=False)
        response = self.view(self.request, pk=self.activity.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "?next=" + self.url))

    def test_get_is_200(self):
        response = self.view(self.request, pk=self.activity.pk)
        self.assertEqual(response.status_code, 200)

    def test_content_is_rendered(self):
        response = self.view(self.request, pk=self.activity.pk)
        # noinspection PyUnresolvedReferences
        content = response.render().content
        self.assertTrue(len(content) > 0)


class ActivityListViewTests(TenantTestCase):
    def setUp(self):
        super(ActivityListViewTests, self).setUp()
        self.activity = ActivityFactory()
        self.login_url = reverse("profiles:auth_login")
        self.url = reverse("backend:activity-list")
        self.user = FamilyUserFactory(is_manager=True)
        self.view = ActivityListView.as_view()
        self.request = RequestFactory().get(self.url)
        fake_registrations_open_middleware(self.request)
        self.request.user = self.user

    def test_access_forbidden_for_anonymous_users(self):
        self.request.user = AnonymousUser()
        response = self.view(self.request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "?next=" + self.url))

    def test_access_forbidden_for_non_backend_users(self):
        self.request.user = FamilyUserFactory(is_manager=False)
        response = self.view(self.request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "?next=" + self.url))

    def test_get_is_200(self):
        response = self.view(self.request)
        self.assertEqual(response.status_code, 200)

    def test_content_is_rendered(self):
        response = self.view(self.request)
        # noinspection PyUnresolvedReferences
        content = response.render().content
        self.assertTrue(len(content) > 0)


class ActivityUpdateViewTests(TenantTestCase):
    def setUp(self):
        super(ActivityUpdateViewTests, self).setUp()
        self.activity = ActivityFactory()
        self.data = model_to_dict(self.activity)
        self.login_url = reverse("profiles:auth_login")
        self.url = self.activity.get_update_url()
        self.user = FamilyUserFactory(is_manager=True)
        self.view = ActivityUpdateView.as_view()
        self.request = RequestFactory().get(self.url)
        fake_registrations_open_middleware(self.request)
        self.request.user = self.user

    def test_access_forbidden_for_anonymous_users(self):
        self.request.user = AnonymousUser()
        response = self.view(self.request, pk=self.activity.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "?next=" + self.url))

    def test_access_forbidden_for_non_backend_users(self):
        self.request.user = FamilyUserFactory(is_manager=False)
        response = self.view(self.request, pk=self.activity.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "?next=" + self.url))

    def test_get_is_200(self):
        response = self.view(self.request, pk=self.activity.pk)
        self.assertEqual(response.status_code, 200)

    def test_content_is_rendered(self):
        response = self.view(self.request, pk=self.activity.pk)
        # noinspection PyUnresolvedReferences
        content = response.render().content
        self.assertTrue(len(content) > 0)

    @patch("django.contrib.messages.success")
    def test_post_is_302(self, _):
        self.request.method = "POST"
        self.request.POST = self.data
        response = self.view(self.request, pk=self.activity.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("backend:activity-list"))
