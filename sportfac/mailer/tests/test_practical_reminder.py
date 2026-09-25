from unittest.mock import patch

from dbtemplates.models import Template
from django.core import mail
from django.core.management import call_command
from django.db import connection
from django.test import override_settings
from django.urls import reverse

from activities.tests.factories import CourseFactory
from profiles.tests.factories import FamilyUserFactory
from registrations.tests.factories import RegistrationFactory
from sportfac.utils import TenantTestCase

from ..models import GenericEmail
from ..models import MailArchive
from ..practical_reminder import BODY_TEMPLATE
from ..practical_reminder import SUBJECT_TEMPLATE
from ..tasks import send_practical_reminder


class PracticalReminderTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        config = override_settings(
            KEPCHUP_PRACTICAL_REMINDER=True, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"
        )
        config.enable()
        self.addCleanup(config.disable)
        self.manager = FamilyUserFactory(is_manager=True)
        self.course = CourseFactory(group_name="16", place="Les Diablerets")
        self.registration = RegistrationFactory(course=self.course, child__bib_number="145")
        self.url = reverse("backend:courses-practical-reminder") + f"?c={self.course.pk}"

    def tearDown(self):
        MailArchive.objects.filter(template=BODY_TEMPLATE).delete()
        GenericEmail.objects.filter(body_template__name=BODY_TEMPLATE).delete()
        Template.objects.filter(name__in=[BODY_TEMPLATE, SUBJECT_TEMPLATE]).delete()
        super().tearDown()

    def install(self, **kwargs):
        call_command("install_montreux_practical_reminder", schema=connection.schema_name, **kwargs)

    def test_install_preserves_edits_and_supports_replace_and_dry_run(self):
        self.install(dry_run=True)
        self.assertFalse(GenericEmail.objects.filter(body_template__name=BODY_TEMPLATE).exists())
        self.install()
        Template.objects.filter(name=BODY_TEMPLATE).update(content="Edited")
        self.install()
        self.assertEqual(Template.objects.get(name=BODY_TEMPLATE).content, "Edited")
        self.install(replace=True)
        self.assertIn("07h40", Template.objects.get(name=BODY_TEMPLATE).content)
        self.assertEqual(GenericEmail.objects.filter(body_template__name=BODY_TEMPLATE).count(), 1)

    def test_access_preview_and_disabled_feature(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)
        self.client.force_login(self.registration.child.family)
        self.assertEqual(self.client.get(self.url).status_code, 302)
        self.client.force_login(self.manager)
        self.assertContains(self.client.get(self.url), "pas encore installé")
        self.install()
        response = self.client.get(self.url)
        self.assertContains(response, "145")
        self.assertContains(response, "Les Diablerets")
        self.assertContains(response, "07h40")
        self.assertContains(response, self.registration.child.first_name)
        self.assertContains(self.client.get(reverse("backend:courses-practical-reminder")), "Aucun enfant")
        with override_settings(KEPCHUP_PRACTICAL_REMINDER=False):
            self.assertEqual(self.client.get(self.url).status_code, 404)
            self.assertEqual(self.client.post(self.url).status_code, 404)

    def test_preview_identifies_recipient_and_preserves_selected_courses_when_browsing(self):
        from urllib.parse import urlencode

        from django.utils.html import escape

        self.install()
        other = RegistrationFactory()
        self.client.force_login(self.manager)
        params = [("c", str(self.course.pk)), ("c", str(other.course.pk))]
        url = reverse("backend:courses-practical-reminder")
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, 200)
        registration = response.context["registration"]
        self.assertContains(response, registration.child.family.email)
        self.assertContains(response, escape(registration.child.family.full_name))
        self.assertContains(response, escape(response.context["from_email"]))
        self.assertContains(response, 'class="dl-horizontal"')
        self.assertContains(response, "Message 1 / 2")
        self.assertContains(response, escape("?" + urlencode(params) + "&number=2"))
        self.assertContains(response, "Envoyer les 2 rappels aux familles")
        second = self.client.get(url, params + [("number", "2")])
        self.assertContains(second, "Message 2 / 2")
        self.assertNotEqual(second.context["registration"].pk, registration.pk)
        self.assertContains(second, escape("?" + urlencode(params) + "&number=1"))

    def test_send_is_queued_archived_and_html(self):
        self.install()
        self.client.force_login(self.manager)
        with patch("mailer.practical_reminder.send_practical_reminder.delay") as delay:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(self.url)
            self.assertEqual(response.status_code, 302)
            delay.assert_called_once()
        archive = MailArchive.objects.get(template=BODY_TEMPLATE)
        self.assertEqual(archive.status, "draft")
        GenericEmail.objects.filter(body_template__name=BODY_TEMPLATE).update(is_html=False)
        send_practical_reminder.run(archive.pk, connection.schema_name, "sender@example.org", "reply@example.org")
        send_practical_reminder.run(archive.pk, connection.schema_name, "sender@example.org", "reply@example.org")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].alternatives[0][1], "text/html")
        self.assertNotIn("{{", mail.outbox[0].alternatives[0][0])
        self.assertIn("145", mail.outbox[0].alternatives[0][0])
        self.assertTrue(archive.is_html)
        self.assertEqual(mail.outbox[0].to, [self.registration.child.family.email])
        archive.refresh_from_db()
        self.assertEqual(archive.status, "sent")

    def test_visual_editor_keeps_variables_until_preview(self):
        self.install()
        self.client.force_login(self.manager)
        mail_type = GenericEmail.objects.get(body_template__name=BODY_TEMPLATE)
        response = self.client.get(mail_type.get_absolute_url())
        self.assertContains(response, "backend/vendor/jodit/jodit.min.js")
        self.assertContains(response, "backend/vendor/jodit/jodit.min.css")
        self.assertNotContains(response, "ckeditor/ckeditor/ckeditor.js")
        content = response.context["form"]["body_text"].value()
        self.assertIn("{{ child.first_name }}", content)
        self.assertIn('{{ child.bib_number|default:"À communiquer" }}', content)
        response = self.client.post(
            mail_type.get_absolute_url(),
            {
                "subject_text": "Rappel {{ year }}",
                "body_text": content,
                "is_html": True,
            },
        )
        self.assertEqual(response.status_code, 302)
        mail_type.body_template.refresh_from_db()
        self.assertIn("{{ child.first_name }}", mail_type.body_template.content)
        preview = self.client.get(self.url)
        self.assertNotIn("{{", preview.context["body"])
        self.assertIn("145", preview.context["body"])

    def test_plain_reminder_is_previewed_and_sent_as_text(self):
        self.install()
        GenericEmail.objects.filter(body_template__name=BODY_TEMPLATE).update(is_html=False)
        Template.objects.filter(name=BODY_TEMPLATE).update(content="Bonjour {{ child.first_name }} <texte>")
        self.client.force_login(self.manager)
        response = self.client.get(self.url)
        self.assertNotContains(response, 'title="Aperçu du rappel"')
        self.assertContains(response, "&lt;texte&gt;")
        with patch("mailer.practical_reminder.send_practical_reminder.delay"):
            with self.captureOnCommitCallbacks(execute=True):
                self.client.post(self.url)
        archive = MailArchive.objects.get(template=BODY_TEMPLATE)
        GenericEmail.objects.filter(body_template__name=BODY_TEMPLATE).update(is_html=True)
        send_practical_reminder.run(archive.pk, connection.schema_name, "sender@example.org", "reply@example.org")
        self.assertFalse(archive.is_html)
        self.assertEqual(mail.outbox[0].alternatives, [])
        self.assertIn("<texte>", mail.outbox[0].body)
