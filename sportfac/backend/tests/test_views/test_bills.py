# -*- coding: utf-8 -*-
from django.contrib.auth.models import AnonymousUser
from django.forms.models import model_to_dict
from django.test import RequestFactory
from django.urls import reverse

from activities.tests.factories import ActivityFactory
from mock import patch
from profiles.tests.factories import FamilyUserFactory
from registrations.models import Bill
from registrations.tests.factories import BillFactory, RegistrationFactory

from sportfac.utils import TenantTestCase

from ...views.registration_views import BillDetailView, BillListView, BillUpdateView
from .base import fake_registrations_open_middleware


class BillDetailViewTests(TenantTestCase):
    def setUp(self):
        super(BillDetailViewTests, self).setUp()
        self.bill = BillFactory()
        self.registration = RegistrationFactory(bill=self.bill)
        self.login_url = reverse("profiles:auth_login")
        self.url = self.bill.get_backend_url()
        self.user = FamilyUserFactory(is_manager=True)
        self.view = BillDetailView.as_view()
        self.request = RequestFactory().get(self.url)
        fake_registrations_open_middleware(self.request)
        self.request.user = self.user

    def test_access_forbidden_for_anonymous_users(self):
        self.request.user = AnonymousUser()
        response = self.view(self.request, pk=self.bill.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "?next=" + self.url))

    def test_access_forbidden_for_non_backend_users(self):
        self.request.user = FamilyUserFactory(is_manager=False)
        response = self.view(self.request, pk=self.bill.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "?next=" + self.url))

    def test_get_is_200(self):
        response = self.view(self.request, pk=self.bill.pk)
        self.assertEqual(response.status_code, 200)

    def test_content_is_rendered(self):
        response = self.view(self.request, pk=self.bill.pk)
        # noinspection PyUnresolvedReferences
        content = response.render().content
        self.assertTrue(len(content) > 0)


class BillListViewTests(TenantTestCase):
    def setUp(self):
        super(BillListViewTests, self).setUp()
        self.bill = BillFactory()
        self.registration = RegistrationFactory(bill=self.bill)
        self.login_url = reverse("profiles:auth_login")
        self.url = reverse("backend:bill-list")
        self.user = FamilyUserFactory(is_manager=True)
        self.view = BillListView.as_view()
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


class BillUpdateViewTests(TenantTestCase):
    def setUp(self):
        super(BillUpdateViewTests, self).setUp()
        self.bill = BillFactory(status=Bill.STATUS.paid)
        self.data = model_to_dict(self.bill)
        self.login_url = reverse("profiles:auth_login")
        self.url = self.bill.get_update_url()
        self.user = FamilyUserFactory(is_manager=True)
        self.view = BillUpdateView.as_view()
        self.request = RequestFactory().get(self.url)
        fake_registrations_open_middleware(self.request)
        self.request.user = self.user

    def test_access_forbidden_for_anonymous_users(self):
        self.request.user = AnonymousUser()
        response = self.view(self.request, pk=self.bill.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "?next=" + self.url))

    def test_access_forbidden_for_non_backend_users(self):
        self.request.user = FamilyUserFactory(is_manager=False)
        response = self.view(self.request, pk=self.bill.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "?next=" + self.url))

    def test_get_is_200(self):
        response = self.view(self.request, pk=self.bill.pk)
        self.assertEqual(response.status_code, 200)

    def test_content_is_rendered(self):
        response = self.view(self.request, pk=self.bill.pk)
        # noinspection PyUnresolvedReferences
        content = response.render().content
        self.assertTrue(len(content) > 0)

    @patch("django.contrib.messages.success")
    def test_post_is_302(self, _):
        self.request.method = "POST"
        self.request.POST = self.data
        response = self.view(self.request, pk=self.bill.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("backend:bill-list"))
