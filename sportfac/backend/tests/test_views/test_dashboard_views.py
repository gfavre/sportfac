# -*- coding: utf-8 -*-
from __future__ import absolute_import

from django.test import RequestFactory, override_settings
from django.urls import reverse

import faker
import pytz
from activities.tests.factories import CourseFactory
from mock import patch
from profiles.tests.factories import FamilyUserFactory

from sportfac.utils import TenantTestCase as TestCase

from ...views.dashboard_views import HomePageView


fake = faker.Faker()


class HomePageViewTests(TestCase):
    def setUp(self):
        super(HomePageViewTests, self).setUp()
        self.manager = FamilyUserFactory(is_manager=True)
        self.url = reverse("backend:home")
        self.view = HomePageView.as_view()
        self.request = RequestFactory().get(self.url)
        self.request.user = self.manager
        self.request.tenant = self.tenant
        self.request.PHASE = 1
        self.request.REGISTRATION_START = fake.future_datetime(tzinfo=pytz.utc)
        self.request.REGISTRATION_END = fake.future_datetime(tzinfo=pytz.utc)
        self.request.REGISTRATION_OPENED = False

    def test_access_forbidden_for_simple_users(self):
        self.request.user = FamilyUserFactory()
        response = self.view(self.request)
        self.assertEqual(response.status_code, 302)

    def test_access_forbidden_for_instructors(self):
        self.request.user = FamilyUserFactory()
        CourseFactory(instructors=[self.request.user])
        response = self.view(self.request)
        self.assertEqual(response.status_code, 302)

    def test_get_phase_1(self):
        response = self.view(self.request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.rendered_content) > 0)

    def test_get_phase_2(self):
        self.request.PHASE = 2
        self.request.REGISTRATION_START = fake.past_datetime(tzinfo=pytz.utc)
        self.request.REGISTRATION_OPENED = True
        response = self.view(self.request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.rendered_content) > 0)

    def test_get_phase_3(self):
        self.request.PHASE = 3
        self.request.REGISTRATION_START = fake.past_datetime(tzinfo=pytz.utc)
        self.request.REGISTRATION_END = fake.past_datetime(tzinfo=pytz.utc)
        self.request.REGISTRATION_OPENED = False
        response = self.view(self.request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.rendered_content) > 0)
