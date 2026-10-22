from django.urls import reverse

from api.tests.utils import UserMixin
from appointments.tests.factories import AppointmentSlotFactory
from profiles.tests.factories import FamilyUserFactory
from sportfac.utils import TenantTestCase


class AppointmentsLayoutTests(UserMixin, TenantTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("backend:appointments-manage")

    def test_login_required(self):
        self.assertEqual(self.tenant_client.get(self.url).status_code, 302)

    def test_family_cannot_manage_appointments(self):
        self.login(FamilyUserFactory())
        response = self.tenant_client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_staff_calendar_has_navigation_and_slot_editor(self):
        slot = AppointmentSlotFactory()
        self.login(FamilyUserFactory(is_staff=True))
        response = self.tenant_client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Créneaux de rendez-vous")
        self.assertContains(response, reverse("backend:appointments-list"))
        self.assertContains(response, 'id="calendar-date"')
        self.assertContains(response, slot.start.date().isoformat())
        self.assertContains(response, "backend/css/appointments.css")
        for element_id in (
            "calendar",
            "calendar-modal",
            "id_places",
            "id_appointment_type",
            "save-event",
            "remove-event",
        ):
            self.assertContains(response, f'id="{element_id}"')
        self.assertNotContains(response, "prompt(")

    def test_staff_can_open_empty_calendar(self):
        self.login(FamilyUserFactory(is_staff=True))
        self.assertEqual(self.tenant_client.get(self.url).status_code, 200)
