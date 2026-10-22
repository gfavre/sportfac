from datetime import timedelta

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from activities.tests.factories import CourseFactory
from api.tests.utils import UserMixin
from profiles.forms import InstructorForm
from profiles.forms import ParentProfileForm
from profiles.tests.factories import FamilyUserFactory
from profiles.utils import invalidate_user_cache
from registrations.tests.factories import ChildFactory
from sportfac.utils import TenantTestCase

from .factories import WizardStepFactory


class ParentProfileStepTests(UserMixin, TenantTestCase):
    def setUp(self):
        super().setUp()
        now = timezone.now()
        self.tenant.preferences["phase__START_REGISTRATION"] = now - timedelta(days=1)
        self.tenant.preferences["phase__END_REGISTRATION"] = now + timedelta(days=1)
        WizardStepFactory(slug="user-update", position=0, lead="", description="Veuillez vérifier vos informations")
        WizardStepFactory(slug="children", position=1)
        self.user = FamilyUserFactory(bank_name="Banque moniteur", is_mep=True)
        CourseFactory(instructors=[self.user])
        invalidate_user_cache(self.user.pk, "is_instructor")
        self.url = reverse("wizard:step", kwargs={"step_slug": "user-update"})
        self.data = {
            "email": self.user.email,
            "first_name": "Camille",
            "last_name": "Parent",
            "address": "Rue du Lac 3",
            "zipcode": "1800",
            "city": "Vevey",
            "country": "CH",
            "private_phone": "+41791234567",
        }

    def test_anonymous_get_and_post_require_login(self):
        for method in (self.tenant_client.get, self.tenant_client.post):
            response = method(self.url)
            self.assertEqual(response.status_code, 302)
            self.assertIn("next=", response.url)

    def test_parents_and_instructors_receive_only_parent_fields(self):
        for user in (FamilyUserFactory(), self.user):
            with self.subTest(instructor=user.is_instructor):
                self.login(user)
                response = self.tenant_client.get(self.url)
                self.assertEqual(response.status_code, 200)
                self.assertIsInstance(response.context["form"], ParentProfileForm)
                for field in ("iban", "ahv", "birth_date", "bank_name", "is_mep", "password1", "password2"):
                    self.assertNotIn(field, response.context["form"].fields)
                    self.assertNotContains(response, f'name="{field}"')
                self.assertContains(response, 'class="wizard-parent-profile"')
                self.assertContains(response, "Veuillez vérifier vos informations", count=1)
                html = response.content.decode()
                self.assertLess(
                    html.index('class="wizard-parent-profile"'), html.index("Veuillez vérifier vos informations")
                )
                self.assertLess(
                    html.index("Veuillez vérifier vos informations"), html.index('class="wizard-parent-form"')
                )
                self.assertContains(response, "wizard/parent-profile.css")
                self.assertNotContains(response, 'class="form-horizontal"')
                self.assertNotContains(response, reverse("backend:password-change", args=[user.pk]))

    def test_save_updates_parent_details_without_touching_instructor_or_authentication_data(self):
        self.login(self.user)
        password = self.user.password
        response = self.tenant_client.post(
            self.url,
            {**self.data, "bank_name": "Autre banque", "is_mep": "", "password1": "changed", "password2": "different"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("wizard:step", kwargs={"step_slug": "children"}))
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Camille")
        self.assertEqual(self.user.address, "Rue du Lac 3")
        self.assertEqual(self.user.bank_name, "Banque moniteur")
        self.assertTrue(self.user.is_mep)
        self.assertTrue(self.user.is_instructor)
        self.assertEqual(self.user.password, password)

    def test_invalid_parent_data_displays_errors_and_preserves_saved_profile(self):
        self.login(self.user)
        original = self.user.first_name
        response = self.tenant_client.post(self.url, {**self.data, "first_name": "", "email": "invalid"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("first_name", response.context["form"].errors)
        self.assertIn("email", response.context["form"].errors)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, original)

    @override_settings(KEPCHUP_REGISTRATION_HIDE_COUNTRY=True, KEPCHUP_REGISTRATION_HIDE_OTHER_PHONES=True)
    def test_hidden_contact_fields_are_preserved(self):
        self.user.country = "FR"
        self.user.private_phone2 = "+41798888888"
        self.user.save()
        self.login(self.user)
        response = self.tenant_client.post(self.url, self.data)
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.country, "FR")
        self.assertEqual(str(self.user.private_phone2), "+41798888888")

    def test_instructor_account_still_has_its_professional_form(self):
        self.login(self.user)
        response = self.tenant_client.get(reverse("profiles:profiles_account"))
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context["form"], InstructorForm)
        self.assertIn("iban", response.context["form"].fields)

    def test_step_footers_share_styles_and_preserve_confirmation_hooks(self):
        ChildFactory(family=self.user)
        WizardStepFactory(slug="activities", position=2)
        WizardStepFactory(slug="confirmation", position=3)
        self.login(self.user)
        for popup in (False, True):
            with self.subTest(popup=popup), override_settings(
                KEPCHUP_CHILDREN_POPUP=popup, KEPCHUP_ACTIVITIES_POPUP=popup
            ):
                for slug in ("user-update", "children", "activities"):
                    response = self.tenant_client.get(reverse("wizard:step", kwargs={"step_slug": slug}))
                    self.assertEqual(response.status_code, 200)
                    self.assertContains(response, 'class="wizard-actions"')
                    self.assertContains(response, "wizard/navigation.css")
                    if slug == "user-update":
                        continue
                    footer = response.content.decode().split('<ul class="wizard-actions">', 1)[1].split("</ul>", 1)[0]
                    self.assertIn('class="btn btn-default"', footer)
                    self.assertIn('class="btn btn-primary"', footer)
                    if popup:
                        self.assertIn('ng-click="confirmNavigation($event)"', footer)
                    elif slug == "children":
                        self.assertIn("navigateToNextStep($event)", footer)
                    else:
                        self.assertIn('<a href="', footer)
