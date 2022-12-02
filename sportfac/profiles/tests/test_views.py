# -*- coding: utf-8 -*-
from __future__ import absolute_import
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.forms.models import model_to_dict
from django.test import override_settings
from django.test import RequestFactory
from django.urls import reverse

from mock import patch

from sportfac.utils import TenantTestCase as TestCase
from ..models import FamilyUser
from ..views import WizardRegistrationView, RegistrationView, AccountView
from .factories import FamilyUserFactory


class UserDataTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        user = FamilyUserFactory()
        self.user_data = model_to_dict(user)
        user.delete()
        self.user_data['email2'] = self.user_data['email']
        self.user_data['private_phone'] = '0791234567'
        self.user_data['password1'] = 'badbadzoot'
        self.user_data['password2'] = 'badbadzoot'


# noinspection PyUnresolvedReferences,PyAttributeOutsideInit
class BaseRegistrationTestMixin:
    view = None
    url = None

    @patch('profiles.views.login')
    def test_user_is_created(self, _):
        request = self.factory.post(self.url, data=self.user_data)
        request.user = AnonymousUser()
        request.REGISTRATION_OPENED = True
        self.view(request)
        self.assertTrue(FamilyUser.objects.exists())
        self.assertEqual(FamilyUser.objects.count(), 1)
        self.assertEqual(FamilyUser.objects.first().email, self.user_data['email'])

    @patch('profiles.views.login')
    def test_user_is_logged_in(self, faked_login):
        request = self.factory.post(self.url, data=self.user_data)
        request.user = AnonymousUser()
        request.REGISTRATION_OPENED = True
        self.view(request)
        self.assertTrue(faked_login.called)


class WizardRegistrationViewTests(BaseRegistrationTestMixin, UserDataTestCase):
    def setUp(self):
        super(WizardRegistrationViewTests, self).setUp()
        self.view = WizardRegistrationView.as_view()
        self.url = reverse('wizard_register')

    def test_account_creation_forbidden_if_registration_closed(self):
        request = self.factory.get(self.url)
        request.user = AnonymousUser()
        request.REGISTRATION_OPENED = False
        with self.assertRaises(PermissionDenied):
            self.view(request)


class RegistrationViewTests(BaseRegistrationTestMixin, UserDataTestCase):
    def setUp(self):
        super(RegistrationViewTests, self).setUp()
        self.factory = RequestFactory()
        self.view = RegistrationView.as_view()
        self.url = reverse('anytime_registeraccount')

    def test_account_creation_forbidden_if_registration_closed(self):
        request = self.factory.get(self.url)
        request.user = AnonymousUser()
        request.REGISTRATION_OPENED = False
        with self.assertRaises(PermissionDenied):
            self.view(request)

    @override_settings(KEPCHUP_REGISTER_ACCOUNTS_AT_ANY_TIME=True)
    def test_account_creation_authorized_if_KEPCHUP_REGISTER_ACCOUNTS_AT_ANY_TIME(self):
        request = self.factory.get(self.url)
        request.user = AnonymousUser()
        request.REGISTRATION_OPENED = False
        response = self.view(request)
        self.assertEqual(response.status_code, 200)


class AccountViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = FamilyUserFactory()
        self.url = reverse('profiles_account')
        self.view = AccountView.as_view()
        self.request = self.factory.get(self.url)
        self.request.user = self.user

    def test_access_forbidden_if_not_logged_in(self):
        self.request.user = AnonymousUser()
        response = self.view(self.request)
        response.client = self.client
        self.assertRedirects(response, reverse('login') + '/?next=' + self.url)

    def test_get_returns_200(self):
        response = self.view(self.request)
        self.assertEqual(response.status_code, 200)
