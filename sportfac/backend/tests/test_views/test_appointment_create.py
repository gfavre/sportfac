from datetime import timedelta
from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone

from api.tests.utils import UserMixin
from appointments.forms import AppointmentCreateForm
from appointments.models import Appointment
from appointments.models import Rental
from appointments.tests.factories import AppointmentFactory
from appointments.tests.factories import AppointmentSlotFactory
from profiles.tests.factories import FamilyUserFactory
from registrations.models import Registration
from registrations.tests.factories import ChildFactory
from registrations.tests.factories import RegistrationFactory
from sportfac.utils import TenantTestCase


class AppointmentCreateTests(UserMixin, TenantTestCase):
    def setUp(self):
        super().setUp()
        self.staff = FamilyUserFactory(is_staff=True)
        self.child = ChildFactory(first_name="Camille", last_name="Exemple")
        self.registration = RegistrationFactory(child=self.child, status=Registration.STATUS.confirmed)
        self.slot = AppointmentSlotFactory(appointment_type="pickup", places=2)
        self.url = reverse("backend:appointment-create") + "?q=Camille+Exemple"

    def book(self, **data):
        return self.tenant_client.post(self.url, {"child": self.child.pk, "slot": self.slot.pk, **data})

    def test_login_and_role_required(self):
        for user in (None, FamilyUserFactory(), FamilyUserFactory(is_restricted_manager=True)):
            if user:
                self.login(user)
            self.assertEqual(self.tenant_client.get(self.url).status_code, 302)
            self.assertEqual(self.book().status_code, 302)
        self.assertFalse(Appointment.objects.exists())

    def test_staff_search_finds_child_without_appointment_by_name_or_parent_email(self):
        self.login(self.staff)
        for search in ("Camille Exemple", self.child.family.email):
            response = self.tenant_client.get(reverse("backend:appointment-create"), {"q": search})
            self.assertEqual(response.status_code, 200)
            self.assertIn(self.child, response.context["form"].fields["child"].queryset)
            self.assertContains(response, 'name="csrfmiddlewaretoken"')

    def test_empty_search_and_no_match(self):
        self.login(self.staff)
        url = reverse("backend:appointment-create")
        response = self.tenant_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["form"].fields["child"].queryset.exists())
        response = self.tenant_client.get(url, {"q": "no-such-child"})
        self.assertContains(response, "Aucun enfant trouvé")

    def test_unique_result_is_selected_without_a_child_menu(self):
        self.login(self.staff)
        response = self.tenant_client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["single_child"], self.child)
        self.assertEqual(response.context["form"]["child"].value(), self.child.pk)
        self.assertContains(response, 'type="hidden" name="child"')
        self.assertNotContains(response, '<select name="child"')
        self.assertContains(response, self.child.family.email)
        self.assertContains(response, "backend/css/appointments.css")

    def test_multiple_results_are_direct_choices_and_keep_selection_on_error(self):
        other = ChildFactory(first_name="Camille", last_name="Exemple")
        self.login(self.staff)
        response = self.tenant_client.get(self.url)
        self.assertIsNone(response.context["single_child"])
        self.assertContains(response, 'type="radio" name="child"', count=2)
        self.assertNotContains(response, '<select name="child"')
        self.assertContains(response, other.family.email)
        response = self.book(child=other.pk, slot="")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form"]["child"].value(), str(other.pk))
        self.assertContains(response, f'value="{other.pk}" required checked')
        self.assertIn("slot", response.context["form"].errors)

    def test_unique_result_does_not_override_tampered_child_on_submission(self):
        other = ChildFactory(first_name="Autre", last_name="Enfant")
        self.login(self.staff)
        response = self.book(child=other.pk)
        self.assertEqual(response.status_code, 200)
        self.assertIn("child", response.context["form"].errors)
        self.assertFalse(Appointment.objects.exists())

    def test_creation_links_pickup_to_unpaid_rental_without_changing_registration(self):
        self.login(self.staff)
        self.assertRedirects(self.book(), reverse("backend:appointments-list"))
        appointment = Appointment.objects.get(child=self.child)
        rental = Rental.objects.get(child=self.child)
        self.assertEqual(appointment.family, self.child.family)
        self.assertEqual(rental.pickup_appointment, appointment)
        self.assertFalse(rental.paid)
        self.assertIsNone(rental.invoice_id)
        self.registration.refresh_from_db()
        self.assertEqual(self.registration.status, Registration.STATUS.confirmed)

    def test_pickup_requires_registration_for_this_child(self):
        self.login(self.staff)
        RegistrationFactory(child=ChildFactory(family=self.child.family))
        for status in (Registration.STATUS.canceled, None):
            with self.subTest(status=status):
                if status:
                    Registration.objects.filter(pk=self.registration.pk).update(status=status)
                else:
                    self.registration.delete()
                response = self.book()
                self.assertEqual(response.status_code, 200)
                self.assertIn("child", response.context["form"].errors)
                self.assertFalse(Appointment.objects.filter(child=self.child).exists())
                self.assertFalse(Rental.objects.filter(child=self.child).exists())

    def test_return_requires_rental_but_allows_return_after_course_cancellation(self):
        self.slot.appointment_type = "return"
        self.slot.save()
        Registration.objects.filter(pk=self.registration.pk).update(status=Registration.STATUS.canceled)
        self.login(self.staff)
        self.assertIn("child", self.book().context["form"].errors)
        rental = Rental.objects.create(child=self.child, paid=True)
        self.assertEqual(self.book().status_code, 302)
        rental.refresh_from_db()
        self.assertEqual(rental.return_appointment.slot, self.slot)
        self.assertTrue(rental.paid)

    def test_other_appointment_does_not_create_rental(self):
        self.slot.appointment_type = "other"
        self.slot.save()
        self.registration.delete()
        self.login(self.staff)
        self.assertEqual(self.book().status_code, 302)
        self.assertFalse(Rental.objects.filter(child=self.child).exists())

    def test_full_or_past_slot_is_rejected(self):
        self.login(self.staff)
        for slot in (
            AppointmentSlotFactory(places=0),
            AppointmentSlotFactory(start=timezone.now() - timedelta(days=2)),
        ):
            response = self.book(slot=slot.pk)
            self.assertIn("slot", response.context["form"].errors)
        self.assertFalse(Appointment.objects.filter(child=self.child).exists())

    def test_capacity_is_rechecked_before_saving(self):
        self.slot.places = 1
        self.slot.save()
        original = AppointmentCreateForm.is_valid

        def validate_then_fill(form):
            valid = original(form)
            if valid:
                AppointmentFactory(slot=self.slot)
            return valid

        self.login(self.staff)
        with patch.object(AppointmentCreateForm, "is_valid", validate_then_fill):
            response = self.book()
        self.assertIn("slot", response.context["form"].errors)
        self.assertFalse(Appointment.objects.filter(child=self.child).exists())

    def test_existing_paid_rental_link_is_preserved_and_duplicate_is_rejected(self):
        pickup = AppointmentFactory(child=self.child)
        rental = Rental.objects.create(child=self.child, pickup_appointment=pickup, paid=True)
        self.login(self.staff)
        response = self.book()
        self.assertIn("slot", response.context["form"].errors)
        rental.refresh_from_db()
        self.assertEqual(rental.pickup_appointment, pickup)
        self.assertTrue(rental.paid)
        self.assertEqual(Appointment.objects.filter(child=self.child).count(), 1)

    def test_repeated_submission_does_not_create_duplicate(self):
        self.login(self.staff)
        self.assertEqual(self.book().status_code, 302)
        response = self.book()
        self.assertIn("slot", response.context["form"].errors)
        self.assertEqual(Appointment.objects.filter(child=self.child).count(), 1)
