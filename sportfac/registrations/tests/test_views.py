# -*- coding: utf-8 -*-
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory
from django.urls import reverse

from sportfac.utils import TenantTestCase as TestCase
from profiles.tests.factories import FamilyUserFactory
from ..views import WizardChildrenListView


class WizardChildrenListViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = WizardChildrenListView.as_view()
        self.url = reverse('wizard_children')
        self.user = FamilyUserFactory()

    def test_access_forbidden_if_registration_closed(self):
        request = self.factory.get(self.url)
        request.user = self.user
        request.REGISTRATION_OPENED = False
        with self.assertRaises(PermissionDenied):
            self.view(request)

    def test_access_forbidden_if_not_logged_in(self):
        request = self.factory.get(self.url)
        request.user = AnonymousUser()
        request.REGISTRATION_OPENED = True
        response = self.view(request)
        response.client = self.client
        self.assertRedirects(response, reverse('login') + '/?next=' + self.url)
