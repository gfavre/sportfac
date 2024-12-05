from django.contrib.auth.models import AnonymousUser
from django.http import Http404
from django.test import RequestFactory
from django.urls import reverse

from profiles.tests.factories import FamilyUserFactory
from sportfac.utils import TenantTestCase as TestCase
from ..views.user import BillDetailView, BillingView, ChildrenListView, SummaryView
from .factories import BillFactory, ChildFactory, RegistrationFactory


class ChildrenListViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = ChildrenListView.as_view()
        self.url = reverse("registrations:registrations_children")
        self.user = FamilyUserFactory()
        self.child = ChildFactory(family=self.user)
        self.request = self.factory.get(self.url)
        self.request.user = self.user

    def test_access_forbidden_if_not_logged_in(self):
        self.request.user = AnonymousUser()
        response = self.view(self.request)
        response.client = self.client
        self.assertRedirects(response, reverse("profiles:auth_login") + "?next=" + self.url)

    def test_only_own_children_in_queryset(self):
        ChildFactory.create_batch(5)
        response = self.view(self.request)
        qs = response.context_data["object_list"]
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first(), self.child)


class BillingViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = BillingView.as_view()
        self.url = reverse("registrations:registrations_billing")
        self.user = FamilyUserFactory()
        self.invoice = BillFactory(family=self.user)
        self.request = self.factory.get(self.url)
        self.request.user = self.user

    def test_access_forbidden_if_not_logged_in(self):
        self.request.user = AnonymousUser()
        response = self.view(self.request)
        response.client = self.client
        self.assertRedirects(response, reverse("profiles:auth_login") + "?next=" + self.url)

    def test_only_own_bills_in_queryset(self):
        BillFactory.create_batch(5)
        response = self.view(self.request)
        qs = response.context_data["object_list"]
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
        self.assertRedirects(response, reverse("profiles:auth_login") + "?next=" + self.url)

    def test_user_cannot_access_other_bills(self):
        invoice_2 = BillFactory()
        request = self.factory.get(invoice_2.get_absolute_url())
        request.user = self.user
        with self.assertRaises(Http404):
            self.view(request, pk=invoice_2.pk)

    def test_user_can_access_own_bills(self):
        response = self.view(self.request, pk=self.invoice.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data["object"], self.invoice)


class SummaryViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = SummaryView.as_view()
        self.url = reverse("registrations:registrations_registered_activities")
        self.user = FamilyUserFactory()
        self.child = ChildFactory(family=self.user)
        self.registration = RegistrationFactory(child=self.child, status="confirmed")
        self.request = self.factory.get(self.url)
        self.request.user = self.user

    def test_access_forbidden_if_not_logged_in(self):
        self.request.user = AnonymousUser()
        response = self.view(self.request)
        response.client = self.client
        self.assertRedirects(response, reverse("profiles:auth_login") + "?next=" + self.url)

    def test_own_registrations_in_context(self):
        RegistrationFactory.create_batch(5, status="confirmed")
        response = self.view(self.request)
        self.assertEqual(response.status_code, 200)
        self.assertIn("registered_list", response.context_data)
        qs = response.context_data["registered_list"]
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first(), self.registration)
