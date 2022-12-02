# -*- coding: utf-8 -*-
from __future__ import absolute_import
import mock.mock
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.test import RequestFactory, override_settings
from django.urls import reverse

from mock import patch

from sportfac.utils import TenantTestCase as TestCase
from appointments.tests.factories import AppointmentFactory
from profiles.tests.factories import FamilyUserFactory
from ..models import Bill, Registration
from ..views import (
    WizardChildrenListView, RegisteredActivitiesListView, WizardBillingView,
    ChildrenListView, SummaryView, BillingView, BillDetailView)
from .factories import BillFactory, ChildFactory, RegistrationFactory


class ChildrenListViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = ChildrenListView.as_view()
        self.url = reverse('registrations_children')
        self.user = FamilyUserFactory()
        self.child = ChildFactory(family=self.user)
        self.request = self.factory.get(self.url)
        self.request.user = self.user

    def test_access_forbidden_if_not_logged_in(self):
        self.request.user = AnonymousUser()
        response = self.view(self.request)
        response.client = self.client
        self.assertRedirects(response, reverse('login') + '/?next=' + self.url)

    def test_only_own_children_in_queryset(self):
        ChildFactory.create_batch(5)
        response = self.view(self.request)
        qs = response.context_data['object_list']
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first(), self.child)


class BillingViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = BillingView.as_view()
        self.url = reverse('registrations_billing')
        self.user = FamilyUserFactory()
        self.invoice = BillFactory(family=self.user)
        self.request = self.factory.get(self.url)
        self.request.user = self.user

    def test_access_forbidden_if_not_logged_in(self):
        self.request.user = AnonymousUser()
        response = self.view(self.request)
        response.client = self.client
        self.assertRedirects(response, reverse('login') + '/?next=' + self.url)

    def test_only_own_bills_in_queryset(self):
        BillFactory.create_batch(5)
        response = self.view(self.request)
        qs = response.context_data['object_list']
        self.assertEqual(response.status_code, 200)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first(), self.invoice)


class BillDetailViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = BillDetailView.as_view()
        self.user = FamilyUserFactory()
        self.invoice = BillFactory(family=self.user)
        self.url = self.invoice.get_absolute_url()
        self.request = self.factory.get(self.url)
        self.request.user = self.user

    def test_access_forbidden_if_not_logged_in(self):
        self.request.user = AnonymousUser()
        response = self.view(self.request)
        response.client = self.client
        self.assertRedirects(response, reverse('login') + '/?next=' + self.url)

    def test_user_cannot_access_other_bills(self):
        invoice_2 = BillFactory()
        request = self.factory.get(invoice_2.get_absolute_url())
        request.user = self.user
        with self.assertRaises(Http404):
            self.view(request, pk=invoice_2.pk)

    def test_user_can_access_own_bills(self):
        response = self.view(self.request, pk=self.invoice.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['object'], self.invoice)


class SummaryViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = SummaryView.as_view()
        self.url = reverse('registrations_registered_activities')
        self.user = FamilyUserFactory()
        self.child = ChildFactory(family=self.user)
        self.registration = RegistrationFactory(child=self.child, status='confirmed')
        self.request = self.factory.get(self.url)
        self.request.user = self.user

    def test_access_forbidden_if_not_logged_in(self):
        self.request.user = AnonymousUser()
        response = self.view(self.request)
        response.client = self.client
        self.assertRedirects(response, reverse('login') + '/?next=' + self.url)

    def test_own_registrations_in_context(self):
        RegistrationFactory.create_batch(5, status='confirmed')
        response = self.view(self.request)
        self.assertEqual(response.status_code, 200)
        self.assertIn('registered_list', response.context_data)
        qs = response.context_data['registered_list']
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first(), self.registration)


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


class WizardBillingViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = WizardBillingView.as_view()
        self.url = reverse('wizard_billing')
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
        self.assertRedirects(response, reverse('login') + '/?next=' + self.url)

    def test_redirect_to_appointments_if_appointment_not_taken(self):
        with mock.patch("profiles.models.FamilyUser.montreux_needs_appointment",
                        new_callable=mock.PropertyMock) as mock_needs_appointment:
            mock_needs_appointment.return_value = True
            response = self.view(self.get_request)
            self.assertTrue(mock_needs_appointment.called)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('wizard_confirm'))

    def test_redirect_to_confirm_view_if_no_invoice(self):
        self.invoice.set_paid()
        response = self.view(self.get_request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('wizard_confirm'))

    @override_settings(KEPCHUP_USE_APPOINTMENTS=True)
    def test_appointments_available_if_setting_enabled(self):
        appointment = AppointmentFactory(family=self.user)
        response = self.view(self.get_request)
        self.assertEqual(response.status_code, 200)
        self.assertIn('include_calendar', response.context_data)
        self.assertTrue(response.context_data['include_calendar'])
        self.assertIn('appointments', response.context_data)
        self.assertIn(appointment, response.context_data['appointments'])

    @override_settings(KEPCHUP_PAYMENT_METHOD='datatrans')
    @patch('payments.datatrans.get_transaction')
    def test_datatrans_transaction_available_if_necessary(self, get_transaction_mock):
        response = self.view(self.get_request)
        get_transaction_mock.assert_called_once()
        self.assertIn('transaction', response.context_data)

    def test_bill_status_updated_on_first_get(self):
        self.view(self.get_request)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, Bill.STATUS.waiting)

    @override_settings(KEPCHUP_USE_APPOINTMENTS=True)
    @patch.object(Bill, 'send_confirmation')
    def test_send_confirmation_called_for_wire_transfers(self, send_confirmation_mock):
        with mock.patch("registrations.models.Bill.is_wire_transfer",
                        new_callable=mock.PropertyMock) as mock_is_wire_transfer:
            mock_is_wire_transfer.return_value = True
            self.view(self.get_request)
        send_confirmation_mock.assert_called_once()
