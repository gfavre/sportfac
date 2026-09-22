import json
from datetime import date
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.test import override_settings
from django.urls import reverse
from dynamic_preferences.models import GlobalPreferenceModel
from dynamic_preferences.registries import global_preferences_registry
from openpyxl import load_workbook

from absences.paper_pdf import AttendancePDFRenderer
from activities.tests.factories import CourseFactory
from activities.tests.factories import ExtraNeedFactory
from backend.dynamic_preferences_registry import AttendanceExtraColumnsField
from profiles.tests.factories import FamilyUserFactory
from registrations.models import ChildActivityLevel
from registrations.models import ExtraInfo
from registrations.tests.factories import RegistrationFactory
from sportfac.utils import TenantTestCase

from .factories import SessionFactory


class PaperAttendanceTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.settings_override = override_settings(KEPCHUP_PAPER_ATTENDANCE=True, KEPCHUP_EXPLICIT_SESSION_DATES=True)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.clock = patch("absences.paper.timezone.localdate", return_value=date(2026, 2, 7))
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.instructor = FamilyUserFactory()
        self.course = CourseFactory(number="262.6", group_name="9", instructors=[self.instructor])
        self.course.sessions.all().delete()
        for day in (date(2026, 1, 31), date(2026, 2, 7), date(2026, 2, 14)):
            SessionFactory(course=self.course, date=day)
        self.registration = RegistrationFactory(course=self.course, child__first_name="=Alfred")
        self.url = reverse("activities:paper-attendance", kwargs={"course": self.course.pk})
        self.client.force_login(self.instructor)
        self.preferences = global_preferences_registry.manager()
        self.preferences["site__ATTENDANCE_EXTRA_COLUMNS"] = "{}"

    def workbook(self, response):
        self.assertEqual(response.status_code, 200)
        return load_workbook(BytesIO(response.content)).active

    def test_multicourse_pdf_uses_one_sheet_per_course_and_shared_columns(self):
        other = CourseFactory(group_name="12")
        other.sessions.all().delete()
        SessionFactory(course=other, date=date(2026, 2, 14))
        RegistrationFactory(course=other)
        self.client.force_login(FamilyUserFactory(is_manager=True))
        url = reverse("backend:courses-absence")
        captured = {}

        def render(renderer, path):
            captured.update(renderer.context)
            Path(path).write_bytes(b"%PDF-test")

        with patch.object(AttendancePDFRenderer, "render_to_pdf", render):
            response = self.client.get(url, {"c": [self.course.pk, other.pk], "pdf": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        sheets = captured["sheets"]
        self.assertEqual(len(sheets), 2)
        by_course = {sheet["course"].pk: sheet for sheet in sheets}
        self.assertEqual(by_course[self.course.pk]["day"], date(2026, 2, 7))
        self.assertEqual(by_course[other.pk]["day"], date(2026, 2, 14))
        sheet = self.workbook(self.client.get(self.url))
        self.assertEqual(by_course[self.course.pk]["headers"], [cell.value for cell in sheet[3]])
        html = render_to_string(AttendancePDFRenderer.message_template, captured)
        self.assertEqual(html.count('<section class="course-sheet">'), 2)
        self.assertIn("Liste de suivi des cours", html)
        self.assertIn("Groupe 12", html)
        sections = html.split('<section class="course-sheet">')[1:]
        for section, data in zip(sections, sheets):
            self.assertIn(f'N° cours : {data["course"].number}', section)
            self.assertIn(data["day"].strftime("%d.%m.%Y"), section)
            self.assertIn(f'{data["count"]} inscrits', section)

    @override_settings(KEPCHUP_USE_ABSENCES=True)
    def test_tracking_pdf_button_labels(self):
        self.client.force_login(FamilyUserFactory(is_manager=True))
        urls = [reverse("backend:course-list"), reverse("backend:courses-absence") + f"?c={self.course.pk}"]
        for url in urls:
            self.assertContains(self.client.get(url), "Liste de suivi des cours (PDF)")
            with override_settings(KEPCHUP_PAPER_ATTENDANCE=False):
                self.assertNotContains(self.client.get(url), "Liste de suivi des cours (PDF)")

    def test_multicourse_pdf_validates_dates_and_permissions(self):
        url = reverse("backend:courses-absence")
        self.client.force_login(FamilyUserFactory(is_manager=True))
        for value in ("bad-date", "2026-02-08"):
            response = self.client.get(url, {"c": self.course.pk, "pdf": "1", "date": value})
            self.assertEqual(response.status_code, 400 if value == "bad-date" else 200)
            self.assertContains(response, "Préparer les fiches PDF", status_code=response.status_code)
        self.assertContains(self.client.get(url, {"pdf": "1"}), "Aucun cours sélectionné ou accessible")
        self.client.force_login(FamilyUserFactory(is_restricted_manager=True))
        self.assertContains(
            self.client.get(url, {"c": self.course.pk, "pdf": "1"}), "Aucun cours sélectionné ou accessible"
        )
        self.client.logout()
        self.assertEqual(self.client.get(url, {"c": self.course.pk, "pdf": "1"}).status_code, 302)

    def test_prepare_pdf_and_explicitly_download_available_courses(self):
        other = CourseFactory(number="Terminé", group_name="12")
        other.sessions.all().delete()
        SessionFactory(course=other, date=date(2026, 1, 31))
        self.client.force_login(FamilyUserFactory(is_manager=True))
        url = reverse("backend:courses-absence")
        params = {"c": [self.course.pk, other.pk], "pdf": "1"}
        with patch.object(AttendancePDFRenderer, "render_to_pdf") as renderer:
            response = self.client.get(url, params)
            renderer.assert_not_called()
        self.assertContains(response, "Aucune séance à venir")
        self.assertContains(response, "Télécharger la fiche disponible")
        self.assertContains(response, other.get_backend_absences_url())
        self.assertEqual(response.context["ready_count"], 1)
        self.assertEqual(response.context["excluded_count"], 1)
        captured = {}

        def render(renderer, path):
            captured.update(renderer.context)
            Path(path).write_bytes(b"%PDF-test")

        with patch.object(AttendancePDFRenderer, "render_to_pdf", render):
            response = self.client.get(url, {**params, "available": "1"})
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual([sheet["course"].pk for sheet in captured["sheets"]], [self.course.pk])
        response = self.client.get(url, {**params, "date": "2026-01-31", "prepare": "1"})
        self.assertEqual(response.context["ready_count"], 2)
        response = self.client.get(url, {**params, "date": "2026-01-01", "available": "1"})
        self.assertEqual(response.context["ready_count"], 0)
        self.assertContains(response, 'class="btn btn-success" disabled')

    def test_download_header_participants_and_print_settings(self):
        sheet = self.workbook(self.client.get(self.url))
        self.assertEqual(sheet["A1"].value, "N° cours : 262.6")
        self.assertEqual(sheet["C1"].value, 1)
        self.assertIn(self.instructor.get_full_name(), sheet["D1"].value)
        self.assertEqual(sheet["I1"].value.date(), date(2026, 2, 7))
        self.assertEqual(sheet["B4"].value, "9")
        self.assertEqual(sheet["D4"].value, "262.6")
        self.assertEqual(sheet["E4"].value, "=Alfred")
        self.assertEqual(sheet["E4"].data_type, "s")
        self.assertIsNone(sheet["A4"].value)
        self.assertEqual(sheet.page_setup.fitToWidth, 1)
        self.assertEqual(sheet.print_title_rows, "$1:$3")
        self.assertEqual(sheet.auto_filter.ref, "A3:J4")
        for cell in sheet[3]:
            self.assertEqual(cell.fill.fgColor.rgb, "00000000")
            self.assertEqual(cell.font.color.rgb, "00FFFFFF")

    def test_explicit_past_date(self):
        sheet = self.workbook(self.client.get(self.url, {"date": "2026-01-31"}))
        self.assertEqual(sheet["I1"].value.date(), date(2026, 1, 31))

    def test_invalid_dates(self):
        for value in ("", "tomorrow", "2026-02-30", "2026-02-08"):
            with self.subTest(value=value):
                self.assertEqual(self.client.get(self.url, {"date": value}).status_code, 400)

    def test_next_future_session_and_no_future_session(self):
        with patch("absences.paper.timezone.localdate", return_value=date(2026, 2, 8)):
            sheet = self.workbook(self.client.get(self.url))
            self.assertEqual(sheet["I1"].value.date(), date(2026, 2, 14))
        with patch("absences.paper.timezone.localdate", return_value=date(2026, 3, 1)):
            self.assertEqual(self.client.get(self.url).status_code, 400)

    def test_access(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)
        for user in (self.registration.child.family, FamilyUserFactory()):
            self.client.force_login(user)
            self.assertEqual(self.client.get(self.url).status_code, 403)
        other_instructor = FamilyUserFactory()
        CourseFactory(instructors=[other_instructor])
        self.client.force_login(other_instructor)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.force_login(FamilyUserFactory(is_manager=True))
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_disabled(self):
        with override_settings(KEPCHUP_PAPER_ATTENDANCE=False):
            self.assertEqual(self.client.get(self.url).status_code, 404)
            response = self.client.get(self.course.get_absolute_url())
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, "attendance.xlsx")

    def test_restricted_manager_only_managed_activities(self):
        manager = FamilyUserFactory(is_restricted_manager=True)
        self.client.force_login(manager)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        manager.managed_activities.add(self.course.activity)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_weekly_calendar_without_explicit_sessions(self):
        self.course.start_date = date(2026, 2, 1)
        self.course.end_date = date(2026, 2, 22)
        type(self.course).objects.filter(pk=self.course.pk).update(
            start_date=self.course.start_date, end_date=self.course.end_date
        )
        with override_settings(KEPCHUP_EXPLICIT_SESSION_DATES=False):
            sheet = self.workbook(self.client.get(self.url))
            self.assertEqual(sheet["I1"].value.date(), date(2026, 2, 8))

    def test_configured_questions_levels_and_blank_manual_columns(self):
        self.preferences["site__ATTENDANCE_EXTRA_COLUMNS"] = '{"Abo": "Magic Pass ?", "Taille": "Pointure ?"}'
        question = ExtraNeedFactory(question_label="Magic Pass ?", type="B")
        ExtraInfo.objects.create(registration=self.registration, key=question, value="True")
        ChildActivityLevel.objects.create(
            child=self.registration.child, activity=self.course.activity, before_level="A 4A", after_level="A 5B"
        )
        self.registration.child.bib_number = "301"
        self.registration.child.save()
        sheet = self.workbook(self.client.get(self.url))
        self.assertEqual(
            [cell.value for cell in sheet[3]],
            ["Absence", "Gp", "N°", "Abo", "Taille", "N° cours", "Prénom", "Nom", "N-1", "N 2026", "Vient de", "Va à"],
        )
        self.assertEqual(
            [cell.value for cell in sheet[4]],
            [
                None,
                "9",
                "301",
                "Oui",
                None,
                "262.6",
                "=Alfred",
                self.registration.child.last_name,
                "A 4A",
                "A 5B",
                None,
                None,
            ],
        )
        ExtraInfo.objects.filter(registration=self.registration).update(value="False")
        self.assertEqual(self.workbook(self.client.get(self.url))["D4"].value, "Non")

    def test_extra_columns_configuration_validation(self):
        field = AttendanceExtraColumnsField(required=False)
        for value in ("null", "{", '{"Abo": 1}', '{"": "Question"}', '[{"label": "Abo"}]'):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                field.clean(value)
        self.assertEqual(field.clean("{}"), "{}")

    def test_structured_columns_map_stored_values(self):
        question = ExtraNeedFactory(question_label="Magic Pass ?", type="B")
        ExtraInfo.objects.create(registration=self.registration, key=question, value="True")
        columns = [{"question": question.question_label, "label": "Abo", "values": {"True": "M", "False": ""}}]
        self.preferences["site__ATTENDANCE_EXTRA_COLUMNS"] = json.dumps(columns)
        self.assertEqual(self.workbook(self.client.get(self.url))["D4"].value, "M")
        ExtraInfo.objects.filter(registration=self.registration).update(value="False")
        self.assertIsNone(self.workbook(self.client.get(self.url))["D4"].value)
        ExtraInfo.objects.filter(registration=self.registration).update(value="Autre")
        self.assertEqual(self.workbook(self.client.get(self.url))["D4"].value, "Autre")
        ExtraInfo.objects.filter(registration=self.registration).delete()
        self.assertIsNone(self.workbook(self.client.get(self.url))["D4"].value)

    def test_preference_admin_editor_and_save(self):
        question = ExtraNeedFactory(question_label="Magic Pass <test> ?")
        pref = GlobalPreferenceModel.objects.get(section="site", name="ATTENDANCE_EXTRA_COLUMNS")
        url = reverse("admin:dynamic_preferences_globalpreferencemodel_change", args=[pref.pk])
        self.client.force_login(FamilyUserFactory(is_staff=True, is_superuser=True))
        response = self.client.get(url)
        self.assertContains(response, "data-column-template")
        self.assertContains(response, "Magic Pass &lt;test&gt; ?")
        self.assertContains(response, "attendance-extra-columns.js")
        columns = [{"question": question.question_label, "label": "Abo", "values": {"True": "M"}}]
        response = self.client.post(url, {"raw_value": json.dumps(columns), "_save": "Save"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(json.loads(self.preferences["site__ATTENDANCE_EXTRA_COLUMNS"]), columns)
        response = self.client.post(url, {"raw_value": '[{"label":"Abo"}]', "_save": "Save"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Choisissez une question")
        self.assertEqual(json.loads(self.preferences["site__ATTENDANCE_EXTRA_COLUMNS"]), columns)

    def test_no_future_button(self):
        with patch("absences.paper.timezone.localdate", return_value=date(2026, 3, 1)):
            response = self.client.get(self.course.get_absolute_url())
            self.assertContains(response, "aucune séance à venir")
            self.assertNotContains(response, "attendance.xlsx")

    def test_buttons_on_instructor_and_backend_pages(self):
        urls = [self.course.get_absolute_url(), self.course.get_absences_url()]
        for url in urls:
            response = self.client.get(url)
            self.assertContains(response, self.url + "?date=2026-02-07")
        self.client.force_login(FamilyUserFactory(is_manager=True))
        for url in (self.course.get_backend_url(), self.course.get_backend_absences_url()):
            self.assertContains(self.client.get(url), self.url + "?date=2026-02-07")
