# -*- coding: utf-8 -*-
from __future__ import absolute_import

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, override_settings
from django.urls import reverse

import mock
from profiles.tests.factories import FamilyUserFactory
from registrations.tests.factories import BillFactory, RegistrationFactory

from sportfac.utils import TenantTestCase as TestCase

from ..views.register import WizardSlotsView


class WizardSlotsViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = WizardSlotsView.as_view()
        self.url = reverse("wizard_billing")
        self.user = FamilyUserFactory()
        self.registration = RegistrationFactory()
        self.child = self.registration.child
        self.user = self.child.family
        self.invoice = BillFactory(family=self.user)
        self.get_request = self.factory.get(self.url)
        self.get_request.user = self.user
        self.get_request.REGISTRATION_OPENED = True

    def test_access_forbidden_if_registration_closed(self):
        self.get_request.REGISTRATION_OPENED = False
        with self.assertRaises(PermissionDenied):
            self.view(self.get_request)

    def test_access_forbidden_if_not_logged_in(self):
        self.get_request.user = AnonymousUser()
        response = self.view(self.get_request)
        response.client = self.client
        self.assertRedirects(response, reverse("profiles:auth_login") + "?next=" + self.url)

    def test_redirect_to_billing_if_user_does_not_require_appointment(self):
        with mock.patch(
            "profiles.models.FamilyUser.montreux_needs_appointment", new_callable=mock.PropertyMock
        ) as mock_needs_appointment:
            mock_needs_appointment.return_value = False
            response = self.view(self.get_request)
            self.assertTrue(mock_needs_appointment.called)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("wizard_billing"))

    def test_redirect_to_confirm_view_if_no_invoice(self):
        self.invoice.set_paid()
        response = self.view(self.get_request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("wizard_confirm"))
