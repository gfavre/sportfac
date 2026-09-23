from datetime import date
from unittest.mock import patch

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from django_tenants.utils import schema_context

from activities.tests.factories import CourseFactory
from mailer.pdfutils import PDFRenderer
from profiles.management.commands.merge_family_accounts import Command as MergeAccounts
from profiles.tests.factories import FamilyUserFactory
from registrations.models import ChildActivityLevel
from registrations.tests.factories import RegistrationFactory
from sportfac.utils import TenantTestCase

from .forms import BatchForm
from .models import Diploma
from .models import DiplomaBatch
from .models import DiplomaEvent
from .services import create_batch
from .tasks import DiplomaRenderer
from .tasks import generate_batch
from .tasks import render_diplomas
from .tasks import send_batch


class DiplomaTests(TenantTestCase):
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

    def test_missing_text_picks_up_level_without_overwriting_manual_text(self):
        self.client.force_login(self.manager)
        Diploma.objects.filter(pk=self.diploma.pk).update(evaluation="", level="")
        response = self.client.get(self.detail_url)
        self.assertContains(response, "A 1A")
        self.diploma.refresh_from_db()
        self.assertEqual(self.diploma.level, "A 1A")
        self.assertEqual(self.diploma.evaluation, f"{self.diploma.activity} — A 1A")
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

    def tearDown(self):
        # Shared tables outlive TenantTestCase's disposable schema.
        batches = DiplomaBatch.objects.filter(created_by=self.manager)
        DiplomaEvent.objects.filter(batch__in=batches).delete()
        Diploma.objects.filter(batch__in=batches).delete()
        batches.delete()
        super().tearDown()

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
        with patch("diplomas.tasks.render_diplomas", return_value=b"%PDF-generated") as renderer:
            generate_batch.run(str(self.batch.pk))
            generate_batch.run(str(self.batch.pk))
        self.assertEqual(renderer.call_count, 2)
        self.batch.refresh_from_db()
        self.diploma.refresh_from_db()
        self.assertEqual(self.batch.status, "ready")
        self.assertEqual(bytes(self.diploma.pdf), b"%PDF-generated")
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
        self.assertContains(response, "backend/css/diplomas.css?v=6")
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
        with patch("diplomas.tasks.render_diplomas", return_value=b"%PDF-test"):
            generate_batch.run(str(self.batch.pk))
        self.diploma.refresh_from_db()
        self.assertIsNone(self.diploma.published_at)
        response = self.client.get(self.detail_url + "?download=1")
        self.assertContains(response, "<iframe", html=False)
        with patch("diplomas.views.send_batch.delay") as send:
            with self.captureOnCommitCallbacks(execute=True):
                self.client.post(self.detail_url, {"action": "send"})
            send.assert_called_once_with(str(self.batch.pk))

    def test_send_from_draft_generates_publishes_and_sends(self):
        self.client.force_login(self.manager)
        with patch("diplomas.views.generate_batch.delay") as generate:
            with self.captureOnCommitCallbacks(execute=True):
                self.client.post(self.detail_url, {"action": "send"})
            generate.assert_called_once_with(str(self.batch.pk), send_after=True)
        with patch("diplomas.tasks.render_diplomas", return_value=b"%PDF-test"):
            generate_batch.run(str(self.batch.pk), send_after=True)
        self.diploma.refresh_from_db()
        self.assertIsNotNone(self.diploma.published_at)
        self.assertEqual(self.diploma.mail_status, "sent")
        self.assertEqual(len(mail.outbox), 1)

    def test_create_form_and_uploaded_pdf_validation(self):
        self.client.force_login(self.manager)
        data = {**self.data, "courses": [self.course.pk], "issued_on": "2026-02-07"}
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
