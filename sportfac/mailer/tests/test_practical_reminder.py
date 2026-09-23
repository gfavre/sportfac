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
        send_practical_reminder.run(archive.pk, connection.schema_name, "sender@example.org", "reply@example.org")
        send_practical_reminder.run(archive.pk, connection.schema_name, "sender@example.org", "reply@example.org")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].content_subtype, "html")
        self.assertEqual(mail.outbox[0].to, [self.registration.child.family.email])
        archive.refresh_from_db()
        self.assertEqual(archive.status, "sent")
