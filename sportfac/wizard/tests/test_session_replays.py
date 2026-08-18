import datetime
import json

from django.urls import reverse
from django.utils import timezone

from activities.tests.factories import CourseFactory
from api.tests.utils import UserMixin
from profiles.tests.factories import FamilyUserFactory
from profiles.tests.factories import SchoolYearFactory
from registrations.models import Child
from registrations.models import Registration
from registrations.models import RegistrationValidation
from registrations.tests.factories import ChildFactory
from sportfac.utils import TenantTestCase as TestCase

from .factories import WizardStepFactory


def _open_registration_period(tenant):
    now = timezone.now()
    tenant.preferences["phase__START_REGISTRATION"] = now - datetime.timedelta(days=1)
    tenant.preferences["phase__END_REGISTRATION"] = now + datetime.timedelta(days=1)


def _create_core_wizard_steps():
    # Positions matter: they drive WizardWorkflow.get_next_step/get_previous_step. No
    # "payment" step is created on purpose - with KEPCHUP_PAYMENT_METHOD="iban" (the test
    # default), confirmation is directly followed by success, matching the production
    # traces these tests replay.
    WizardStepFactory(slug="user-update", position=0)
    WizardStepFactory(slug="children", position=1)
    WizardStepFactory(slug="activities", position=2)
    WizardStepFactory(slug="questions", position=3)
    WizardStepFactory(slug="confirmation", position=4)
    WizardStepFactory(slug="success", position=5)


