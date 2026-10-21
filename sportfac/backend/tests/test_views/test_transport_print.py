from datetime import date
from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse

from absences.models import Absence
from absences.models import Session
from absences.tests.factories import SessionFactory
from activities.tests.factories import CourseFactory
from profiles.tests.factories import FamilyUserFactory
from registrations.models import Registration
from registrations.models import Transport
from registrations.tests.factories import RegistrationFactory
from sportfac.utils import TenantTestCase


class TransportPrintTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        settings_override = override_settings(KEPCHUP_EXPLICIT_SESSION_DATES=True)
        settings_override.enable()
        self.addCleanup(settings_override.disable)
        self.manager = FamilyUserFactory(is_manager=True)
        self.transport = Transport.objects.create(name="Car 1 Montreux")
        self.course = CourseFactory(number="261.4", group_name="5")
        self.course.sessions.all().delete()
        self.day = date(2026, 2, 7)
        self.session = SessionFactory(course=self.course, date=self.day)
        self.registration = RegistrationFactory(course=self.course, transport=self.transport, child__bib_number="138")
        self.url = reverse("backend:transport-print", args=[self.transport.pk])
        self.multi_url = reverse("backend:transports-print")
        self.client.force_login(self.manager)

    def test_prepare_defaults_to_saturday_when_printing_on_friday(self):
        self.assertEqual(self.transport.participants.count(), 1)
        self.assertEqual(self.course.all_dates, [self.day])
        with patch("backend.views.transport_print_views.timezone.localdate", return_value=date(2026, 2, 6)):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_date"], self.day, response.context["available_dates"])
        self.assertEqual(response.context["count"], 1)
        self.assertContains(response, "Date du cours")
        self.assertContains(response, "Télécharger la fiche car PDF")

    @override_settings(KEPCHUP_BIB_NUMBERS=True)
    def test_transport_list_exposes_multiple_selection(self):
        response = self.client.get(reverse("backend:transport-list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="transport-select"')
        self.assertContains(response, "Préparer les fiches cars PDF")
        self.assertContains(response, self.multi_url)
        self.assertContains(response, "Tous les cars")
        self.assertContains(response, "Cars sélectionnés")
        self.assertContains(response, "Concerne tous les cars, quelle que soit la sélection.")

    @patch("backend.views.transport_print_views.render_transport_pdf", return_value=b"%PDF-cars")
    def test_multiple_cars_prepare_then_download_one_pdf(self, renderer):
        from django.template.loader import render_to_string

        other = Transport.objects.create(name="2")
        other_registration = RegistrationFactory(course=self.course, transport=other, child__bib_number="200")
        Absence.objects.update_or_create(
            session=self.session, child=other_registration.child, defaults={"status": "excused"}
        )
        params = {"t": [self.transport.pk, other.pk], "date": "2026-02-07"}
        response = self.client.get(self.multi_url, params)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["ready_count"], 2)
        renderer.assert_not_called()
        response = self.client.get(self.multi_url, {**params, "download": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(response.content, b"%PDF-cars")
        context = renderer.call_args.args[0]
        self.assertEqual(len(context["sheets"]), 2)
        by_car = {sheet["transport"].pk: sheet for sheet in context["sheets"]}
        self.assertEqual(by_car[self.transport.pk]["count"], 1)
        self.assertEqual(by_car[other.pk]["rows"][0]["absences"], "Excusé")
        html = render_to_string("backend/registration/transport-paper-pdf.html", context)
        self.assertEqual(html.count('<section class="transport-sheet">'), 2)
        self.assertIn("Car #2", html)
        self.assertIn("page-break-before: always", html)

    @patch("backend.views.transport_print_views.render_transport_pdf", return_value=b"%PDF-cars")
    def test_unavailable_car_is_excluded_only_after_availability_review(self, renderer):
        empty = Transport.objects.create(name="Car sans séance")
        params = {"t": [self.transport.pk, empty.pk], "date": "2026-02-07", "download": "1"}
        response = self.client.get(self.multi_url, params)
        self.assertEqual(response.status_code, 200)
        renderer.assert_not_called()
        self.assertEqual(response.context["excluded_count"], 1)
        self.assertContains(response, "pas inclus dans le PDF")
        response = self.client.get(self.multi_url, {**params, "available": "1"})
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(len(renderer.call_args.args[0]["sheets"]), 1)

    @patch("backend.views.transport_print_views.render_transport_pdf")
    def test_multiple_cars_reject_invalid_dates_and_empty_selection(self, renderer):
        response = self.client.get(self.multi_url, {"t": ["bad", "999999"], "download": "1"})
        self.assertContains(response, "Aucun car sélectionné", status_code=200)
        for value in ("bad", "2026-02-08"):
            response = self.client.get(self.multi_url, {"t": self.transport.pk, "date": value, "download": "1"})
            self.assertEqual(response.status_code, 400)
        renderer.assert_not_called()

    def test_multicar_selection_deduplicates_ids(self):
        response = self.client.get(
            self.multi_url, {"t": [self.transport.pk, self.transport.pk, "bad"], "date": "2026-02-07"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["sheets"]), 1)

    def test_multicar_permissions(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.multi_url).status_code, 302)
        for user in (FamilyUserFactory(), FamilyUserFactory(is_restricted_manager=True)):
            self.client.force_login(user)
            self.assertEqual(self.client.get(self.multi_url).status_code, 302)

    def test_numeric_car_name_is_labeled_without_duplicating_descriptive_names(self):
        Transport.objects.filter(pk=self.transport.pk).update(name="1")
        response = self.client.get(self.url, {"date": "2026-02-07"})
        self.assertContains(response, "Car #1", status_code=200)
        self.assertEqual(response.context["transport_label"], "Car #1")
        Transport.objects.filter(pk=self.transport.pk).update(name="Car 1 Montreux")
        response = self.client.get(self.url, {"date": "2026-02-07"})
        self.assertEqual(response.context["transport_label"], "Car 1 Montreux")

    @patch("backend.views.transport_print_views.render_transport_pdf", return_value=b"%PDF-test")
    def test_download_contains_only_selected_date_and_groups_after_bibs(self, renderer):
        from django.template.loader import render_to_string

        older = SessionFactory(course=self.course, date=date(2026, 1, 31))
        Absence.objects.update_or_create(session=older, child=self.registration.child, defaults={"status": "absent"})
        Absence.objects.update_or_create(
            session=self.session, child=self.registration.child, defaults={"status": "excused"}
        )
        response = self.client.get(self.url, {"date": "2026-02-07", "download": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(response.content, b"%PDF-test")
        context = renderer.call_args.args[0]
        self.assertEqual(context["rows"][0]["groups"], "5")
        self.assertEqual(context["rows"][0]["absences"], "Excusé")
        html = render_to_string("backend/registration/transport-paper-pdf.html", context)
        self.assertIn("<th>Dossard</th><th>Gp</th>", html)
        self.assertIn("07.02.2026</th>", html)
        self.assertNotIn("31.01.2026", html)
        self.assertIn("Excusé", html)
        self.assertIn("Total : 1 élève", html)

    def test_excludes_other_dates_canceled_registrations_and_other_cars(self):
        other_course = CourseFactory()
        other_course.sessions.all().delete()
        SessionFactory(course=other_course, date=date(2026, 2, 14))
        RegistrationFactory(transport=self.transport, course=other_course)
        canceled = RegistrationFactory(transport=self.transport, course=self.course)
        Registration.objects.filter(pk=canceled.pk).update(status=Registration.STATUS.canceled)
        RegistrationFactory(transport=Transport.objects.create(name="Car 2"), course=self.course)
        response = self.client.get(self.url, {"date": "2026-02-07"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["count"], 1)
        self.assertEqual(response.context["rows"][0]["child"], self.registration.child)

    def test_child_on_multiple_courses_counted_once_without_losing_groups(self):
        other = CourseFactory(number="262.1", group_name="8")
        other.sessions.all().delete()
        SessionFactory(course=other, date=self.day)
        RegistrationFactory(transport=self.transport, course=other, child=self.registration.child)
        response = self.client.get(self.url, {"date": "2026-02-07"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["count"], 1)
        self.assertEqual(response.context["rows"][0]["groups"], "5, 8")
        self.assertEqual(response.context["rows"][0]["courses"], "261.4, 262.1")

    def test_bibs_are_sorted_numerically_and_missing_bib_is_supported(self):
        RegistrationFactory(course=self.course, transport=self.transport, child__bib_number="20")
        RegistrationFactory(course=self.course, transport=self.transport, child__bib_number="")
        response = self.client.get(self.url, {"date": "2026-02-07"})
        self.assertEqual([row["child"].bib_number for row in response.context["rows"]], ["20", "138", ""])

    def test_missing_family_and_present_absence_leave_printable_data(self):
        child = self.registration.child
        child.family = None
        child.save()
        Absence.objects.update_or_create(session=self.session, child=child, defaults={"status": "present"})
        response = self.client.get(self.url, {"date": "2026-02-07"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["rows"][0]["absences"], "")

    @patch("backend.views.transport_print_views.render_transport_pdf")
    def test_invalid_or_unavailable_date_cannot_generate_pdf(self, renderer):
        for value in ("invalid", "2026-02-30", "2026-02-08"):
            with self.subTest(value=value):
                response = self.client.get(self.url, {"date": value, "download": "1"})
                self.assertEqual(response.status_code, 400)
        renderer.assert_not_called()

    def test_reading_the_list_does_not_create_sessions_or_absences(self):
        before = (Session.objects.count(), Absence.objects.count())
        self.client.get(self.url, {"date": "2026-02-07"})
        self.assertEqual((Session.objects.count(), Absence.objects.count()), before)

    def test_weekly_courses_without_explicit_sessions(self):
        self.course.sessions.all().delete()
        type(self.course).objects.filter(pk=self.course.pk).update(start_date=self.day, end_date=date(2026, 2, 21))
        with override_settings(KEPCHUP_EXPLICIT_SESSION_DATES=False):
            response = self.client.get(self.url, {"date": "2026-02-14"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["count"], 1)
        self.assertEqual(response.context["rows"][0]["absences"], "")

    def test_empty_car_and_missing_transport(self):
        empty = Transport.objects.create(name="Car vide")
        response = self.client.get(reverse("backend:transport-print", args=[empty.pk]))
        self.assertContains(response, "Aucune séance disponible", status_code=200)
        self.assertEqual(self.client.get(reverse("backend:transport-print", args=[999999])).status_code, 404)

    def test_anonymous_parent_and_restricted_manager_cannot_access(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)
        for user in (FamilyUserFactory(), FamilyUserFactory(is_restricted_manager=True)):
            self.client.force_login(user)
            self.assertEqual(self.client.get(self.url).status_code, 302)
