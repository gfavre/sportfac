# -*- coding: utf-8 -*-
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory
from django.urls import reverse

from mock import patch

from sportfac.utils import TenantTestCase as TestCase
from profiles.tests.factories import FamilyUserFactory
from ..models import Bill, Registration
from ..views import WizardChildrenListView, RegisteredActivitiesListView
from .factories import ChildFactory, RegistrationFactory


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


class RegisteredActivitiesListViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = RegisteredActivitiesListView.as_view()
        self.url = reverse('wizard_confirm')
        self.user = FamilyUserFactory()
        self.data = {'accept': True}

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

    def test_redirects_to_wizard_activities_if_no_registrations(self):
        request = self.factory.get(self.url)
        request.user = self.user
        request.REGISTRATION_OPENED = True
        ChildFactory(family=self.user)
        response = self.view(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('wizard_activities'))

    def test_get_returns_200(self):
        request = self.factory.get(self.url)
        request.user = self.user
        request.REGISTRATION_OPENED = True
        RegistrationFactory(child__family=self.user)
        response = self.view(request)
        self.assertEqual(response.status_code, 200)

    def test_post_redirects_to_billing(self):
        request = self.factory.post(self.url, self.data)
        request.user = self.user
        request.REGISTRATION_OPENED = True
        RegistrationFactory(child__family=self.user,  course__price=100)
        response = self.view(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('wizard_billing'))

    def test_post_create_invoice(self):
        request = self.factory.post(self.url, self.data)
        request.user = self.user
        request.REGISTRATION_OPENED = True
        registration = RegistrationFactory(child__family=self.user, course__price=100)
        self.view(request)
        self.assertTrue(Bill.objects.exists())
        self.assertEquals(Bill.objects.first().status, Bill.STATUS.just_created)

    def test_post_sets_registration_status_to_validated(self):
        data = {'accept': True}
        request = self.factory.post(self.url, data)
        request.user = self.user
        request.REGISTRATION_OPENED = True
        registration = RegistrationFactory(child__family=self.user)
        self.view(request)
        registration.refresh_from_db()
        self.assertEquals(registration.status, Registration.STATUS.valid)

    @patch('django.contrib.messages.success')
    def test_post_sets_bill_paid(self, messages_mock):
        data = {'accept': True}
        request = self.factory.post(self.url, data)
        request.user = self.user
        request.REGISTRATION_OPENED = True
        registration = RegistrationFactory(child__family=self.user, course__price=0)
        self.view(request)
        registration.refresh_from_db()
        self.assertEquals(Bill.objects.first().status, Bill.STATUS.paid)
