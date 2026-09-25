from unittest.mock import patch

from dbtemplates.models import Template
from django.core import mail
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from mailer.forms import GenericEmailForm
from mailer.html import clean_email_html
from mailer.html import make_email
from mailer.html import template_is_html
from mailer.models import GenericEmail
from mailer.models import MailArchive
from mailer.tasks import send_mail
from profiles.tests.factories import FamilyUserFactory
from sportfac.utils import TenantTestCase


class HTMLMailTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.subject = Template.objects.create(name="test-html-subject", content="Bonjour")
        self.body = Template.objects.create(name="test-html-body", content="Texte initial")
        self.mail_type = GenericEmail.objects.create(subject_template=self.subject, body_template=self.body)

    def tearDown(self):
        self.mail_type.delete()
        self.subject.delete()
        self.body.delete()
        super().tearDown()

    def test_default_plain_and_html_lookup(self):
        self.assertFalse(self.mail_type.is_html)
        self.assertFalse(template_is_html(self.body.name))
        self.mail_type.is_html = True
        self.mail_type.save()
        self.assertTrue(template_is_html(self.body.name))
        self.assertFalse(template_is_html("missing"))

    def test_form_validates_template_and_sanitizes_only_html(self):
        data = {
            "subject_text": "Bonjour",
            "body_text": '<p>{{ child.first_name }}</p><img src="{{ logo_url }}" onerror="bad()">',
            "is_html": True,
        }
        form = GenericEmailForm(data=data, instance=self.mail_type)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIn("{{ child.first_name }}", form.cleaned_data["body_text"])
        self.assertIn("{{ logo_url }}", form.cleaned_data["body_text"])
        self.assertNotIn("onerror", form.cleaned_data["body_text"])
        data["body_text"] = "{% invalid %}"
        self.assertFalse(GenericEmailForm(data=data, instance=self.mail_type).is_valid())
        data.update(is_html=False, body_text="Bonjour <texte>\nDeuxième ligne")
        form = GenericEmailForm(data=data, instance=self.mail_type)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["body_text"], data["body_text"])
        self.body.content = '{% load i18n %}\n{% translate "Hello" %}'
        data["body_text"] = '{% translate "Hello" %}'
        form = GenericEmailForm(data=data, instance=self.mail_type)
        self.assertTrue(form.is_valid(), form.errors)

    def test_editor_permissions_and_html_save(self):
        url = self.mail_type.get_absolute_url()
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(FamilyUserFactory())
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(FamilyUserFactory(is_manager=True))
        self.assertContains(self.client.get(url), "generic-email.js")
        data = {"subject_text": "Bonjour", "is_html": True, "body_text": "<p>Bonjour {{ child.first_name }}</p>"}
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.mail_type.refresh_from_db()
        self.body.refresh_from_db()
        self.assertTrue(self.mail_type.is_html)
        self.assertIn("{{ child.first_name }}", self.body.content)

    def test_delivery_honours_snapshot_and_preserves_plain_mail(self):
        for html in (False, True):
            send_mail.run("Sujet", "<p>Bonjour</p>", "sender@example.org", ["family@example.org"], [], is_html=html)
        self.assertEqual(mail.outbox[0].body, "<p>Bonjour</p>")
        self.assertEqual(mail.outbox[0].alternatives, [])
        self.assertEqual(mail.outbox[1].body, "Bonjour")
        self.assertEqual(mail.outbox[1].alternatives, [("<p>Bonjour</p>", "text/html")])
        email = make_email(is_html=True, subject="Sujet", body="<p>Bonjour</p>")
        email.attach("test.pdf", b"%PDF", "application/pdf")
        self.assertEqual(email.message().get_content_type(), "multipart/mixed")
        self.assertIn("multipart/alternative", email.message().as_string())

    def test_generic_preview_and_enqueue_use_mail_type_format(self):
        from mailer.mixins import TemplatedEmailMixin
        from mailer.views import MailPreviewView

        class Preview(TemplatedEmailMixin, MailPreviewView):
            def create_receipt(self):
                pass

        preview = Preview()
        preview.message_template = self.body.name
        preview.subject_template = self.subject.name
        self.body.content = '<p>Bonjour</p><img onerror="bad()">'
        self.body.save()
        self.mail_type.is_html = True
        self.mail_type.save()
        self.assertTrue(preview.get_is_html())
        self.assertNotIn("onerror", preview.get_mail_body({}))
        with patch("mailer.tasks.send_mail.delay") as queued:
            preview.send_mail(FamilyUserFactory(), [], {})
        self.assertTrue(queued.call_args.kwargs["is_html"])


class HTMLSafetyTests(TenantTestCase):
    def test_sanitizer_retains_table_and_rejects_active_content(self):
        html = clean_email_html(
            '<table style="border-collapse:collapse;position:fixed"><tr><td>Texte</td></tr></table>'
            '<script>bad()</script><img src="javascript:bad()" onerror="bad()">'
        )
        self.assertIn("<table", html)
        self.assertIn("border-collapse", html)
        for unsafe in ("<script", "javascript:", "onerror", "position"):
            self.assertNotIn(unsafe, html)

    def test_preview_and_archive_cannot_escape_iframe(self):
        body = mark_safe('"><script>alert(1)</script>')
        html = render_to_string("mailer/message-preview.html", {"is_html": True, "message": body})
        self.assertIn('sandbox=""', html)
        self.assertNotIn("<script>", html)
        archive = MailArchive(messages=[body], is_html=True)
        self.assertNotIn("<script>", archive.admin_message())
        archive.is_html = False
        self.assertNotIn("<script>", archive.admin_message())