class WizardHappyPathReplayTests(UserMixin, TestCase):
    """Replays the "wizard-completed-payment" production session: an already-authenticated
    family updates their profile, picks a course for their child and confirms the
    registration."""

    def setUp(self):
        super().setUp()
        _open_registration_period(self.tenant)
        _create_core_wizard_steps()
        self.user = FamilyUserFactory()
        self.child = ChildFactory(family=self.user)
        self.course = CourseFactory()

    def test_full_registration_flow(self):
        self.login(self.user)

        response = self.tenant_client.get(reverse("wizard:entry_point"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("user-update", response.url)

        response = self.tenant_client.get(reverse("wizard:step", kwargs={"step_slug": "user-update"}))
        self.assertEqual(response.status_code, 200)

        response = self.tenant_client.post(
            reverse("wizard:step", kwargs={"step_slug": "user-update"}),
            data={
                "email": self.user.email,
                "first_name": "Jean",
                "last_name": "Dupont",
                "address": "Rue du Lac 3",
                "zipcode": "1800",
                "city": "Vevey",
                "country": "CH",
                "private_phone": "+41791234567",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("children", response.url)

        response = self.tenant_client.get(reverse("wizard:step", kwargs={"step_slug": "activities"}))
        self.assertEqual(response.status_code, 200)

        # Representative polling call: the SPA fetches the selected course's details.
        response = self.tenant_client.get(reverse("api:course-detail", kwargs={"pk": self.course.pk}))
        self.assertEqual(response.status_code, 200)

        response = self.tenant_client.post(
            reverse("api:registration-list"),
            data={"child": self.child.pk, "course": self.course.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 201)

        # "questions" has no configured questions - it just forwards to confirmation.
        response = self.tenant_client.get(reverse("wizard:step", kwargs={"step_slug": "questions"}))
        self.assertEqual(response.status_code, 302)
        self.assertIn("confirmation", response.url)

        response = self.tenant_client.get(reverse("wizard:step", kwargs={"step_slug": "confirmation"}))
        self.assertEqual(response.status_code, 200)

        response = self.tenant_client.post(
            reverse("wizard:step", kwargs={"step_slug": "confirmation"}),
            data={"consent_given": True},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("success", response.url)

        response = self.tenant_client.get(reverse("wizard:step", kwargs={"step_slug": "success"}))
        self.assertEqual(response.status_code, 200)

        registration = Registration.objects.get(child=self.child, course=self.course)
        self.assertEqual(registration.status, Registration.STATUS.valid)
        self.assertIsNotNone(registration.bill)
        self.assertEqual(registration.bill.family, self.user)
        self.assertGreater(registration.bill.total, 0)

        validation = RegistrationValidation.objects.get(user=self.user)
        self.assertTrue(validation.consent_given)


class WizardImpersonationReplayTests(UserMixin, TestCase):
    """Replays the "admin" production session: a manager impersonates a family, completes
    a registration on their behalf, then stops impersonating."""

    def setUp(self):
        super().setUp()
        _open_registration_period(self.tenant)
        _create_core_wizard_steps()
        self.manager = FamilyUserFactory(is_manager=True)
        self.family_user = FamilyUserFactory()
        self.child = ChildFactory(family=self.family_user)
        self.course = CourseFactory()

    def test_impersonated_registration_then_stop(self):
        self.login(self.manager)

        response = self.tenant_client.get(reverse("impersonate-start", kwargs={"uid": self.family_user.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.tenant_client.session["_impersonate"], str(self.family_user.pk))

        # While impersonating, the effective user is the family, not the manager: braces'
        # UserPassesTestMixin bounces non-managers to the login page instead of the backend.
        response = self.tenant_client.get(reverse("backend:user-list"))
        self.assertEqual(response.status_code, 302)
        self.assertNotEqual(response.url, reverse("backend:user-list"))

        response = self.tenant_client.get(reverse("wizard:entry_point"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("user-update", response.url)

        response = self.tenant_client.post(
            reverse("wizard:step", kwargs={"step_slug": "user-update"}),
            data={
                "email": self.family_user.email,
                "first_name": "Marie",
                "last_name": "Rochat",
                "address": "Avenue de la Gare 12",
                "zipcode": "1820",
                "city": "Montreux",
                "country": "CH",
                "private_phone": "+41791112233",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("children", response.url)

        response = self.tenant_client.get(reverse("wizard:step", kwargs={"step_slug": "activities"}))
        self.assertEqual(response.status_code, 200)

        response = self.tenant_client.post(
            reverse("api:registration-list"),
            data={"child": self.child.pk, "course": self.course.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 201)

        response = self.tenant_client.get(reverse("wizard:step", kwargs={"step_slug": "confirmation"}))
        self.assertEqual(response.status_code, 200)

        response = self.tenant_client.post(
            reverse("wizard:step", kwargs={"step_slug": "confirmation"}),
            data={"consent_given": True},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("success", response.url)

        response = self.tenant_client.get(reverse("wizard:step", kwargs={"step_slug": "success"}))
        self.assertEqual(response.status_code, 200)

        registration = Registration.objects.get(child=self.child, course=self.course)
        self.assertEqual(registration.status, Registration.STATUS.valid)
        self.assertEqual(registration.bill.family, self.family_user)

        response = self.tenant_client.get(reverse("impersonate-stop"))
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("_impersonate", self.tenant_client.session)

        # Back to being the manager: the backend is reachable again.
        response = self.tenant_client.get(reverse("backend:user-list"))
        self.assertEqual(response.status_code, 200)


class WizardValidationRetryReplayTests(UserMixin, TestCase):
    """Replays the "wizard-authenticated-abandoned" production session: a child creation
    is rejected (400) because a required field is missing, then a corrected update on the
    existing child succeeds - the same recovery shape as the real POST /api/children/ 400
    followed by a successful PUT /api/children/<id>/."""

    def setUp(self):
        super().setUp()
        _open_registration_period(self.tenant)
        _create_core_wizard_steps()
        self.year = SchoolYearFactory()
        self.user = FamilyUserFactory()
        self.child = ChildFactory(family=self.user, first_name="Ancien")

    def test_invalid_child_payload_then_corrected_retry(self):
        self.login(self.user)

        response = self.tenant_client.get(reverse("wizard:step", kwargs={"step_slug": "children"}))
        self.assertEqual(response.status_code, 200)

        # school_year has no `required=False` on ChildrenSerializer, so it stays mandatory
        # even though the model field itself is nullable - a realistic client-side slip.
        invalid_payload = {
            "first_name": "Nouveau",
            "last_name": "Dupont",
            "sex": "M",
            "nationality": "CH",
            "language": "F",
            "birth_date": "2016-03-12",
        }
        response = self.tenant_client.post(reverse("api:child-list"), invalid_payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("school_year", response.data)
        self.assertEqual(Child.objects.count(), 1)

        valid_payload = dict(invalid_payload, school_year=self.year.year)
        url = reverse("api:child-detail", kwargs={"pk": self.child.pk})
        response = self.tenant_client.put(url, json.dumps(valid_payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)

        self.child.refresh_from_db()
        self.assertEqual(self.child.first_name, "Nouveau")
        self.assertEqual(self.child.school_year, self.year)
        self.assertEqual(Child.objects.count(), 1)

        response = self.tenant_client.get(reverse("wizard:step", kwargs={"step_slug": "activities"}))
        self.assertEqual(response.status_code, 200)
