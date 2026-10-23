from datetime import date
from io import BytesIO
from unittest.mock import patch

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from django_tenants.utils import schema_context
from pypdf import PdfReader
from pypdf import PdfWriter

from absences.tests.factories import SessionFactory
from activities.tests.factories import CourseFactory
from mailer.pdfutils import PDFRenderer
from profiles.management.commands.merge_family_accounts import Command as MergeAccounts
from profiles.tests.factories import FamilyUserFactory
from registrations.models import ChildActivityLevel
from registrations.tests.factories import RegistrationFactory
from sportfac.utils import TenantTestCase

from .forms import BatchForm
from .forms import validate_supplement
from .models import Diploma
from .models import DiplomaBatch
from .models import DiplomaEvent
from .services import course_mail_history
from .services import create_batch
from .services import separate_draft_courses
from .tasks import DiplomaRenderer
from .tasks import generate_batch
from .tasks import render_diplomas
from .tasks import send_batch


def sample_pdf(width=595):
    with PdfWriter() as writer:
        writer.add_blank_page(width=width, height=420)
        output = BytesIO()
        writer.write_stream(output)
        return output.getvalue()


class DiplomaTests(TenantTestCase):
    def test_reopening_grouped_draft_separates_course_rosters_and_preserves_content(self):
        other_course = CourseFactory()
        other_registration = RegistrationFactory(course=other_course)
        data = {
            **self.data,
            "courses": type(self.course).objects.filter(pk__in=[self.course.pk, other_course.pk]),
            "supplement": SimpleUploadedFile("infos.pdf", sample_pdf(), content_type="application/pdf"),
        }
        grouped = create_batch(data, self.manager)
        other_diploma = grouped.diplomas.get(source_registration_id=other_registration.pk)
        DiplomaEvent.objects.create(batch=grouped, diploma=other_diploma, actor=self.manager, action="edited")
        url = reverse("backend:diploma-batch", args=[grouped.pk])
        self.assertEqual(
            self.client.post(url, {"action": "course", "course_number": self.diploma.course_number}).status_code, 302
        )
        self.assertEqual(grouped.diplomas.count(), 2)
        self.client.force_login(self.parent)
        self.assertEqual(
            self.client.post(url, {"action": "course", "course_number": self.diploma.course_number}).status_code, 302
        )
        self.assertEqual(grouped.diplomas.count(), 2)
        self.client.force_login(self.manager)
        self.assertContains(self.client.get(url), "Cette création regroupe 2 cours")
        response = self.client.post(url, {"action": "course", "course_number": self.diploma.course_number})
        self.assertRedirects(response, url)
        self.assertEqual(
            list(grouped.diplomas.values_list("source_registration_id", flat=True)), [self.registration.pk]
        )
        other_diploma.refresh_from_db()
        separated = other_diploma.batch
        self.assertNotEqual(separated.pk, grouped.pk)
        self.assertEqual(separated.message, grouped.message)
        self.assertEqual(separated.subject, grouped.subject)
        self.assertEqual(bytes(separated.supplements.get().content), bytes(grouped.supplements.get().content))
        self.assertEqual(other_diploma.events.filter(action="edited").get().batch_id, separated.pk)
        response = self.client.get(url)
        self.assertEqual(len(response.context["diplomas"]), 1)
        self.assertEqual(response.context["diplomas"][0].source_registration_id, self.registration.pk)
        count = DiplomaBatch.objects.count()
        self.client.post(url, {"action": "course", "course_number": self.diploma.course_number})
        self.assertEqual(DiplomaBatch.objects.count(), count)

    def test_course_separation_rejects_published_or_generated_batches_and_invalid_course(self):
        for status in ("generating", "queued"):
            DiplomaBatch.objects.filter(pk=self.batch.pk).update(status=status)
            with self.assertRaises(ValueError):
                separate_draft_courses(self.batch.pk, self.diploma.course_number, self.manager)
        DiplomaBatch.objects.filter(pk=self.batch.pk).update(status="draft")
        with self.assertRaises(ValueError):
            separate_draft_courses(self.batch.pk, "unknown", self.manager)
        Diploma.objects.filter(pk=self.diploma.pk).update(published_at=timezone.now())
        with self.assertRaises(ValueError):
            separate_draft_courses(self.batch.pk, self.diploma.course_number, self.manager)

        self.assertEqual(self.batch.diplomas.count(), 1)
        Diploma.objects.filter(pk=self.diploma.pk).update(published_at=None)
        DiplomaBatch.objects.filter(pk=self.batch.pk).update(source_schema="other_period")
        with self.assertRaises(ValueError):
            separate_draft_courses(self.batch.pk, self.diploma.course_number, self.manager)

    def test_resume_separates_ready_and_failed_unsent_groups_by_course(self):
        other_course = CourseFactory()
        RegistrationFactory(course=other_course)
        courses = type(self.course).objects.filter(pk__in=[self.course.pk, other_course.pk])
        self.client.force_login(self.manager)
        for status in ("ready", "failed"):
            with self.subTest(status=status):
                batch = create_batch({**self.data, "courses": courses}, self.manager)
                DiplomaBatch.objects.filter(pk=batch.pk).update(status=status, print_pdf=b"%PDF-all-courses")
                batch.diplomas.update(pdf=b"%PDF-child")
                response = self.client.get(reverse("backend:diploma-list"))
                row = next(c for c in response.context["courses"] if c["number"] == self.course.number)
                self.assertTrue(row["current"]["can_resume"])
                url = reverse("backend:diploma-batch", args=[batch.pk])
                response = self.client.post(url, {"action": "course", "course_number": self.course.number})
                self.assertRedirects(response, url)
                batch.refresh_from_db()
                self.assertEqual(batch.status, "draft")
                self.assertIsNone(batch.print_pdf)
                self.assertEqual(list(batch.diplomas.values_list("course_number", flat=True)), [self.course.number])
                self.assertEqual(bytes(batch.diplomas.get().pdf), b"%PDF-child")

    def test_course_scoped_archive_never_displays_other_course_children_or_group_actions(self):
        other_course = CourseFactory()
        RegistrationFactory(course=other_course)
        courses = type(self.course).objects.filter(pk__in=[self.course.pk, other_course.pk])
        batch = create_batch({**self.data, "courses": courses}, self.manager)
        batch.diplomas.update(mail_status="sent", sent_at=timezone.now(), published_at=timezone.now())
        other_diploma = batch.diplomas.exclude(source_registration_id=self.registration.pk).get()
        DiplomaEvent.objects.create(batch=batch, diploma=other_diploma, action="mail_sent")
        self.client.force_login(self.manager)
        url = reverse("backend:diploma-batch", args=[batch.pk])
        response = self.client.get(url, {"course": self.course.number})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([d.source_registration_id for d in response.context["diplomas"]], [self.registration.pk])
        self.assertNotContains(response, "Cette création regroupe")
        self.assertNotContains(response, "data-diploma-actions")
        self.assertFalse(response.context["can_resume_course"])
        self.assertFalse(any(event.diploma_id == other_diploma.pk for event in response.context["events"]))
        self.assertEqual(self.client.get(url, {"course": "unknown"}).status_code, 404)

    def test_creation_of_multiple_courses_makes_independent_diplomas(self):
        other_course = CourseFactory()
        other_registration = RegistrationFactory(course=other_course)
        self.client.force_login(self.manager)
        data = {
            **self.data,
            "courses": [self.course.pk, other_course.pk],
            "final_levels": ["A 1A", "__empty__"],
            "supplement": SimpleUploadedFile("infos.pdf", sample_pdf(), content_type="application/pdf"),
        }
        response = self.client.post(reverse("backend:diploma-create"), data)
        self.assertRedirects(response, reverse("backend:diploma-list"))
        batches = DiplomaBatch.objects.filter(created_by=self.manager).exclude(pk=self.batch.pk)
        self.assertEqual(batches.count(), 2)
        rosters = []
        for batch in batches:
            rosters.append(set(batch.diplomas.values_list("source_registration_id", flat=True)))
            self.assertTrue(bytes(batch.supplements.get().content).startswith(b"%PDF-"))
        self.assertIn({self.registration.pk}, rosters)
        self.assertIn({other_registration.pk}, rosters)

    def test_diploma_list_groups_preparations_by_course_in_current_period(self):
        self.client.force_login(self.manager)
        other = create_batch(self.data, self.manager)
        sent_at = timezone.now()
        Diploma.objects.filter(pk=self.diploma.pk).update(mail_status="sent", sent_at=sent_at)
        url = reverse("backend:diploma-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Diplômes par cours")
        self.assertNotContains(response, "Archives de toutes les saisons")
        courses = response.context["courses"]
        self.assertEqual(len(courses), 1)
        self.assertEqual(courses[0]["number"], self.diploma.course_number)
        self.assertEqual(len(courses[0]["preparations"]), 2)
        self.assertEqual(courses[0]["current"]["batch_id"], other.pk)
        self.assertEqual(courses[0]["history"][0]["batch_id"], self.batch.pk)
        self.assertContains(response, "Reprendre les diplômes")
        self.assertContains(response, "Brouillon · aucun email envoyé")
        self.assertContains(response, "Anciennes créations de diplômes (1)")
        self.assertEqual(courses[0]["last_sent"], sent_at)
        self.assertContains(response, self.detail_url)
        DiplomaBatch.objects.filter(pk=other.pk).update(source_schema="another_period")
        response = self.client.get(url)
        self.assertEqual(len(response.context["courses"][0]["preparations"]), 1)
        self.assertNotContains(response, reverse("backend:diploma-batch", args=[other.pk]))
        DiplomaBatch.objects.filter(pk=self.batch.pk).update(source_schema="another_period")
        response = self.client.get(url)
        self.assertContains(response, "Aucun diplôme préparé pour cette période.")

    def test_course_mail_history_warns_on_new_preparation_and_is_visible_on_course(self):
        self.client.force_login(self.manager)
        sent_at = timezone.now()
        Diploma.objects.filter(pk=self.diploma.pk).update(mail_status="sent", sent_at=sent_at)
        new_batch = create_batch(self.data, self.manager)
        response = self.client.get(reverse("backend:diploma-batch", args=[new_batch.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Des diplômes ont déjà été envoyés pour ces cours.")
        history = response.context["course_mail_history"]
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["sent_count"], 1)
        self.assertEqual(history[0]["last_sent"], sent_at)
        self.assertEqual(history[0]["batch_id"], self.batch.pk)
        response = self.client.get(self.course.get_backend_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Envois précédents par cours")

    def test_course_mail_history_ignores_other_periods_unsent_and_failed_mail(self):
        self.assertEqual(course_mail_history(self.batch.source_schema, [self.diploma.course_number]), [])
        Diploma.objects.filter(pk=self.diploma.pk).update(mail_status="failed", sent_at=timezone.now())
        self.assertEqual(course_mail_history(self.batch.source_schema, [self.diploma.course_number]), [])
        Diploma.objects.filter(pk=self.diploma.pk).update(mail_status="sent")
        self.assertEqual(course_mail_history("other_period", [self.diploma.course_number]), [])
        self.assertEqual(course_mail_history(self.batch.source_schema, ["other_course"]), [])

    def test_instructor_is_only_first_name_from_latest_session(self):
        self.course.sessions.all().delete()
        previous = FamilyUserFactory(first_name="Ancien", last_name="Moniteur")
        latest = FamilyUserFactory(first_name="François", last_name="Iff")
        self.course.instructors.add(previous)
        # Create the older session last to verify ordering by date, not creation.
        SessionFactory(course=self.course, date=date(2026, 2, 7), instructor=latest)
        SessionFactory(course=self.course, date=date(2026, 1, 31), instructor=previous)
        batch = create_batch(self.data, self.manager)
        self.assertEqual(batch.diplomas.get().instructors, "François")

    def test_no_fallback_when_latest_session_has_no_instructor(self):
        self.course.sessions.all().delete()
        previous = FamilyUserFactory(first_name="Ancien")
        self.course.instructors.add(previous)
        SessionFactory(course=self.course, date=date(2026, 1, 31), instructor=previous)
        SessionFactory(course=self.course, date=date(2026, 2, 7), instructor=None)
        batch = create_batch(self.data, self.manager)
        self.assertEqual(batch.diplomas.get().instructors, "")

    def test_no_instructor_when_course_has_no_sessions(self):
        self.course.sessions.all().delete()
        self.course.instructors.add(FamilyUserFactory())
        batch = create_batch(self.data, self.manager)
        self.assertEqual(batch.diplomas.get().instructors, "")

    def test_creation_filters_final_levels_and_selects_all_initially(self):
        absent = RegistrationFactory(course=self.course)
        empty = RegistrationFactory(course=self.course)
        ChildActivityLevel.objects.create(activity=self.course.activity, child=absent.child, after_level="ABS")
        self.client.force_login(self.manager)
        url = reverse("backend:diploma-create")
        response = self.client.get(url, {"c": self.course.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.context["form"].initial["final_levels"]), {"A 1A", "ABS", "__empty__"})
        self.assertContains(response, "Sans niveau (1)")
        data = {**self.data, "courses": [self.course.pk], "final_levels": ["A 1A"]}
        data.pop("supplement")
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        batch = self.client.get(response.url).context["batch"]
        self.assertEqual(list(batch.diplomas.values_list("source_registration_id", flat=True)), [self.registration.pk])
        data["final_levels"] = ["__empty__"]
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        batch = self.client.get(response.url).context["batch"]
        self.assertEqual(list(batch.diplomas.values_list("source_registration_id", flat=True)), [empty.pk])

    def test_creation_requires_explicit_level_selection(self):
        data = {**self.data, "courses": [self.course.pk], "final_levels": []}
        form = BatchForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn("final_levels", form.errors)
        data["final_levels"] = ["ABS"]
        self.assertFalse(BatchForm(data).is_valid())

    def test_status_poll_permissions_and_busy_page(self):
        url = reverse("backend:diploma-status", args=[self.batch.pk])
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.parent)
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.manager)
        for status in ("queued", "generating", "ready", "failed"):
            DiplomaBatch.objects.filter(pk=self.batch.pk).update(status=status)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"status": status})
            self.assertEqual(response["Cache-Control"], "private, no-store")
        DiplomaBatch.objects.filter(pk=self.batch.pk).update(status="queued")
        response = self.client.get(self.detail_url + "?download=1")
        self.assertContains(response, "Génération des diplômes, restez sur cette page")
        self.assertContains(response, url)
        self.assertContains(response, "backend/js/diplomas.js")
        self.assertNotContains(response, "window.location.reload()")
        with override_settings(KEPCHUP_DIPLOMAS=False):
            self.assertEqual(self.client.get(url).status_code, 404)

    def test_renderer_embeds_font_dependencies(self):
        def write_pdf(renderer, path):
            from pathlib import Path

            self.assertTrue(renderer.context["label_font"])
            self.assertTrue(renderer.context["text_font"])
            self.assertEqual(len(renderer.context["horizontal_stars"]), 65)
            Path(path).write_bytes(b"%PDF-test")

        with patch.object(DiplomaRenderer, "render_to_pdf", autospec=True, side_effect=write_pdf):
            self.assertEqual(render_diplomas(self.batch, [self.diploma]), b"%PDF-test")

    def test_renderer_selects_deployment_palette(self):
        def write_pdf(renderer, path):
            from pathlib import Path

            self.assertEqual(renderer.context["montreux_style"], _expected)
            html = renderer.get_content(renderer.get_message_template())
            self.assertEqual("body, td { color: #252525; }" in html, _expected)
            self.assertEqual(".stars { color: #b2cd49; }" in html, _expected)
            Path(path).write_bytes(b"%PDF-test")

        for style, _expected in (("montreux", True), ("classic", False)):
            with self.subTest(style=style), override_settings(KEPCHUP_DIPLOMA_STYLE=style):
                with patch.object(DiplomaRenderer, "render_to_pdf", autospec=True, side_effect=write_pdf):
                    self.assertEqual(render_diplomas(self.batch, [self.diploma]), b"%PDF-test")

    @patch("diplomas.tasks.sync_playwright")
    @patch("diplomas.tasks.DiplomaRenderer.get_content", return_value="<html>Diplôme</html>")
    def test_renderer_uses_local_chromium(self, get_content, playwright):
        renderer = DiplomaRenderer({})
        browser = playwright.return_value.__enter__.return_value.chromium.launch.return_value
        page = browser.new_page.return_value
        renderer.render_to_pdf("diplomas.pdf")
        page.set_content.assert_called_once_with(get_content.return_value, wait_until="networkidle")
        page.evaluate.assert_called_once_with("document.fonts.ready")
        page.pdf.assert_called_once_with(path="diplomas.pdf", print_background=True, prefer_css_page_size=True)
        browser.close.assert_called_once()

    def test_generation_merges_individual_pages_in_diploma_order(self):
        second = Diploma.objects.get(pk=self.diploma.pk)
        second.pk = None
        second.source_registration_id += 100000
        second.last_name = "ZZZ"
        second.save()
        ordered = list(self.batch.diplomas.all())
        contents = [sample_pdf(400), sample_pdf(600)]
        DiplomaBatch.objects.filter(pk=self.batch.pk).update(status="queued")
        with patch("diplomas.tasks.render_diplomas", side_effect=contents) as renderer:
            generate_batch.run(str(self.batch.pk))
        self.assertEqual(renderer.call_count, 2)
        for call, diploma, content in zip(renderer.call_args_list, ordered, contents):
            self.assertEqual(call.args[1], [diploma])
            diploma.refresh_from_db()
            self.assertEqual(bytes(diploma.pdf), content)
        self.batch.refresh_from_db()
        pages = PdfReader(BytesIO(bytes(self.batch.print_pdf))).pages
        self.assertEqual([float(page.mediabox.width) for page in pages], [400, 600])

    def test_missing_text_picks_up_level_without_overwriting_manual_text(self):
        self.client.force_login(self.manager)
        Diploma.objects.filter(pk=self.diploma.pk).update(evaluation="", level="")
        response = self.client.get(self.detail_url)
        self.assertContains(response, "Ski alpin, niveau 1, à améliorer")
        self.diploma.refresh_from_db()
        self.assertEqual(self.diploma.level, "A 1A")
        self.assertEqual(self.diploma.evaluation, "Ski alpin, niveau 1, à améliorer")
        ChildActivityLevel.objects.filter(child=self.registration.child).update(after_level="A 2A")
        self.client.get(self.detail_url)
        self.diploma.refresh_from_db()
        self.assertEqual(self.diploma.level, "A 1A")
        self.assertEqual(self.diploma.events.filter(action="edited").count(), 1)

    def test_missing_text_is_not_filled_from_other_period_or_for_ready_batch(self):
        self.client.force_login(self.manager)
        Diploma.objects.filter(pk=self.diploma.pk).update(evaluation="", level="")
        DiplomaBatch.objects.filter(pk=self.batch.pk).update(source_schema="other_period")
        self.client.get(self.detail_url)
        self.diploma.refresh_from_db()
        self.assertEqual(self.diploma.evaluation, "")
        DiplomaBatch.objects.filter(pk=self.batch.pk).update(source_schema=connection.schema_name, status="ready")
        self.client.get(self.detail_url)
        self.diploma.refresh_from_db()
        self.assertEqual(self.diploma.evaluation, "")

    def test_preview_permissions_and_no_side_effects(self):
        url = reverse("backend:diploma-preview", args=[self.diploma.pk])
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.parent)
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.manager)
        with patch("diplomas.views.render_diplomas", return_value=b"%PDF-preview") as render:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, b"%PDF-preview")
            self.assertTrue(response["Content-Disposition"].startswith("inline;"))
            self.assertEqual(response["Cache-Control"], "private, no-store")
            render.assert_called_once()
        self.diploma.refresh_from_db()
        self.batch.refresh_from_db()
        self.assertIsNone(self.diploma.pdf)
        self.assertIsNone(self.diploma.published_at)
        self.assertEqual(self.diploma.mail_status, "pending")
        self.assertEqual(self.batch.status, "draft")
        self.ready()
        with patch("diplomas.views.render_diplomas") as render:
            self.assertEqual(self.client.get(url).content, b"%PDF-child")
            render.assert_not_called()
        with override_settings(KEPCHUP_DIPLOMAS=False):
            self.assertEqual(self.client.get(url).status_code, 404)

    def test_preview_failure_has_retry_and_return_links(self):
        self.client.force_login(self.manager)
        url = reverse("backend:diploma-preview", args=[self.diploma.pk])
        with patch("diplomas.views.render_diplomas", side_effect=RuntimeError("PDF unavailable")):
            response = self.client.get(url)
        self.assertContains(response, "Réessayer", status_code=503)
        self.assertContains(response, self.detail_url, status_code=503)

    def setUp(self):
        super().setUp()
        settings_override = override_settings(KEPCHUP_DIPLOMAS=True, KEPCHUP_DIPLOMA_LOGO="")
        settings_override.enable()
        self.addCleanup(settings_override.disable)
        self.manager = FamilyUserFactory(is_manager=True)
        self.parent = FamilyUserFactory()
        self.course = CourseFactory()
        self.registration = RegistrationFactory(course=self.course, child__family=self.parent)
        ChildActivityLevel.objects.create(
            activity=self.course.activity, child=self.registration.child, after_level="A 1A"
        )
        self.data = {
            "courses": type(self.course).objects.filter(pk=self.course.pk),
            "season": "Hiver 2026",
            "issued_on": date(2026, 2, 7),
            "place": "Les Diablerets",
            "subject": "Diplôme 2026",
            "message": "Bonjour, voici le diplôme.",
            "supplement": None,
        }
        self.batch = create_batch(self.data, self.manager)
        self.diploma = self.batch.diplomas.get()
        self.detail_url = reverse("backend:diploma-batch", args=[self.batch.pk])
        self.download_url = reverse("profiles:diploma-download", args=[self.diploma.pk])
        self.confirmation_url = reverse("backend:diploma-send-confirmation", args=[self.batch.pk])

    def tearDown(self):
        # Shared tables outlive TenantTestCase's disposable schema.
        batches = DiplomaBatch.objects.filter(created_by=self.manager)
        DiplomaEvent.objects.filter(batch__in=batches).delete()
        Diploma.objects.filter(batch__in=batches).delete()
        batches.delete()
        super().tearDown()

    def confirm_send(self):
        response = self.client.get(self.confirmation_url)
        return self.client.post(
            self.confirmation_url, {"action": "send", "confirmation_token": response.context["confirmation_token"]}
        )

    def ready(self):
        DiplomaBatch.objects.filter(pk=self.batch.pk).update(status="ready", print_pdf=b"%PDF-print")
        Diploma.objects.filter(pk=self.diploma.pk).update(pdf=b"%PDF-child")

    def test_snapshot_survives_child_and_period(self):
        first_name = self.registration.child.first_name
        self.registration.child.delete()
        with schema_context("public"):
            diploma = Diploma.objects.get(pk=self.diploma.pk)
            self.assertEqual(diploma.first_name, first_name)
            self.assertEqual(diploma.parent_id, self.parent.pk)
            self.assertEqual(diploma.level, "A 1A")
            self.assertEqual(diploma.batch.season, "Hiver 2026")
        self.assertEqual(self.batch.source_schema, connection.schema_name)

    def test_generation_is_idempotent_and_logged(self):
        DiplomaBatch.objects.filter(pk=self.batch.pk).update(status="queued")
        content = sample_pdf()
        with patch("diplomas.tasks.render_diplomas", return_value=content) as renderer:
            generate_batch.run(str(self.batch.pk))
            generate_batch.run(str(self.batch.pk))
        self.assertEqual(renderer.call_count, 1)
        self.batch.refresh_from_db()
        self.diploma.refresh_from_db()
        self.assertEqual(self.batch.status, "ready")
        self.assertEqual(bytes(self.diploma.pdf), content)
        self.assertEqual(len(PdfReader(BytesIO(bytes(self.batch.print_pdf))).pages), 1)
        self.assertIsNone(self.diploma.published_at)
        self.assertTrue(self.batch.events.filter(action="generated", diploma=self.diploma).exists())

    def test_generation_failure_is_logged(self):
        DiplomaBatch.objects.filter(pk=self.batch.pk).update(status="queued")
        with patch("diplomas.tasks.render_diplomas", side_effect=ValueError("Service PDF indisponible")):
            with self.assertRaises(ValueError):
                generate_batch.run(str(self.batch.pk))
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.status, "failed")
        self.assertTrue(self.batch.events.filter(action="generation_failed").exists())

    def test_family_access_and_archive_without_current_children(self):
        self.ready()
        self.client.force_login(self.parent)
        self.assertEqual(self.client.get(self.download_url).status_code, 404)
        Diploma.objects.filter(pk=self.diploma.pk).update(published_at=timezone.now())
        self.registration.child.delete()
        response = self.client.get(reverse("profiles:diplomas"))
        self.assertContains(response, self.diploma.first_name)
        self.assertContains(response, "Hiver 2026")
        response = self.client.get(self.download_url)
        self.assertEqual(response.content, b"%PDF-child")
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.client.force_login(FamilyUserFactory())
        self.assertEqual(self.client.get(self.download_url).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(self.download_url).status_code, 302)
        self.assertEqual(self.client.get(reverse("profiles:diplomas")).status_code, 302)

    def test_send_publishes_once_and_attaches_supplements(self):
        self.ready()
        self.batch.supplements.create(name="niveaux.pdf", content=b"%PDF-levels")
        send_batch.run(str(self.batch.pk))
        send_batch.run(str(self.batch.pk))
        send_batch.run(str(self.batch.pk))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.parent.email])
        self.assertEqual(mail.outbox[0].body, self.batch.message)
        self.assertEqual(len(mail.outbox[0].attachments), 2)
        self.diploma.refresh_from_db()
        self.assertEqual(self.diploma.mail_status, "sent")
        self.assertEqual(self.diploma.recipient, self.parent.email)
        self.assertEqual(self.diploma.events.filter(action="mail_sent").count(), 1)

    def test_image_supplement_is_sent_unchanged_with_its_mime_type(self):
        self.ready()
        content = b"\xff\xd8\xff\xe0image attachment"
        self.batch.supplements.create(name="niveaux.jpeg", content=content)
        send_batch.run(str(self.batch.pk))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(("niveaux.jpeg", content, "image/jpeg"), mail.outbox[0].attachments)
        attachment = mail.outbox[0].message().get_payload()[-1]
        self.assertEqual(attachment.get_content_type(), "image/jpeg")
        self.assertEqual(attachment.get_payload(decode=True), content)

    def test_image_supplement_upload_creates_batch(self):
        self.client.force_login(self.manager)
        data = {
            **self.data,
            "courses": [self.course.pk],
            "issued_on": "2026-02-07",
            "final_levels": ["A 1A"],
            "supplement": SimpleUploadedFile("niveaux.jpg", b"\xff\xd8\xff\xe0image"),
        }
        response = self.client.post(reverse("backend:diploma-create"), data)
        self.assertEqual(response.status_code, 302)
        response = self.client.get(response.url)
        self.assertEqual(response.status_code, 200)
        supplement = response.context["batch"].supplements.get()
        self.assertEqual(supplement.name, "niveaux.jpg")
        self.assertEqual(bytes(supplement.content), b"\xff\xd8\xff\xe0image")

    def test_supplement_accepts_image_formats_and_rewinds_upload(self):
        for extension in ("jpg", "jpeg", "png", "gif", "webp", "tiff", "svg", "bmp"):
            with self.subTest(extension=extension):
                upload = SimpleUploadedFile(f"niveaux.{extension}", b"image attachment")
                self.assertIs(validate_supplement(upload), upload)
                self.assertEqual(upload.read(), b"image attachment")

    def test_supplement_rejects_other_files_and_oversized_images(self):
        from django.core.exceptions import ValidationError

        for upload in (
            SimpleUploadedFile("niveaux.txt", b"text"),
            SimpleUploadedFile("niveaux.pdf", b"not a PDF"),
            SimpleUploadedFile("niveaux.jpg", b"x" * (10 * 1024 * 1024 + 1)),
        ):
            with self.subTest(name=upload.name), self.assertRaises(ValidationError):
                validate_supplement(upload)

    def test_send_failure_is_not_automatically_retried(self):
        self.ready()
        Diploma.objects.filter(pk=self.diploma.pk).update(published_at=timezone.now())
        with patch("diplomas.tasks.EmailMessage.send", side_effect=RuntimeError("SMTP indisponible")) as send:
            send_batch.run(str(self.batch.pk))
            send_batch.run(str(self.batch.pk))
        self.assertEqual(send.call_count, 1)
        self.diploma.refresh_from_db()
        self.assertEqual(self.diploma.mail_status, "failed")
        self.assertTrue(self.diploma.events.filter(action="mail_failed").exists())

    def test_batch_sends_directly_with_reviewed_count_and_token(self):
        self.client.force_login(self.manager)
        response = self.client.get(self.detail_url)
        self.assertContains(response, "1 email à envoyer")
        self.assertContains(response, "Envoyer 1 email aux familles")
        self.assertNotContains(response, "Vérifier et confirmer l’envoi")
        self.assertEqual(response["Cache-Control"], "private, no-store")
        with patch("diplomas.views.generate_batch.delay") as generate:
            with self.captureOnCommitCallbacks(execute=True):
                result = self.client.post(
                    self.detail_url, {"action": "send", "confirmation_token": response.context["confirmation_token"]}
                )
        self.assertRedirects(result, self.detail_url, fetch_redirect_response=False)
        generate.assert_called_once()

    def test_batch_collapses_complete_diplomas_and_shows_family_mail_preview(self):
        self.client.force_login(self.manager)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<details class="diploma-review">')
        self.assertContains(response, 'class="instructor-mail-card"')
        self.assertContains(response, self.parent.email)
        self.assertContains(response, self.batch.subject)
        self.assertContains(response, reverse("backend:diploma-preview", args=[self.diploma.pk]))
        self.assertContains(response, 'target="_blank" rel="noopener"')
        self.assertNotContains(response, 'class="well"')

    def test_batch_opens_diplomas_when_text_needs_completing(self):
        self.client.force_login(self.manager)
        ChildActivityLevel.objects.filter(child=self.registration.child).delete()
        Diploma.objects.filter(pk=self.diploma.pk).update(evaluation="", level="")
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<details class="diploma-review" open>')
        self.assertContains(response, "1 texte à compléter")
        self.assertContains(response, "avant de continuer.")
        self.assertNotContains(response, 'id="diploma-message"')
        self.assertNotContains(response, "data-diploma-actions")
        Diploma.objects.filter(pk=self.diploma.pk).update(evaluation="Niveau acquis")
        response = self.client.get(self.detail_url)
        self.assertContains(response, 'id="diploma-message"')
        self.assertContains(response, "data-diploma-actions")

    def test_backend_pages_permissions_and_draft_edit(self):
        urls = [
            reverse("backend:diploma-list"),
            reverse("backend:diploma-create"),
            self.detail_url,
            reverse("backend:diploma-edit", args=[self.diploma.pk]),
        ]
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.parent)
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.manager)
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 200)
        response = self.client.get(self.detail_url)
        self.assertContains(response, "backend/css/diplomas.css?v=7")
        self.assertContains(response, 'class="table diploma-children"')
        response = self.client.get(urls[-1])
        self.assertNotContains(response, 'name="level"')
        self.assertContains(response, 'name="evaluation"')
        response = self.client.post(
            urls[-1],
            {
                "first_name": "Mariia",
                "last_name": "Bilytska",
                "level": "A 1A",
                "evaluation": "Ski alpin, niveau 1, à améliorer",
                "place": "Les Diablerets",
                "instructors": "Romain C.",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.diploma.refresh_from_db()
        self.assertEqual(self.diploma.evaluation, "Ski alpin, niveau 1, à améliorer")
        with override_settings(KEPCHUP_DIPLOMAS=False):
            self.assertEqual(self.client.get(self.detail_url).status_code, 404)

    def test_download_prepares_without_publishing_and_send_prepares_and_publishes(self):
        self.client.force_login(self.manager)
        response = self.client.get(self.detail_url)
        self.assertNotContains(response, "Non envoyé")
        self.assertNotContains(response, "Marquer comme imprimés")
        with patch("diplomas.views.generate_batch.delay") as generate:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(self.detail_url, {"action": "download"})
            generate.assert_called_once_with(str(self.batch.pk), send_after=False)
        self.assertEqual(response.url, self.detail_url + "?download=1")
        with patch("diplomas.tasks.render_diplomas", return_value=sample_pdf()):
            generate_batch.run(str(self.batch.pk))
        self.diploma.refresh_from_db()
        self.assertIsNone(self.diploma.published_at)
        response = self.client.get(self.detail_url + "?download=1")
        self.assertContains(response, "<iframe", html=False)
        with patch("diplomas.views.send_batch.delay") as send:
            with self.captureOnCommitCallbacks(execute=True):
                self.confirm_send()
            send.assert_called_once_with(str(self.batch.pk))

    def test_send_from_draft_generates_publishes_and_sends(self):
        self.client.force_login(self.manager)
        with patch("diplomas.views.generate_batch.delay") as generate:
            with self.captureOnCommitCallbacks(execute=True):
                self.confirm_send()
            generate.assert_called_once_with(str(self.batch.pk), send_after=True)
        with patch("diplomas.tasks.render_diplomas", return_value=sample_pdf()):
            generate_batch.run(str(self.batch.pk), send_after=True)
        self.diploma.refresh_from_db()
        self.assertIsNotNone(self.diploma.published_at)
        self.assertEqual(self.diploma.mail_status, "sent")
        self.assertEqual(len(mail.outbox), 1)

    def test_create_form_and_uploaded_pdf_validation(self):
        self.client.force_login(self.manager)
        data = {**self.data, "courses": [self.course.pk], "issued_on": "2026-02-07", "final_levels": ["A 1A"]}
        data.pop("supplement")
        response = self.client.post(reverse("backend:diploma-create"), data)
        self.assertEqual(response.status_code, 302)
        form = BatchForm(data, {"supplement": SimpleUploadedFile("bad.pdf", b"not a PDF")})
        self.assertFalse(form.is_valid())
        self.assertIn("supplement", form.errors)

    def test_supplement_is_only_uploaded_on_creation(self):
        self.client.force_login(self.manager)
        data = {
            **self.data,
            "courses": [self.course.pk],
            "issued_on": "2026-02-07",
            "supplement": SimpleUploadedFile("niveaux.pdf", b"%PDF-levels"),
            "final_levels": ["A 1A"],
        }
        response = self.client.post(reverse("backend:diploma-create"), data)
        self.assertEqual(response.status_code, 302)
        detail_url = response.url
        response = self.client.get(detail_url)
        self.assertContains(response, "niveaux.pdf")
        self.assertNotContains(response, 'type="file"')
        batch = response.context["batch"]
        self.assertEqual(bytes(batch.supplements.get().content), b"%PDF-levels")
        response = self.client.post(
            detail_url,
            {"action": "supplement", "supplement": SimpleUploadedFile("autre.pdf", b"%PDF-other")},
            follow=True,
        )
        self.assertContains(response, "Cette action n’est pas disponible")
        self.assertEqual(batch.supplements.count(), 1)

    @override_settings(KEPCHUP_REGISTRATION_LEVELS=True)
    def test_missing_evaluation_blocks_generation_and_queue_failure_is_logged(self):
        self.client.force_login(self.manager)
        ChildActivityLevel.objects.filter(child=self.registration.child).update(after_level="")
        Diploma.objects.filter(pk=self.diploma.pk).update(evaluation="")
        with patch("diplomas.views.generate_batch.delay") as generate:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(self.detail_url, {"action": "download"}, follow=True)
            generate.assert_not_called()
        self.assertContains(response, "Le texte à imprimer manque")
        self.assertContains(response, "cliquez sur « Modifier »")
        self.assertContains(response, "Texte sur le diplôme")
        self.assertContains(response, reverse("backend:child-absences", kwargs={"child": self.registration.child_id}))
        DiplomaBatch.objects.filter(pk=self.batch.pk).update(source_schema="another_period")
        response = self.client.get(self.detail_url)
        self.assertNotContains(response, "Saisir le niveau après cours")
        Diploma.objects.filter(pk=self.diploma.pk).update(evaluation="A 1A")
        with patch("diplomas.views.generate_batch.delay", side_effect=RuntimeError("Broker indisponible")):
            with self.captureOnCommitCallbacks(execute=True):
                self.client.post(self.detail_url, {"action": "download"})
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.status, "failed")
        self.assertTrue(self.batch.events.filter(action="queue_failed").exists())

    def test_pdf_format_does_not_change_other_exports(self):
        self.assertEqual(PDFRenderer.page_format, "A4")
        self.assertEqual(DiplomaRenderer.page_format, "A5")
        self.assertTrue(DiplomaRenderer.is_landscape)

    def test_merge_accounts_transfers_archived_diplomas(self):
        winner = FamilyUserFactory()
        MergeAccounts()._merge_one(winner, self.parent, "default", dry_run=False)
        self.diploma.refresh_from_db()
        self.assertEqual(self.diploma.parent_id, winner.pk)
        self.assertEqual(self.diploma.level, "A 1A")

    def test_confirmation_counts_emails_per_diploma_not_per_family(self):
        for index in range(308):
            Diploma.objects.create(
                batch=self.batch,
                parent=self.parent,
                source_registration_id=self.registration.pk + index + 1,
                first_name=f"Enfant {index}",
                last_name="Test",
                activity="Ski",
                course_number="1",
                evaluation="Niveau acquis",
                place="Les Diablerets",
                instructors="Romain",
                mail_status={305: "sent", 306: "failed", 307: "sending"}.get(index, "pending"),
            )
        self.client.force_login(self.manager)
        with patch("diplomas.views.generate_batch.delay") as generate, patch(
            "diplomas.views.send_batch.delay"
        ) as send:
            response = self.client.get(self.confirmation_url)
        self.assertContains(response, "306 emails prévus", status_code=200)
        self.assertContains(response, "Envoyer les 306 emails aux familles")
        self.assertEqual(response.context["mail_counts"], {"pending": 306, "sent": 1, "failed": 1, "sending": 1})
        generate.assert_not_called()
        send.assert_not_called()
        self.diploma.refresh_from_db()
        self.assertIsNone(self.diploma.published_at)
        self.assertIsNone(self.diploma.pdf)

    def test_old_send_button_only_redirects_to_confirmation(self):
        self.client.force_login(self.manager)
        with patch("diplomas.views.generate_batch.delay") as generate, patch(
            "diplomas.views.send_batch.delay"
        ) as send:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(self.detail_url, {"action": "send"})
        self.assertRedirects(response, self.confirmation_url, fetch_redirect_response=False)
        generate.assert_not_called()
        send.assert_not_called()
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.status, "draft")

    def test_confirmation_previews_exact_subject_body_recipient_and_attachments(self):
        supplement = self.batch.supplements.create(name="Niveaux.pdf", content=sample_pdf())
        self.client.force_login(self.manager)
        response = self.client.get(self.confirmation_url)
        self.assertContains(response, self.batch.subject, status_code=200)
        self.assertContains(response, self.batch.message)
        self.assertContains(response, self.parent.email)
        self.assertContains(response, reverse("backend:diploma-preview", args=[self.diploma.pk]))
        self.assertContains(
            response, reverse("backend:diploma-supplement-preview", args=[self.batch.pk, supplement.pk])
        )
        self.assertContains(response, 'target="_blank" rel="noopener"')
        self.assertContains(response, "Modifier le mail")
        self.assertNotContains(response, "confirm(")

    def test_confirmation_cannot_be_bypassed_and_changed_mail_requires_review(self):
        self.client.force_login(self.manager)
        token = self.client.get(self.confirmation_url).context["confirmation_token"]
        with patch("diplomas.views.generate_batch.delay") as generate:
            with self.captureOnCommitCallbacks(execute=True):
                for value in ("", "tampered"):
                    response = self.client.post(self.confirmation_url, {"action": "send", "confirmation_token": value})
                    self.assertEqual(response.status_code, 400)
                DiplomaBatch.objects.filter(pk=self.batch.pk).update(message="Texte corrigé")
                response = self.client.post(self.confirmation_url, {"action": "send", "confirmation_token": token})
        self.assertContains(response, "La préparation a changé", status_code=400)
        generate.assert_not_called()
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.status, "draft")

    def test_changed_recipient_or_supplements_invalidate_confirmation(self):
        self.client.force_login(self.manager)
        token = self.client.get(self.confirmation_url).context["confirmation_token"]
        self.parent.email = "nouvelle-adresse@example.org"
        self.parent.save()
        with patch("diplomas.views.generate_batch.delay") as generate:
            with self.captureOnCommitCallbacks(execute=True):
                self.assertEqual(
                    self.client.post(
                        self.confirmation_url, {"action": "send", "confirmation_token": token}
                    ).status_code,
                    400,
                )
                token = self.client.get(self.confirmation_url).context["confirmation_token"]
                self.batch.supplements.create(name="nouveau.pdf", content=sample_pdf())
                self.assertEqual(
                    self.client.post(
                        self.confirmation_url, {"action": "send", "confirmation_token": token}
                    ).status_code,
                    400,
                )
        generate.assert_not_called()

    def test_no_pending_mail_disables_confirmation_and_does_not_resend(self):
        self.ready()
        Diploma.objects.filter(pk=self.diploma.pk).update(mail_status="sent", sent_at=timezone.now())
        self.client.force_login(self.manager)
        response = self.client.get(self.confirmation_url)
        self.assertContains(response, "Aucun email en attente", status_code=200)
        self.assertFalse(response.context["can_send"])
        with patch("diplomas.views.send_batch.delay") as send:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.confirm_send()
        self.assertEqual(response.status_code, 400)
        send.assert_not_called()
        response = self.client.get(self.detail_url)
        self.assertContains(response, "1 email(s) accepté(s) par le serveur mail")

    def test_confirmation_blocks_missing_diploma_text_and_busy_or_incomplete_batches(self):
        self.client.force_login(self.manager)
        Diploma.objects.filter(pk=self.diploma.pk).update(evaluation="")
        response = self.client.get(self.confirmation_url)
        self.assertFalse(response.context["can_send"])
        self.assertContains(response, "Le texte à imprimer manque", status_code=200)
        Diploma.objects.filter(pk=self.diploma.pk).update(evaluation="Acquis")
        for status in ("queued", "generating", "ready"):
            DiplomaBatch.objects.filter(pk=self.batch.pk).update(status=status)
            response = self.client.get(self.confirmation_url)
            self.assertFalse(response.context["can_send"])

    def test_confirmation_navigation_covers_pending_diplomas_only(self):
        other = Diploma.objects.create(
            batch=self.batch,
            parent=self.parent,
            source_registration_id=self.registration.pk + 1,
            first_name="Zoé",
            last_name="Zzz",
            activity="Ski",
            course_number="2",
            evaluation="Acquis",
            place="Les Diablerets",
            instructors="Romain",
        )
        self.client.force_login(self.manager)
        response = self.client.get(self.confirmation_url + "?number=2")
        self.assertEqual(response.context["diploma"], other)
        self.assertContains(response, "Message 2 / 2")
        Diploma.objects.filter(pk=self.diploma.pk).update(mail_status="failed")
        response = self.client.get(self.confirmation_url)
        self.assertEqual(response.context["delivery_total"], 1)
        self.assertEqual(response.context["diploma"], other)

    def test_attachment_previews_are_private_inline_and_scoped_to_batch(self):
        self.client.force_login(self.manager)
        for name, content, content_type in (
            ("Niveaux.pdf", sample_pdf(), "application/pdf"),
            ("Niveaux.png", b"\x89PNG\r\n\x1a\nimage", "image/png"),
        ):
            supplement = self.batch.supplements.create(name=name, content=content)
            url = reverse("backend:diploma-supplement-preview", args=[self.batch.pk, supplement.pk])
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Type"], content_type)
            self.assertTrue(response["Content-Disposition"].startswith("inline;"))
            self.assertEqual(response["Cache-Control"], "private, no-store")
            self.assertEqual(b"".join(response.streaming_content), content)
            other_batch = create_batch(self.data, self.manager)
            self.assertEqual(
                self.client.get(
                    reverse("backend:diploma-supplement-preview", args=[other_batch.pk, supplement.pk])
                ).status_code,
                404,
            )
        supplement = self.batch.supplements.create(name="niveaux.svg", content=b"<svg></svg>")
        response = self.client.get(reverse("backend:diploma-supplement-preview", args=[self.batch.pk, supplement.pk]))
        self.assertEqual(response["Content-Type"], "application/octet-stream")
        self.assertTrue(response["Content-Disposition"].startswith("attachment;"))

    def test_confirmation_and_supplement_preview_permissions_and_feature_flag(self):
        supplement = self.batch.supplements.create(name="Niveaux.pdf", content=sample_pdf())
        supplement_url = reverse("backend:diploma-supplement-preview", args=[self.batch.pk, supplement.pk])
        instructor = FamilyUserFactory()
        self.course.instructors.add(instructor)
        for user in (
            None,
            self.parent,
            instructor,
            FamilyUserFactory(is_restricted_manager=True),
        ):
            self.client.logout()
            if user:
                self.client.force_login(user)
            self.assertEqual(self.client.get(self.confirmation_url).status_code, 302)
            self.assertEqual(self.client.post(self.confirmation_url, {"action": "send"}).status_code, 302)
            self.assertEqual(self.client.get(supplement_url).status_code, 302)
        self.client.force_login(self.manager)
        with override_settings(KEPCHUP_DIPLOMAS=False):
            self.assertEqual(self.client.get(self.confirmation_url).status_code, 404)
            self.assertEqual(self.client.get(supplement_url).status_code, 404)

    def test_creation_form_groups_fields_and_collapses_prefilled_message(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("backend:diploma-create"), {"c": self.course.pk})
        self.assertContains(response, "Enfants concernés", status_code=200)
        self.assertContains(response, "Informations sur le diplôme")
        self.assertContains(response, "Pièce jointe complémentaire")
        self.assertContains(response, 'class="diploma-create-grid diploma-create-metadata"')
        self.assertContains(response, '<details class="diploma-create-message">')
        self.assertContains(response, 'id="div_id_final_levels"')
        self.assertContains(response, "data-level-status")
        for name in ("courses", "final_levels", "season", "issued_on", "place", "subject", "message", "supplement"):
            self.assertContains(response, f'name="{name}"')

    def test_creation_message_errors_are_visible_in_expanded_editor(self):
        self.client.force_login(self.manager)
        data = {**self.data, "courses": [self.course.pk], "final_levels": ["A 1A"], "message": ""}
        data.pop("supplement")
        response = self.client.post(reverse("backend:diploma-create"), data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("message", response.context["form"].errors)
        self.assertContains(response, '<details class="diploma-create-message" open>')

    def test_diploma_date_displays_and_accepts_swiss_format(self):
        form = BatchForm(initial={"issued_on": date(2026, 2, 7)})
        self.assertIn('value="07.02.2026"', str(form["issued_on"]))
        self.assertEqual(form.fields["issued_on"].widget.config.options["format"], "DD.MM.YYYY")
        self.assertEqual(form.fields["issued_on"].widget.config.options["locale"], "fr")
        self.assertIn("datepicker-widget.js", str(form.media))
        data = {**self.data, "courses": [self.course.pk], "final_levels": ["A 1A"]}
        data.pop("supplement")
        for value in ("07.02.2026", "2026-02-07"):
            form = BatchForm({**data, "issued_on": value})
            self.assertTrue(form.is_valid(), form.errors)
            self.assertEqual(form.cleaned_data["issued_on"], date(2026, 2, 7))
        form = BatchForm({**data, "issued_on": "02/07/2026"})
        self.assertFalse(form.is_valid())
        self.assertIn("jj.mm.aaaa", form.errors["issued_on"][0])
