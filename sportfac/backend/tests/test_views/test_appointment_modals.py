from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone

from api.tests.utils import UserMixin
from appointments.forms import AppointmentForm
from appointments.models import Appointment
from appointments.models import Rental
from appointments.tests.factories import AppointmentFactory
from appointments.tests.factories import AppointmentSlotFactory
from profiles.tests.factories import FamilyUserFactory
from sportfac.utils import TenantTestCase


class AppointmentModalTests(UserMixin, TenantTestCase):
    headers = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}

    def setUp(self):
        super().setUp()
        self.staff = FamilyUserFactory(is_staff=True)
        self.current = AppointmentSlotFactory(places=1)
        self.appointment = AppointmentFactory(slot=self.current)
        self.target = AppointmentSlotFactory(
            start=self.current.start + timedelta(days=1), end=self.current.end + timedelta(days=1), places=1
        )
        self.full = AppointmentSlotFactory(places=1)
        AppointmentFactory(slot=self.full)
        self.edit_url = self.appointment.get_backend_edit_url
        self.delete_url = self.appointment.get_backend_delete_url

    def test_edit_and_delete_require_staff_for_get_and_post(self):
        for url in (self.edit_url, self.delete_url):
            self.assertEqual(self.tenant_client.get(url, **self.headers).status_code, 302)
            self.assertEqual(self.tenant_client.post(url, {}, **self.headers).status_code, 302)
        self.login(FamilyUserFactory())
        for url in (self.edit_url, self.delete_url):
            self.assertEqual(self.tenant_client.get(url, **self.headers).status_code, 302)
            self.assertEqual(self.tenant_client.post(url, {}, **self.headers).status_code, 302)

    def test_edit_fragment_keeps_current_full_slot_and_excludes_other_full_slots(self):
        self.login(self.staff)
        response = self.tenant_client.get(self.edit_url, **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(self.appointment.child))
        self.assertNotContains(response, "<!DOCTYPE")
        self.assertEqual(
            set(response.context["form"].fields["slot"].queryset.values_list("pk", flat=True)),
            {self.current.pk, self.target.pk},
        )

    def test_modal_moves_existing_appointment_and_preserves_rental_link(self):
        rental = Rental.objects.create(child=self.appointment.child, pickup_appointment=self.appointment)
        other_child = AppointmentFactory().child
        self.login(self.staff)
        response = self.tenant_client.post(
            self.edit_url, {"slot": self.target.pk, "child": other_child.pk}, **self.headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"success": True})
        self.appointment.refresh_from_db()
        rental.refresh_from_db()
        self.assertEqual(self.appointment.slot_id, self.target.pk)
        self.assertEqual(self.appointment.child_id, rental.child_id)
        self.assertEqual(rental.pickup_appointment_id, self.appointment.pk)
        self.assertEqual(self.current.available_places, 1)
        self.assertEqual(self.target.available_places, 0)

    def test_invalid_slot_returns_fragment_errors_without_moving(self):
        self.login(self.staff)
        response = self.tenant_client.post(self.edit_url, {"slot": self.full.pk}, **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn("slot", response.context["form"].errors)
        self.assertContains(response, 'id="appointment-modal-title"')
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.slot_id, self.current.pk)

    def test_capacity_is_rechecked_before_saving(self):
        original = AppointmentForm.is_valid

        def validate_then_fill(form):
            valid = original(form)
            if valid:
                AppointmentFactory(slot=self.target)
            return valid

        self.login(self.staff)
        with patch.object(AppointmentForm, "is_valid", validate_then_fill):
            response = self.tenant_client.post(self.edit_url, {"slot": self.target.pk}, **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ce créneau est complet.")
        self.assertEqual(response.context["current_slot"].pk, self.current.pk)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.slot_id, self.current.pk)

    def test_full_page_fallback_still_renders_and_redirects(self):
        self.login(self.staff)
        self.assertEqual(self.tenant_client.get(self.edit_url).status_code, 200)
        self.assertEqual(self.tenant_client.get(self.delete_url).status_code, 200)
        response = self.tenant_client.post(self.edit_url, {"slot": self.target.pk})
        self.assertEqual(response.status_code, 302)

    def test_delete_confirmation_and_post_preserve_rental(self):
        rental = Rental.objects.create(child=self.appointment.child, pickup_appointment=self.appointment)
        self.login(self.staff)
        response = self.tenant_client.get(self.delete_url, **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(self.appointment.child))
        self.assertNotContains(response, "<!DOCTYPE")
        response = self.tenant_client.post(self.delete_url, {}, **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"success": True, "deleted": True})
        self.assertFalse(Appointment.objects.filter(pk=self.appointment.pk).exists())
        rental.refresh_from_db()
        self.assertIsNone(rental.pickup_appointment_id)
        self.assertTrue(rental.child_id)

    def test_current_full_slot_can_be_saved_without_changing_it(self):
        self.login(self.staff)
        response = self.tenant_client.post(self.edit_url, {"slot": self.current.pk}, **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"success": True})

    def test_past_slots_are_neither_offered_nor_accepted_as_destinations(self):
        past = AppointmentSlotFactory(start=timezone.now() - timedelta(days=2), end=timezone.now() - timedelta(days=1))
        self.login(self.staff)
        response = self.tenant_client.get(self.edit_url, **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(past, response.context["form"].fields["slot"].queryset)
        response = self.tenant_client.post(self.edit_url, {"slot": past.pk}, **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn("slot", response.context["form"].errors)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.slot_id, self.current.pk)

    def test_past_current_appointment_stays_in_summary_but_not_destination_choices(self):
        self.current.start = timezone.now() - timedelta(days=2)
        self.current.end = timezone.now() - timedelta(days=1)
        self.current.save()
        self.login(self.staff)
        response = self.tenant_client.get(self.edit_url, **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["current_slot"].pk, self.current.pk)
        self.assertNotIn(self.current, response.context["form"].fields["slot"].queryset)
        self.assertIn(self.target, response.context["form"].fields["slot"].queryset)
