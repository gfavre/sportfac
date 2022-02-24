# -*- coding: utf-8 -*-
from datetime import timedelta

from django.test.client import RequestFactory
from django.utils.timezone import now

import faker

from profiles.tests.factories import DEFAULT_PASS, FamilyUserFactory
from sportfac.utils import TenantTestCase


fake = faker.Factory.create()


def fake_registrations_open_middleware(request):
    request.REGISTRATION_START = now() - timedelta(days=1)
    request.REGISTRATION_END = now() + timedelta(days=1)
    request.REGISTRATION_OPENED = True
    request.PHASE = 3


class BackendTestBase(TenantTestCase):
    def setUp(self):
        super(BackendTestBase, self).setUp()
        self.factory = RequestFactory()
        self.user = FamilyUserFactory()
        self.manager = FamilyUserFactory()
        self.manager.is_manager = True
        self.manager.save()

    def generic_test_rights(self, url):
        # anonymous access
        response = self.tenant_client.get(url)
        self.assertEqual(response.status_code, 302)

        # basic user access
        self.tenant_client.login(username=self.user.email, password=DEFAULT_PASS)
        response = self.tenant_client.get(url)
        self.assertEqual(response.status_code, 302)

        # manager access
        self.tenant_client.login(username=self.manager.email, password=DEFAULT_PASS)
        response = self.tenant_client.get(url)
        self.assertEqual(response.status_code, 200)
