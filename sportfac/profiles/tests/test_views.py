from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.forms.models import model_to_dict
from django.test import RequestFactory, override_settings
from django.utils import timezone
from django.urls import reverse

from faker import Faker

from sportfac.utils import TenantTestCase as TestCase

from ..models import FamilyUser
from ..views import AccountView, RegistrationView, WizardRegistrationView
from .factories import FamilyUserFactory


fake = Faker(locale="fr_CH")

# noinspection PyUnresolvedReferences
class UserDataTestCaseMixin:

    def setUp(self):
        self.factory = RequestFactory()
        sid = transaction.savepoint()
        user = FamilyUserFactory()
        self.user_data = model_to_dict(user, exclude=["id", "groups", "user_permissions"])
        # We can't call delete() because of groups and user_permissions not using uuids.
        transaction.savepoint_rollback(sid)
        self.user_data["email2"] = self.user_data["email"]
        self.user_data["private_phone"] = "0791234567"
        self.user_data["password1"] = "badbadzoot"
        self.user_data["password2"] = "badbadzoot"
        del self.user_data["external_identifier"]
        del self.user_data["last_login"]
        del self.user_data["birth_date"]
        del self.user_data["permit_type"]

    @patch("profiles.views.login")
    def test_user_is_created(self, _):
        request = self.factory.post(self.url, data=self.user_data)
        request.user = AnonymousUser()
        request.REGISTRATION_OPENED = True
        self.view(request)
        self.assertTrue(FamilyUser.objects.exists())
        self.assertEqual(FamilyUser.objects.count(), 1)
        self.assertEqual(FamilyUser.objects.first().email, self.user_data["email"])

    @patch("profiles.views.login")
    def test_user_is_logged_in(self, faked_login):
        request = self.factory.post(self.url, data=self.user_data)
        request.user = AnonymousUser()
        request.REGISTRATION_OPENED = True
        self.view(request)
        self.assertTrue(faked_login.called)


class WizardRegistrationViewTests(UserDataTestCaseMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.view = WizardRegistrationView.as_view()
        self.url = reverse("wizard_register")

    def test_account_creation_forbidden_if_registration_closed(self):
        request = self.factory.get(self.url)
        request.user = AnonymousUser()
        request.REGISTRATION_OPENED = False
        with self.assertRaises(PermissionDenied):
            self.view(request)


class RegistrationViewTests(UserDataTestCaseMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.view = RegistrationView.as_view()
        self.url = reverse("profiles:anytime_registeraccount")

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
        self.url = reverse("profiles:profiles_account")
        self.view = AccountView.as_view()
        self.request = self.factory.get(self.url)
        self.request.user = self.user

    def test_access_forbidden_if_not_logged_in(self):
        self.request.user = AnonymousUser()
        response = self.view(self.request)
        response.client = self.client
        self.assertRedirects(response, reverse("profiles:auth_login") + "?next=" + self.url)

    def test_get_returns_200(self):
        response = self.view(self.request)
        self.assertEqual(response.status_code, 200)
