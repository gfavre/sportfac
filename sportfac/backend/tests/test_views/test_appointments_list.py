from datetime import timedelta

from django.db import connection
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from api.tests.utils import UserMixin
from appointments.tests.factories import AppointmentFactory
from appointments.tests.factories import AppointmentSlotFactory
from backend.views.site_views import AppointmentsListView
from profiles.tests.factories import FamilyUserFactory
from sportfac.utils import TenantTestCase


class AppointmentsListTests(UserMixin, TenantTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("backend:appointments-list")
        self.staff = FamilyUserFactory(is_staff=True)
        self.start = (timezone.now() + timedelta(days=3)).replace(hour=10, minute=0, second=0, microsecond=0)

    def create_booking(self, start=None):
        start = start or self.start
        slot = AppointmentSlotFactory(start=start, end=start + timedelta(minutes=15))
        return AppointmentFactory(slot=slot)

    def test_login_and_role_required(self):
        self.assertEqual(self.tenant_client.get(self.url).status_code, 302)
        self.login(FamilyUserFactory())
        response = self.tenant_client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_default_shows_all_dates_with_contacts_and_actions(self):
        first = self.create_booking()
        later = self.create_booking(self.start + timedelta(days=7))
        self.create_booking(self.start - timedelta(days=10))
        self.login(self.staff)
        response = self.tenant_client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_date"], "all")
        self.assertEqual(response.context["appointment_count"], 3)
        self.assertContains(response, str(first.child))
        self.assertContains(response, first.child.family.email)
        self.assertContains(response, first.get_backend_edit_url)
        self.assertContains(response, first.get_backend_delete_url)
        self.assertContains(response, later.get_backend_edit_url)

    def test_date_filter_and_optional_empty_slots(self):
        booked = self.create_booking()
        empty = AppointmentSlotFactory(
            start=self.start + timedelta(minutes=30), end=self.start + timedelta(minutes=45)
        )
        self.login(self.staff)
        date = timezone.localdate(self.start).isoformat()
        response = self.tenant_client.get(self.url, {"date": date, "empty": "0"})
        self.assertEqual([slot.pk for slot in response.context["object_list"]], [booked.slot_id])
        response = self.tenant_client.get(self.url, {"date": date, "empty": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["slot_count"], 2)
        self.assertEqual(response.context["appointment_count"], 1)
        self.assertContains(response, f'id="appointments-slot-{empty.pk}"')
        self.assertContains(response, "Aucun rendez-vous enregistré sur ce créneau.")

    def test_all_dates_are_paginated_and_filters_are_preserved(self):
        for index in range(227):
            self.create_booking(self.start + timedelta(minutes=index * 15))
        self.login(self.staff)
        response = self.tenant_client.get(self.url, {"date": "all"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["object_list"]), 25)
        self.assertEqual(response.context["appointment_count"], 227)
        self.assertContains(response, "date=all&amp;empty=1&amp;q=&amp;page=2")
        response = self.tenant_client.get(self.url, {"date": "all", "page": "10"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["object_list"]), 2)

    def test_invalid_date_falls_back_without_error(self):
        self.create_booking()
        self.login(self.staff)
        for date in ("not-a-date", "2026-02-31"):
            response = self.tenant_client.get(self.url, {"date": date})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["selected_date"], "all")

    def test_empty_list(self):
        self.login(self.staff)
        response = self.tenant_client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["appointment_count"], 0)
        self.assertContains(response, "Aucun rendez-vous pour cette sélection")

    def test_contacts_are_prefetched_with_constant_query_count(self):
        for index in range(8):
            self.create_booking(self.start + timedelta(minutes=index * 15))
        view = AppointmentsListView()
        view.request = RequestFactory().get(self.url, {"date": "all"})
        with CaptureQueriesContext(connection) as queries:
            slots = list(view.get_queryset())
            for slot in slots:
                for appointment in slot.appointments.all():
                    str(appointment.child)
                    appointment.child.family.best_phone
                    appointment.child.family.email
        # django-tenants also issues SET search_path before each SELECT.
        self.assertEqual(sum(query["sql"].lstrip().startswith("SELECT") for query in queries), 4)

    def test_summary_counts_multiple_children_in_one_slot_once(self):
        appointment = self.create_booking()
        AppointmentFactory(slot=appointment.slot)
        self.login(self.staff)
        response = self.tenant_client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["slot_count"], 1)
        self.assertEqual(response.context["appointment_count"], 2)

    def test_search_finds_child_across_dates_and_keeps_slot_contacts_complete(self):
        appointment = self.create_booking()
        appointment.child.first_name = "Camille"
        appointment.child.last_name = "Exemple"
        appointment.child.save()
        other = AppointmentFactory(slot=appointment.slot)
        excluded = self.create_booking(self.start + timedelta(days=7))
        self.login(self.staff)
        response = self.tenant_client.get(self.url, {"q": "Camille Exemple"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["slot_count"], 1)
        self.assertEqual(response.context["appointment_count"], 2)
        self.assertContains(response, other.get_backend_edit_url)
        self.assertNotContains(response, excluded.get_backend_edit_url)

    def test_empty_slots_and_remaining_capacity_are_visible_by_default(self):
        slot = AppointmentSlotFactory(start=self.start, end=self.start + timedelta(minutes=15), places=4)
        self.login(self.staff)
        response = self.tenant_client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["include_empty"])
        self.assertContains(response, f'id="appointments-slot-{slot.pk}"')
        self.assertContains(response, "4 places disponibles")
