import json

from django.urls import reverse

from api.tests.utils import UserMixin
from appointments.forms import RentalSelectionForm
from appointments.models import Appointment
from appointments.models import Rental
from appointments.tests.factories import AppointmentSlotFactory
from profiles.tests.factories import FamilyUserFactory
from registrations.models import Registration
from registrations.tests.factories import ChildFactory
from registrations.tests.factories import RegistrationFactory
from sportfac.utils import TenantTestCase


class RentalEligibilityTests(UserMixin, TenantTestCase):
    def setUp(self):
        super().setUp()
        self.user = FamilyUserFactory()
        self.clement = ChildFactory(family=self.user, first_name="Clément")
        self.judith = ChildFactory(family=self.user, first_name="Judith")
        RegistrationFactory(child=self.clement, status=Registration.STATUS.valid)
        self.slot = AppointmentSlotFactory(appointment_type="pickup", places=10)
        self.create_url = reverse("api:rental-list")
        self.pickup_url = reverse("api:appointments-management", kwargs={"slot_id": self.slot.pk})

    def post_json(self, url, data):
        return self.tenant_client.post(url, json.dumps(data), content_type="application/json")

    def test_only_registered_child_is_offered_and_unregistered_sibling_cannot_rent(self):
        form = RentalSelectionForm(user=self.user)
        self.assertEqual(list(form.fields["children"].queryset), [self.clement])
        self.login(self.user)
        response = self.post_json(self.create_url, {"child": self.judith.pk})
        self.assertEqual(response.status_code, 400)
        self.assertIn("child", response.json())
        self.assertFalse(Rental.objects.filter(child=self.judith).exists())

    def test_active_course_selections_can_rent_including_before_final_confirmation(self):
        self.login(self.user)
        for status in (Registration.STATUS.waiting, Registration.STATUS.valid, Registration.STATUS.confirmed):
            with self.subTest(status=status):
                child = ChildFactory(family=self.user)
                RegistrationFactory(child=child, status=status)
                response = self.post_json(self.create_url, {"child": child.pk})
                self.assertEqual(response.status_code, 201, response.content)
                self.assertTrue(Rental.objects.filter(child=child).exists())

    def test_canceled_registration_does_not_allow_rental_even_with_paid_sibling(self):
        registration = RegistrationFactory(child=self.judith)
        Registration.objects.filter(pk=registration.pk).update(status=Registration.STATUS.canceled)
        Rental.objects.create(child=self.clement, paid=True)
        form = RentalSelectionForm(user=self.user, disabled_children_initial=[self.clement])
        self.assertNotIn(self.judith, form.fields["children"].queryset)
        self.login(self.user)
        response = self.post_json(self.create_url, {"child": self.judith.pk})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Rental.objects.filter(child=self.judith).exists())

    def test_foreign_family_child_cannot_be_used_for_rental(self):
        foreign = ChildFactory()
        RegistrationFactory(child=foreign)
        self.login(self.user)
        self.assertEqual(self.post_json(self.create_url, {"child": foreign.pk}).status_code, 400)
        self.assertFalse(Rental.objects.filter(child=foreign).exists())

    def test_existing_ineligible_rental_cannot_be_used_to_book_pickup(self):
        Rental.objects.create(child=self.judith)
        self.login(self.user)
        response = self.post_json(
            self.pickup_url, {"children": [self.judith.pk], "slot": self.slot.pk, "appointment_type": "pickup"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Appointment.objects.filter(child=self.judith).exists())

    def test_mixed_pickup_request_is_rejected_before_any_booking(self):
        for child in (self.clement, self.judith):
            Rental.objects.create(child=child)
        self.login(self.user)
        response = self.post_json(
            self.pickup_url,
            {"children": [self.clement.pk, self.judith.pk], "slot": self.slot.pk, "appointment_type": "pickup"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Appointment.objects.filter(slot=self.slot).exists())

    def test_registered_child_can_book_pickup(self):
        rental = Rental.objects.create(child=self.clement)
        self.login(self.user)
        response = self.post_json(
            self.pickup_url, {"children": [self.clement.pk], "slot": self.slot.pk, "appointment_type": "pickup"}
        )
        self.assertEqual(response.status_code, 201, response.content)
        rental.refresh_from_db()
        self.assertEqual(rental.pickup_appointment.slot_id, self.slot.pk)

    def test_return_remains_possible_for_material_already_rented_without_active_course(self):
        rental = Rental.objects.create(child=self.judith, paid=True)
        slot = AppointmentSlotFactory(appointment_type="return", places=10)
        form = RentalSelectionForm(user=self.user, disabled=True, disabled_children_initial=[self.judith])
        self.assertIn(self.judith, form.fields["disabled_children"].queryset)
        self.login(self.user)
        response = self.post_json(
            reverse("api:appointments-management", kwargs={"slot_id": slot.pk}),
            {"children": [self.judith.pk], "slot": slot.pk, "appointment_type": "return"},
        )
        self.assertEqual(response.status_code, 201, response.content)
        rental.refresh_from_db()
        self.assertEqual(rental.return_appointment.slot_id, slot.pk)

    def test_rental_endpoints_are_scoped_to_the_family(self):
        foreign = ChildFactory()
        rental = Rental.objects.create(child=foreign)
        self.login(self.user)
        detail_url = reverse("api:rental-detail", kwargs={"pk": rental.pk})
        self.assertEqual(self.tenant_client.get(detail_url).status_code, 404)
        response = self.tenant_client.patch(
            detail_url, json.dumps({"child": self.clement.pk}), content_type="application/json"
        )
        self.assertEqual(response.status_code, 404)
        delete_url = reverse("api:rental-detail", kwargs={"pk": foreign.pk})
        self.assertEqual(self.tenant_client.delete(delete_url).status_code, 404)
        self.assertTrue(Rental.objects.filter(pk=rental.pk).exists())

    def test_anonymous_creation_and_booking_are_rejected(self):
        self.assertIn(self.post_json(self.create_url, {"child": self.clement.pk}).status_code, (401, 403))
        self.assertIn(
            self.post_json(
                self.pickup_url, {"children": [self.clement.pk], "slot": self.slot.pk, "appointment_type": "pickup"}
            ).status_code,
            (401, 403),
        )
