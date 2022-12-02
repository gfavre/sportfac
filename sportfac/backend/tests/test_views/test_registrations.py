# -*- coding: utf-8 -*-
from __future__ import absolute_import
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.forms.models import model_to_dict, BaseModelFormSet
from django.forms.formsets import ManagementForm, BaseFormSet
from django.test import RequestFactory, override_settings
from django.urls import reverse

from mock import patch

from activities.tests.factories import CourseFactory
from profiles.tests.factories import FamilyUserFactory
from registrations.models import Registration
from registrations.tests.factories import RegistrationFactory
from sportfac.utils import TenantTestCase, add_middleware_to_request

from ...views.registration_views import (
    RegistrationCreateView, RegistrationDeleteView, RegistrationDetailView,
    RegistrationListView, RegistrationUpdateView,
    RegistrationsMoveView, RegistrationValidateView
)
from .base import fake_registrations_open_middleware


class RegistrationCreateViewTests(TenantTestCase):
    def setUp(self):
        super(RegistrationCreateViewTests, self).setUp()
        self.login_url = reverse('login')
        self.url = reverse('backend:registration-create')
        self.user = FamilyUserFactory(is_manager=True)
        self.view = RegistrationCreateView.as_view()
        self.request = RequestFactory().get(self.url)
        fake_registrations_open_middleware(self.request)
        self.request.user = self.user
        self.request = add_middleware_to_request(self.request, SessionMiddleware)

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


class RegistrationDeleteViewTests(TenantTestCase):
    def setUp(self):
        self.registration = RegistrationFactory()
        self.data = {"confirm": "True"}
        self.login_url = reverse("login")
        self.url = self.registration.get_delete_url()
        self.user = FamilyUserFactory(is_manager=True)
        self.view = RegistrationDeleteView.as_view()
        self.request = RequestFactory().get(self.url)
        self.request.user = self.user
        fake_registrations_open_middleware(self.request)

    def test_access_forbidden_for_anonymous_users(self):
        self.request.user = AnonymousUser()
        response = self.view(self.request, pk=self.registration.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "/?next=" + self.url))

    def test_access_forbidden_for_non_backend_users(self):
        self.request.user = FamilyUserFactory(is_manager=False)
        response = self.view(self.request, pk=self.registration.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "/?next=" + self.url))

    def test_get_is_200(self):
        response = self.view(self.request, pk=self.registration.pk)
        self.assertEqual(response.status_code, 200)

    def test_content_is_rendered(self):
        response = self.view(self.request, pk=self.registration.pk)
        # noinspection PyUnresolvedReferences
        content = response.render().content
        self.assertTrue(len(content) > 0)

    @patch('django.contrib.messages.success')
    def test_post_is_302_and_registration_is_canceled(self, _):
        course = self.registration.course
        self.request.method = "POST"
        self.request.POST = self.data
        response = self.view(self.request, pk=self.registration.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, course.get_backend_url())
        self.assertEqual(Registration.objects.all_with_deleted().count(), 1)
        registration = Registration.objects.all_with_deleted().first()
        self.assertEqual(registration.status, Registration.STATUS.canceled)


class RegistrationDetailViewTests(TenantTestCase):
    def setUp(self):
        super(RegistrationDetailViewTests, self).setUp()
        self.user = FamilyUserFactory(is_manager=True)
        self.registration = RegistrationFactory()
        self.login_url = reverse('login')
        self.url = self.registration.get_backend_url()
        self.view = RegistrationDetailView.as_view()
        self.request = RequestFactory().get(self.url)
        fake_registrations_open_middleware(self.request)
        self.request.user = self.user

    def test_access_forbidden_for_anonymous_users(self):
        self.request.user = AnonymousUser()
        response = self.view(self.request, pk=self.registration.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "/?next=" + self.url))

    def test_access_forbidden_for_non_backend_users(self):
        self.request.user = FamilyUserFactory(is_manager=False)
        response = self.view(self.request, pk=self.registration.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "/?next=" + self.url))

    def test_get_is_200(self):
        response = self.view(self.request, pk=self.registration.pk)
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
        response = self.view(self.request, pk=self.registration.pk)
        # noinspection PyUnresolvedReferences
        content = response.render().content
        self.assertTrue(len(content) > 0)


class RegistrationListViewTests(TenantTestCase):
    def setUp(self):
        super(RegistrationListViewTests, self).setUp()
        self.registration = RegistrationFactory()
        self.login_url = reverse('login')
        self.url = reverse('backend:registration-list')
        self.user = FamilyUserFactory(is_manager=True)
        self.view = RegistrationListView.as_view()
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


class RegistrationUpdateViewTests(TenantTestCase):
    def setUp(self):
        super(RegistrationUpdateViewTests, self).setUp()
        self.registration = RegistrationFactory()
        self.login_url = reverse('login')
        self.url = self.registration.get_update_url()
        self.user = FamilyUserFactory(is_manager=True)
        self.view = RegistrationUpdateView.as_view()
        self.request = RequestFactory().get(self.url)
        fake_registrations_open_middleware(self.request)
        self.request.user = self.user
        self.data = model_to_dict(self.registration)
        self.data['extra_infos-TOTAL_FORMS'] = 0
        self.data['extra_infos-INITIAL_FORMS'] = 0
        self.data['extra_infos-MIN_NUM_FORMS'] = 0
        self.data['extra_infos-MAX_NUM_FORMS'] = 1000

    def test_access_forbidden_for_anonymous_users(self):
        self.request.user = AnonymousUser()
        response = self.view(self.request, pk=self.registration.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "/?next=" + self.url))

    def test_access_forbidden_for_non_backend_users(self):
        self.request.user = FamilyUserFactory(is_manager=False)
        response = self.view(self.request, pk=self.registration.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "/?next=" + self.url))

    def test_get_is_200(self):
        response = self.view(self.request, pk=self.registration.pk)
        self.assertEqual(response.status_code, 200)

    def test_content_is_rendered(self):
        response = self.view(self.request, pk=self.registration.pk)
        # noinspection PyUnresolvedReferences
        content = response.render().content
        self.assertTrue(len(content) > 0)

    @patch('django.contrib.messages.success')
    @patch.object(BaseFormSet, 'is_valid', return_value=True)
    @patch.object(BaseModelFormSet, 'save')
    def test_post_is_302(self, _, __, ___):
        self.request.method = "POST"
        self.request.POST = self.data
        response = self.view(self.request, pk=self.registration.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('backend:registration-list'))


class RegistrationMoveViewTests(TenantTestCase):
    def setUp(self):
        super(RegistrationMoveViewTests, self).setUp()
        self.user = FamilyUserFactory(is_manager=True)
        self.registration = RegistrationFactory()
        self.login_url = reverse('login')
        self.url = reverse('backend:registrations-move')
        self.view = RegistrationsMoveView.as_view()
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

    def test_initial_course(self):
        self.url = reverse('backend:registrations-move') + '?course={}'.format(self.registration.course.pk)
        self.request = RequestFactory().get(self.url)
        fake_registrations_open_middleware(self.request)
        self.request.user = self.user
        response = self.view(self.request)
        context = response.context_data
        self.assertEqual(context['form'].initial, {'origin_course_id': self.registration.course.pk})

    def test_initial_activity(self):
        self.url = reverse('backend:registrations-move') + '?activity={}'.format(self.registration.course.activity.pk)
        self.request = RequestFactory().get(self.url)
        fake_registrations_open_middleware(self.request)
        self.request.user = self.user
        response = self.view(self.request)
        context = response.context_data
        self.assertEqual(context['form'].initial, {'origin_activity_id': self.registration.course.activity.pk})