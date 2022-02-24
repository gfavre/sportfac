# -*- coding: utf-8 -*-
from django.contrib.auth.models import AnonymousUser
from django.forms.models import model_to_dict
from django.test import RequestFactory
from django.urls import reverse
from django.utils.timezone import now

from mock import patch

from activities.models import Activity
from activities.tests.factories import CourseFactory, ActivityFactory
from profiles.tests.factories import FamilyUserFactory

from ...views.activity_views import ActivityCreateView
from .base import BackendTestBase


class CourseViewsTests(BackendTestBase):

    def test_list(self):
        url = reverse('backend:course-list')
        self.generic_test_rights(url)

    def test_create(self):
        url = reverse('backend:course-create')
        self.generic_test_rights(url)


class ActivityCreateViewTests(BackendTestBase):
    def setUp(self):
        super(ActivityCreateViewTests, self).setUp()
        self.login_url = reverse('login')
        self.url = reverse('backend:activity-create')
        self.user = FamilyUserFactory(is_manager=True)
        self.view = ActivityCreateView.as_view()
        self.request = RequestFactory().get(self.url)
        self.request.REGISTRATION_START = now()
        self.request.REGISTRATION_END = now()
        self.request.REGISTRATION_OPENED = True
        self.request.PHASE = 3
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

    @patch('django.contrib.messages.success')
    def test_post_creates_activity(self, _):
        activity = ActivityFactory()
        activity_data = model_to_dict(activity)
        activity.delete()
        del activity_data['id']
        self.request.method = "POST"
        self.request.POST = activity_data
        response = self.view(self.request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('backend:activity-list'))
        self.assertEqual(Activity.objects.count(), 1)


class ActivitiesViewsTests(BackendTestBase):

    def test_list(self):
        url = reverse('backend:activity-list')
        self.generic_test_rights(url)

    def test_create(self):
        url = reverse('backend:activity-create')
        self.generic_test_rights(url)

