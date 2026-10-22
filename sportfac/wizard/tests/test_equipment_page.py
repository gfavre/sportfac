from datetime import timedelta

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from api.tests.utils import UserMixin
from appointments.forms import RentalSelectionForm
from appointments.models import Rental
from appointments.serializers import RentalSerializer
from appointments.tests.factories import AppointmentFactory
from appointments.tests.factories import AppointmentSlotFactory
from profiles.tests.factories import FamilyUserFactory
from registrations.tests.factories import ChildFactory
from registrations.tests.factories import RegistrationFactory
from sportfac.utils import TenantTestCase

from .factories import WizardStepFactory


class EquipmentPageTests(UserMixin, TenantTestCase):
    def setUp(self):
        super().setUp()
        configuration = override_settings(KEPCHUP_USE_APPOINTMENTS=True, ROOT_URLCONF="wizard.tests.equipment_urls")
        configuration.enable()
        self.addCleanup(configuration.disable)
        now = timezone.now()
        self.tenant.preferences["phase__START_REGISTRATION"] = now - timedelta(days=1)
        self.tenant.preferences["phase__END_REGISTRATION"] = now + timedelta(days=1)
        for position, slug in enumerate(
            ("user-update", "children", "activities", "equipment", "equipment-return", "confirmation")
        ):
            WizardStepFactory(slug=slug, position=position)
        self.user = FamilyUserFactory()
        self.child = ChildFactory(family=self.user)
        RegistrationFactory(child=self.child)
        self.url = reverse("wizard:step", kwargs={"step_slug": "equipment"})
        self.slot = AppointmentSlotFactory(
            start=now + timedelta(days=3), end=now + timedelta(days=3, hours=1), appointment_type="pickup"
        )

    def test_login_is_required(self):
        self.assertEqual(self.tenant_client.get(self.url).status_code, 302)

    def test_pickup_sections_keep_calendar_and_rental_hooks(self):
        self.login(self.user)
        response = self.tenant_client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="wizard-equipment"')
        self.assertContains(response, "wizard/equipment.css")
        for element_id in (
            "rent-yes",
            "rent-no",
            "rental-form",
            "dates-selection",
            "calendar",
            "modal-save-btn",
            "next-step-btn",
        ):
            self.assertContains(response, f'id="{element_id}"')
        self.assertContains(response, "Enfants concernés")
        self.assertContains(response, "Choisir un rendez-vous de retrait")
        self.assertContains(response, self.slot.start.date().isoformat())
        self.assertContains(response, "dayGridMonth,timeGridWeek,timeGridDay")
        self.assertContains(response, "Accès rapide aux dates proposées")
        self.assertContains(
            response, "Cliquez sur un créneau disponible dans le calendrier pour réserver votre rendez-vous."
        )
        self.assertNotContains(response, 'class="lead"')

    def test_existing_rental_is_still_selected(self):
        Rental.objects.create(child=self.child)
        self.login(self.user)
        response = self.tenant_client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.child, response.context["form"].initial["children"])
        self.assertEqual(response.context["rentals_json"][0]["child"], self.child.pk)
        self.assertFalse(response.context["form"].fields["children"].widget.attrs.get("disabled", False))

    def test_return_uses_same_layout_with_locked_child_selection(self):
        Rental.objects.create(child=self.child)
        self.login(self.user)
        response = self.tenant_client.get(reverse("wizard:step", kwargs={"step_slug": "equipment-return"}))
        self.assertEqual(response.status_code, 200, getattr(response, "url", ""))
        self.assertContains(response, "Choisir un rendez-vous de retour")
        self.assertNotContains(response, "equipment-introduction")
        self.assertNotContains(response, "Restitution du matériel")
        self.assertContains(response, 'id="rent-yes"')
        self.assertTrue(response.context["form"].fields["children"].widget.attrs["disabled"])
        self.assertEqual(response.context["form"].fields["children"].label, "")
        self.assertEqual(response.context["form"].fields["disabled_children"].label, "")
        self.assertContains(response, "Le rendez-vous de retour concerne le matériel loué pour ces enfants.")

    def test_saved_appointment_dates_are_available_on_reload_and_after_booking(self):
        pickup = AppointmentFactory(child=self.child, slot=self.slot)
        return_slot = AppointmentSlotFactory(appointment_type="return")
        returned = AppointmentFactory(child=self.child, slot=return_slot)
        rental = Rental.objects.create(child=self.child, pickup_appointment=pickup, return_appointment=returned)
        self.login(self.user)
        for slug in ("equipment", "equipment-return"):
            with self.subTest(slug=slug):
                response = self.tenant_client.get(reverse("wizard:step", kwargs={"step_slug": slug}))
                self.assertEqual(response.status_code, 200)
                data = response.context["rentals_json"][0]
                self.assertEqual(parse_datetime(data["pickup_start"]), self.slot.start)
                self.assertEqual(parse_datetime(data["return_start"]), return_slot.start)
                self.assertContains(response, "Rendez-vous enregistré")
        data = RentalSerializer(rental).data
        self.assertIsNotNone(data["pickup_start"])
        self.assertIsNotNone(data["return_start"])

    def test_unbooked_rental_has_no_appointment_date(self):
        data = RentalSerializer(Rental.objects.create(child=self.child)).data
        self.assertIsNone(data["pickup_start"])
        self.assertIsNone(data["return_start"])

    def test_form_keeps_paid_rentals_disabled(self):
        Rental.objects.create(child=self.child, paid=True)
        form = RentalSelectionForm(user=self.user, disabled_children_initial=self.user.children.all())
        self.assertEqual(list(form.fields["disabled_children"].queryset), [self.child])
        self.assertTrue(form.fields["disabled_children"].widget.attrs["disabled"])
        self.assertNotIn(self.child, form.fields["children"].queryset)
        self.assertEqual(form.helper.form_id, "rental-form")

    def test_paid_rental_remains_available_for_appointment_selection(self):
        rental = Rental.objects.create(child=self.child, paid=True)
        self.login(self.user)
        response = self.tenant_client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["rentals_json"][0]["id"], rental.pk)
        self.assertIn(self.child, response.context["form"].initial["disabled_children"])
        self.assertContains(response, "querySelectorAll('input[type=\"checkbox\"]:checked')")

    def test_child_without_course_registration_is_not_offered_for_rental(self):
        child = ChildFactory(family=self.user)
        other_child = ChildFactory()
        self.login(self.user)
        response = self.tenant_client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(child, response.context["form"].fields["children"].queryset)
        self.assertNotIn(other_child, response.context["form"].fields["children"].queryset)
        Rental.objects.create(child=self.child, paid=True)
        response = self.tenant_client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(child, response.context["form"].fields["children"].queryset)
