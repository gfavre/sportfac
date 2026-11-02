from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.db import transaction
from django.forms.models import model_to_dict
from django.test import RequestFactory
from django.test import override_settings
from django.urls import reverse
from faker import Faker

from activities.tests.factories import CourseFactory
from sportfac.utils import TenantTestCase as TestCase

from ..models import FamilyUser
from ..views import AccountView
from ..views import RegistrationView
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


class RegistrationViewTests(UserDataTestCaseMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.view = RegistrationView.as_view()
        self.url = reverse("profiles:anytime_registeraccount")

    @override_settings(KEPCHUP_REGISTER_ACCOUNTS_AT_ANY_TIME=False)
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


class RegistrationRaceConditionTests(UserDataTestCaseMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.view = RegistrationView.as_view()
        self.url = reverse("profiles:anytime_registeraccount")

    @override_settings(KEPCHUP_REGISTER_ACCOUNTS_AT_ANY_TIME=True)
    @patch("profiles.views.FamilyUser.objects.create_user")
    def test_integrity_error_from_a_racing_duplicate_email_is_a_form_error_not_a_500(self, mock_create_user):
        # Regression test (La Tour-de-Peilz, 2026-09): RegistrationForm.clean_email checks
        # uniqueness (email__iexact) before this runs, but nothing stops two
        # near-simultaneous submissions for the same not-yet-existing email (a double
        # form submit, browser back + resubmit, two tabs...) from both passing that check
        # before either commits - the unique constraint on FamilyUser.email is what
        # actually catches the second one. Left uncaught, that crashed
        # wizard/steps/user-create/ with a 500 instead of the normal "email already in
        # use" form error.
        mock_create_user.side_effect = IntegrityError("duplicate key value violates unique constraint")
        request = self.factory.post(self.url, data=self.user_data)
        request.user = AnonymousUser()
        request.REGISTRATION_OPENED = True

        response = self.view(request)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(FamilyUser.objects.exists())


class LoginCaseInsensitivityTests(TestCase):
    # Regression test for the actual bug report: an account created (or ever saved) with
    # a mixed-case email must still be able to log in with a different-case version of it
    # - e.g. after a password reset, whose own lookup (Django's PasswordResetForm.get_users)
    # already matches case-insensitively, unlike ModelBackend's login lookup before this fix.
    def test_login_with_different_case_email_succeeds(self):
        password = "badbadzoot"  # noqa: S105
        user = FamilyUserFactory(email="Some.User@Example.com")
        user.set_password(password)
        user.save()

        response = self.tenant_client.post(
            reverse("profiles:auth_login"),
            data={"username": "some.user@example.com", "password": password},
        )

        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.wsgi_request.user.pk, user.pk)


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

    def test_get_for_instructors(self):
        course = CourseFactory()
        course.instructors.add(self.user)
        response = self.view(self.request)
        self.assertEqual(response.status_code, 200)

    def account_data(self, email):
        data = model_to_dict(self.user, exclude=["groups", "user_permissions"])
        data = {key: value for key, value in data.items() if value is not None}
        data.update(email=email, private_phone="0791234567", password1="", password2="")
        return data

    def test_case_variant_duplicate_email_is_a_form_error(self):
        other = FamilyUserFactory(email="existing-account@example.com")
        original_email = self.user.email
        self.client.force_login(self.user)
        response = self.client.post(self.url, self.account_data("  EXISTING-ACCOUNT@example.com  "))
        self.assertEqual(response.status_code, 200)
        self.assertIn("email", response.context["form"].errors)
        self.user.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(self.user.email, original_email)
        self.assertEqual(other.email, "existing-account@example.com")

    def test_own_email_can_be_saved_with_different_case(self):
        original_email = self.user.email
        self.client.force_login(self.user)
        response = self.client.post(self.url, self.account_data(original_email.upper()))
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, original_email)

    def test_legacy_case_variant_duplicate_is_a_form_error(self):
        other = FamilyUserFactory(email="legacy-account@example.com")
        FamilyUser.objects.filter(pk=self.user.pk).update(email="Legacy-Account@example.com")
        self.user.refresh_from_db()
        self.addCleanup(
            lambda: FamilyUser.objects.filter(pk=self.user.pk).update(email=f"cleanup-{self.user.pk}@example.com")
        )
        self.client.force_login(self.user)
        response = self.client.post(self.url, self.account_data(self.user.email))
        self.assertEqual(response.status_code, 200)
        self.assertIn("email", response.context["form"].errors)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "Legacy-Account@example.com")
        self.assertTrue(FamilyUser.objects.filter(pk=other.pk).exists())

    def test_racing_email_collision_is_a_form_error_and_rolls_back(self):
        from profiles.forms import UserForm

        other = FamilyUserFactory(email="before-race@example.com")
        original_email = self.user.email
        original_save = UserForm.save

        def racing_save(form, *args, **kwargs):
            FamilyUser.objects.filter(pk=other.pk).update(email=form.cleaned_data["email"])
            return original_save(form, *args, **kwargs)

        self.client.force_login(self.user)
        with patch.object(UserForm, "save", autospec=True, side_effect=racing_save):
            response = self.client.post(self.url, self.account_data("race-target@example.com"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("email", response.context["form"].errors)
        self.assertFalse(any(message.level_tag == "success" for message in response.context["messages"]))
        self.user.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(self.user.email, original_email)
        self.assertEqual(other.email, "before-race@example.com")

    def test_unrelated_integrity_error_is_not_hidden(self):
        self.client.force_login(self.user)
        with patch("profiles.forms.UserForm.save", side_effect=IntegrityError("unrelated constraint")):
            with self.assertRaises(IntegrityError):
                self.client.post(self.url, self.account_data("valid-new@example.com"))

    def test_parent_and_instructor_forms_reject_case_variant_email(self):
        from profiles.forms import InstructorForm
        from profiles.forms import ParentProfileForm
        from profiles.forms import UserForm

        FamilyUserFactory(email="reserved-form@example.com")
        for form_class in (UserForm, ParentProfileForm, InstructorForm):
            with self.subTest(form=form_class.__name__):
                form = form_class(data=self.account_data("RESERVED-FORM@example.com"), instance=self.user)
                self.assertFalse(form.is_valid())
                self.assertIn("email", form.errors)

    def test_new_email_is_normalized_and_saved(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, self.account_data("  New.Account@example.com  "))
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "new.account@example.com")
