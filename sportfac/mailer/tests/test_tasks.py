"""Tests for mailer.tasks.send_instructors_email's KEPCHUP_ADDITIONAL_INSTRUCTOR_EMAIL_DOCUMENTS
handling: a missing document must not send a partial email, must be logged loudly (ERROR
-> a Sentry event via sentry_logging in settings/production.py), and must not leave the
task's temp directory behind. Regression coverage for a real incident: montreux.py once
referenced 'COVID_19.pdf' instead of 'pdf/COVID_19.pdf', which crashed this exact loop with
an uncaught FileNotFoundError - the mail simply never went out, with nothing but an
unhandled-exception trace to explain why.
"""
import os
import tempfile
from unittest import mock

from django.core import mail
from django.test import override_settings

from activities.tests.factories import CourseFactory
from profiles.tests.factories import FamilyUserFactory
from sportfac.utils import TenantTestCase

from .. import tasks


def _fake_render_to_pdf(output):
    with open(output, "wb") as f:
        f.write(b"%PDF-1.4 fake")


class SendInstructorsEmailAdditionalDocumentsTest(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.course = CourseFactory()
        self.instructor = FamilyUserFactory()
        self.course.instructors.add(self.instructor)

        # The two mandatory attachments (participants/mes_cours) go through the real,
        # PhantomJsCloud-backed PDFRenderer - stub them out, their content isn't what's
        # under test here. Presence list and SSF decompte are switched off so only the
        # additional-documents loop is exercised beyond those two.
        for target in ("mailer.tasks.CourseParticipants.render_to_pdf", "mailer.tasks.MyCourses.render_to_pdf"):
            patcher = mock.patch(target, side_effect=_fake_render_to_pdf)
            patcher.start()
            self.addCleanup(patcher.stop)

        self.settings_override = override_settings(
            KEPCHUP_SEND_PRESENCE_LIST=False,
            KEPCHUP_NO_SSF=True,
        )
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)

    def _send(self, bcc=None):
        return tasks.send_instructors_email(
            self.course.pk,
            self.instructor.pk,
            "Informations du cours",
            "Voici les documents",
            "noreply@kepchup.ch",
            ["noreply@kepchup.ch"],
            bcc=bcc,
        )

    @override_settings(KEPCHUP_ADDITIONAL_INSTRUCTOR_EMAIL_DOCUMENTS=[])
    def test_invalid_bcc_does_not_block_delivery_to_valid_recipients(self):
        valid_bcc = ["Direction <es.coppet@vd.ch>", "Juliana Isgrò <juliana.isgro@apej.ch>"]
        invalid_bcc = str(self.instructor.pk)
        with self.assertLogs("mailer.tasks", level="WARNING") as logs:
            self._send(bcc=[invalid_bcc, *valid_bcc])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.instructor.get_email_string()])
        self.assertEqual(mail.outbox[0].bcc, valid_bcc)
        self.assertIn(invalid_bcc, logs.output[0])

    @override_settings(KEPCHUP_ADDITIONAL_INSTRUCTOR_EMAIL_DOCUMENTS=[])
    def test_all_invalid_bcc_still_sends_to_instructor(self):
        with self.assertLogs("mailer.tasks", level="WARNING"):
            self._send(bcc=[str(self.instructor.pk)])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].bcc, [])

    @override_settings(KEPCHUP_ADDITIONAL_INSTRUCTOR_EMAIL_DOCUMENTS=["pdf/does-not-exist.pdf"])
    def test_missing_document_does_not_send_the_email(self):
        self._send()
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(KEPCHUP_ADDITIONAL_INSTRUCTOR_EMAIL_DOCUMENTS=["pdf/does-not-exist.pdf"])
    def test_missing_document_logs_an_error_for_sentry(self):
        with self.assertLogs("mailer.tasks", level="ERROR") as logs:
            self._send()
        self.assertIn("does-not-exist.pdf", logs.output[0])
        self.assertIn(str(self.course.pk), logs.output[0])
        self.assertIn(str(self.instructor.pk), logs.output[0])

    @override_settings(KEPCHUP_ADDITIONAL_INSTRUCTOR_EMAIL_DOCUMENTS=["pdf/does-not-exist.pdf"])
    def test_missing_document_does_not_leave_the_temp_directory_behind(self):
        created_tempdirs = []
        real_mkdtemp = tasks.mkdtemp

        def _tracking_mkdtemp(*args, **kwargs):
            path = real_mkdtemp(*args, **kwargs)
            created_tempdirs.append(path)
            return path

        with mock.patch("mailer.tasks.mkdtemp", side_effect=_tracking_mkdtemp):
            self._send()

        self.assertEqual(len(created_tempdirs), 1)
        self.assertFalse(os.path.exists(created_tempdirs[0]))

    def test_all_documents_present_sends_the_email_with_every_attachment(self):
        with tempfile.TemporaryDirectory() as static_root:
            os.makedirs(os.path.join(static_root, "pdf"))
            with open(os.path.join(static_root, "pdf", "infos.pdf"), "wb") as f:
                f.write(b"%PDF-1.4 fake")

            with override_settings(
                STATIC_ROOT=static_root,
                KEPCHUP_ADDITIONAL_INSTRUCTOR_EMAIL_DOCUMENTS=["pdf/infos.pdf"],
            ):
                self._send()

        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.to, [self.instructor.get_email_string()])
        attachment_names = {name for name, _content, _mimetype in sent.attachments}
        self.assertEqual(attachment_names, {"%s-participants.pdf" % self.course.number, "mes_cours.pdf", "infos.pdf"})

    def test_no_additional_documents_configured_still_sends(self):
        with override_settings(KEPCHUP_ADDITIONAL_INSTRUCTOR_EMAIL_DOCUMENTS=[]):
            self._send()
        self.assertEqual(len(mail.outbox), 1)


class InstructorParticipantOrderingTests(TenantTestCase):
    @override_settings(KEPCHUP_BIB_NUMBERS=True)
    def test_participant_and_presence_documents_use_numeric_bib_order(self):
        from registrations.tests.factories import RegistrationFactory

        from ..pdfutils import CourseParticipants
        from ..pdfutils import CourseParticipantsPresence

        course = CourseFactory()
        for bib, name in (("100", "Albert"), ("10", "Bernard"), ("2", "Charles"), ("", "Daniel")):
            RegistrationFactory(course=course, child__bib_number=bib, child__last_name=name)
        for renderer_class in (CourseParticipants, CourseParticipantsPresence):
            with self.subTest(renderer=renderer_class.__name__):
                renderer = renderer_class({"course": course})
                self.assertEqual(
                    [registration.child.bib_number for registration in renderer.context["participants"]],
                    ["2", "10", "100", ""],
                )
                html = renderer.get_content(renderer.get_message_template())
                self.assertLess(html.index("Charles"), html.index("Bernard"))
                self.assertLess(html.index("Bernard"), html.index("Albert"))
                self.assertLess(html.index("Albert"), html.index("Daniel"))
