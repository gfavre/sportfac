from unittest import mock

import faker
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import override_settings
from django.test.client import RequestFactory
from django.urls import reverse

from activities.tests.factories import CourseFactory
from mailer.models import MailArchive
from mailer.tests.factories import MailArchiveFactory
from profiles.models import FamilyUser
from profiles.tests.factories import FamilyUserFactory
from profiles.tests.factories import SchoolYearFactory
from registrations.models import Bill
from registrations.tests.factories import BillFactory
from registrations.tests.factories import ChildFactory
from registrations.tests.factories import RegistrationFactory
from registrations.tests.factories import WaitingBillFactory
from registrations.tests.factories import WaitingRegistrationFactory
from sportfac.middleware import VersionMiddleware
from sportfac.utils import process_request_for_middleware

from ...views import mail_views
from .base import BackendTestBase


fake = faker.Factory.create()


class MailViewsTests(BackendTestBase):
    def test_list(self):
        url = reverse("backend:archive")
        self.generic_test_rights(url)

    def test_confirmation(self):
        self.year = SchoolYearFactory()
        self.child = ChildFactory(family=self.user, school_year=self.year)
        self.registration = RegistrationFactory(child=self.child)
        self.registration.set_waiting()
        self.registration.save()
        url = reverse("backend:mail-needconfirmation")
        self.generic_test_rights(url)

    def test_notpaid(self):
        url = reverse("backend:mail-notpaidyet")
        self.year = SchoolYearFactory()
        self.child = ChildFactory(family=self.user, school_year=self.year)
        self.course = CourseFactory(price=20)
        self.registration = RegistrationFactory(child=self.child, course=self.course)
        self.bill = BillFactory(family=self.user, registrations=[self.registration])
        self.bill.status = Bill.STATUS.waiting
        self.bill.save()
        self.generic_test_rights(url)

    def test_custom(self):
        url = reverse("backend:custom-mail-custom-users")
        self.generic_test_rights(url)


# noinspection DuplicatedCode
class MailCreateViewTests(BackendTestBase):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.other_users = FamilyUserFactory.create_batch(4)
        self.instructors = FamilyUserFactory.create_batch(2)
        self.course = CourseFactory(instructors=self.instructors)
        self.url = reverse("backend:custom-mail-custom-users")

    def test_rights(self):
        self.generic_test_rights(self.url)

    def test_get(self):
        request = self.factory.get(self.url)
        request.user = self.manager
        process_request_for_middleware(request, SessionMiddleware)
        response = mail_views.MailCreateView.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_nb_recipients(self):
        data = {"subject": fake.sentence(), "message": fake.paragraph()}
        request = self.factory.post(self.url, data=data)
        request.user = self.manager
        process_request_for_middleware(request, SessionMiddleware)
        request.session["mail-userids"] = [str(user.pk) for user in self.other_users]
        request.session.save()
        mail_views.MailCreateView.as_view()(request)
        archive = MailArchive.objects.first()
        self.assertEqual(len(archive.recipients), len(self.other_users))
        self.assertEqual(len(archive.bcc_recipients), 0)

    def test_send_copy(self):
        data = {"subject": fake.sentence(), "message": fake.paragraph(), "send_copy": "1"}
        request = self.factory.post(self.url, data=data)
        request.user = self.manager
        process_request_for_middleware(request, SessionMiddleware)
        request.session["mail-userids"] = [str(user.pk) for user in self.other_users]
        request.session.save()
        mail_views.MailCreateView.as_view()(request)
        archive = MailArchive.objects.first()
        self.assertEqual(len(archive.recipients), len(self.other_users))
        self.assertEqual(len(archive.bcc_recipients), 1)

    def test_send_all_admin_copy(self):
        data = {
            "subject": fake.sentence(),
            "message": fake.paragraph(),
            "send_copy": "1",
            "copy_all_admins": "1",
        }
        request = self.factory.post(self.url, data=data)
        request.user = self.manager
        process_request_for_middleware(request, SessionMiddleware)
        request.session["mail-userids"] = [str(user.pk) for user in self.other_users]
        request.session.save()
        mail_views.MailCreateView.as_view()(request)
        archive = MailArchive.objects.first()
        self.assertEqual(len(archive.recipients), len(self.other_users))
        self.assertEqual(len(archive.bcc_recipients), FamilyUser.managers_objects.count())


# noinspection DuplicatedCode
class MailPreviewTest(BackendTestBase):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.instructors = FamilyUserFactory.create_batch(2)
        self.other_users = FamilyUserFactory.create_batch(4)
        self.course = CourseFactory(instructors=self.instructors)
        self.archive = MailArchiveFactory(
            recipients=[str(user.pk) for user in self.other_users],
            bcc_recipients=[str(user.pk) for user in FamilyUser.managers_objects.all()],
        )
        self.url = reverse(
            "backend:custom-mail-custom-users-preview",
        )

    def test_get(self):
        request = self.factory.get(self.url)
        request.user = self.manager
        process_request_for_middleware(request, SessionMiddleware)
        request.session["mail"] = self.archive.pk
        request.session.save()
        response = mail_views.MailPreview.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context_data["to_email"]), len(self.other_users))
        self.assertEqual(len(response.context_data["bcc_email"]), FamilyUser.managers_objects.count())

    @mock.patch("mailer.tasks.send_mail.delay")
    def test_post(self, sendmail_method):
        request = self.factory.post(self.url, data={})
        request.user = self.manager
        process_request_for_middleware(request, SessionMiddleware)
        process_request_for_middleware(request, MessageMiddleware)
        request.session["mail"] = self.archive.pk
        request.session.save()
        response = mail_views.MailPreview.as_view()(request)
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("mail", request.session)
        self.assertNotIn("mail-userids", request.session)
        self.assertEqual(sendmail_method.call_count, FamilyUser.managers_objects.count() + len(self.other_users))


# noinspection DuplicatedCode
class ParticipantsMailCreateViewTests(BackendTestBase):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.instructors = FamilyUserFactory.create_batch(2)
        self.course = CourseFactory(instructors=self.instructors)
        self.year = SchoolYearFactory()
        self.children = ChildFactory.create_batch(10, school_year=self.year)
        self.registrations = [RegistrationFactory(course=self.course, child=child) for child in self.children]
        self.url = reverse("backend:mail-participants-custom", kwargs={"course": self.course.pk})

    def test_rights(self):
        self.generic_test_rights(self.url)

    def test_get(self):
        request = self.factory.get(self.url)
        request.user = self.manager
        process_request_for_middleware(request, SessionMiddleware)
        response = mail_views.MailCreateView.as_view()(request, course=self.course.pk)
        self.assertEqual(response.status_code, 200)

    def test_nb_recipients(self):
        data = {"subject": fake.sentence(), "message": fake.paragraph()}
        request = self.factory.post(self.url, data=data)
        request.user = self.manager
        process_request_for_middleware(request, SessionMiddleware)
        mail_views.ParticipantsMailCreateView.as_view()(request, course=self.course.pk)
        archive = MailArchive.objects.first()
        self.assertEqual(len(archive.recipients), len(self.registrations))
        self.assertEqual(len(archive.bcc_recipients), 0)

    def test_send_copy(self):
        data = {"subject": fake.sentence(), "message": fake.paragraph(), "send_copy": "1"}
        request = self.factory.post(self.url, data=data)
        request.user = self.manager
        process_request_for_middleware(request, SessionMiddleware)
        mail_views.ParticipantsMailCreateView.as_view()(request, course=self.course.pk)
        archive = MailArchive.objects.first()
        self.assertEqual(len(archive.recipients), len(self.registrations))
        self.assertEqual(len(archive.bcc_recipients), 1)

    def test_send_all_instructors_copy(self):
        data = {
            "subject": fake.sentence(),
            "message": fake.paragraph(),
            "copy_all_instructors": "1",
        }
        request = self.factory.post(self.url, data=data)
        request.user = self.manager
        process_request_for_middleware(request, SessionMiddleware)
        mail_views.ParticipantsMailCreateView.as_view()(request, course=self.course.pk)
        archive = MailArchive.objects.first()
        self.assertEqual(len(archive.recipients), len(self.registrations))
        self.assertEqual(len(archive.bcc_recipients), len(self.instructors))


# noinspection DuplicatedCode
class ParticipantsMailPreviewTest(BackendTestBase):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.instructors = FamilyUserFactory.create_batch(2)
        self.course = CourseFactory(instructors=self.instructors)
        self.year = SchoolYearFactory()
        self.children = ChildFactory.create_batch(10, school_year=self.year)
        self.registrations = [RegistrationFactory(course=self.course, child=child) for child in self.children]
        self.archive = MailArchiveFactory(
            recipients=[str(child.family.pk) for child in self.children],
            bcc_recipients=[str(user.pk) for user in self.instructors],
        )
        self.url = reverse("backend:mail-participants-custom-preview", kwargs={"course": self.course.pk})

    def test_no_archive(self):
        request = self.factory.get(self.url)
        request.user = self.manager
        process_request_for_middleware(request, SessionMiddleware)
        response = mail_views.ParticipantsMailPreview.as_view()(request, course=self.course.pk)
        self.assertEqual(response.status_code, 302)

    def test_get(self):
        request = self.factory.get(self.url)
        request.user = self.manager
        process_request_for_middleware(request, SessionMiddleware)
        request.session["mail"] = self.archive.pk
        request.session.save()
        response = mail_views.ParticipantsMailPreview.as_view()(request, course=self.course.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context_data["to_email"]), len(self.children))
        self.assertEqual(len(response.context_data["bcc_email"]), len(self.instructors))

    @mock.patch("mailer.tasks.send_mail.delay")
    def test_post(self, sendmail_method):
        request = self.factory.post(self.url, data={})
        request.user = self.manager
        process_request_for_middleware(request, SessionMiddleware)
        process_request_for_middleware(request, MessageMiddleware)
        request.session["mail"] = self.archive.pk
        request.session.save()
        response = mail_views.ParticipantsMailPreview.as_view()(request, course=self.course.pk)
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("mail", request.session)
        self.assertNotIn("mail-userids", request.session)
        self.assertEqual(sendmail_method.call_count, len(self.instructors) + len(self.children))


class MailCourseInstructorsViewTest(BackendTestBase):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.instructors = FamilyUserFactory.create_batch(2)
        self.course = CourseFactory(instructors=self.instructors)
        self.url = reverse("backend:course-mail-instructors", kwargs={"course": self.course.pk})

    def test_rights(self):
        self.generic_test_rights(self.url)

    @mock.patch("mailer.tasks.send_instructors_email.delay")
    def test_admin_copies_without_archive_address_use_emails(self, sendmail_method):
        from backend.dynamic_preferences_registry import global_preferences_registry

        global_preferences_registry.manager()["email__ADMIN_ARCHIVE_MAIL"] = ""
        request = self.factory.post(self.url, data={"copy_all_admins": "on"})
        request.user = self.manager
        process_request_for_middleware(request, SessionMiddleware)
        process_request_for_middleware(request, MessageMiddleware)
        response = mail_views.MailCourseInstructorsView.as_view()(request, course=self.course.pk)
        self.assertEqual(response.status_code, 302)
        expected = {admin.get_email_string() for admin in FamilyUser.managers_objects.all()}
        self.assertTrue(expected)
        for call in sendmail_method.call_args_list:
            self.assertEqual(set(call.kwargs["bcc"]), expected)

    def test_get(self):
        request = self.factory.get(self.url)
        request.user = self.manager
        process_request_for_middleware(request, SessionMiddleware)
        response = mail_views.MailCourseInstructorsView.as_view()(request, course=self.course.pk)
        self.assertEqual(response.status_code, 200)

    @override_settings(
        KEPCHUP_NO_SSF=True,
        KEPCHUP_SEND_PRESENCE_LIST=True,
        KEPCHUP_ADDITIONAL_INSTRUCTOR_EMAIL_DOCUMENTS=["pdf/consignes.pdf"],
    )
    def test_confirmation_previews_recipients_messages_and_attachments(self):
        self.client.force_login(self.manager)
        with mock.patch("mailer.tasks.send_instructors_email.delay") as send:
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        send.assert_not_called()
        previews = response.context["instructor_previews"]
        self.assertEqual(len(previews), 2)
        for preview in previews:
            self.assertContains(response, preview["recipient"].email)
            self.assertTrue(preview["body"])
            self.assertTrue(preview["subject"])
            self.assertEqual(
                preview["attachments"],
                [
                    f"{self.course.number}-participants.pdf",
                    "mes_cours.pdf",
                    f"{self.course.number}-presences.pdf",
                    "consignes.pdf",
                ],
            )
        self.assertContains(response, "Aperçu du mail", count=2)

    @override_settings(
        KEPCHUP_NO_SSF=False,
        KEPCHUP_FICHE_SALAIRE_MONTREUX=False,
        KEPCHUP_SEND_PRESENCE_LIST=False,
        KEPCHUP_ADDITIONAL_INSTRUCTOR_EMAIL_DOCUMENTS=[],
    )
    def test_multicourse_confirmation_includes_each_course_and_instructor(self):
        other = CourseFactory(instructors=[self.instructors[0]])
        self.client.force_login(self.manager)
        response = self.client.get(reverse("backend:courses-mail-instructors"), {"c": [self.course.pk, other.pk]})
        self.assertEqual(response.status_code, 200)
        previews = response.context["instructor_previews"]
        self.assertEqual(len(previews), 3)
        self.assertEqual({preview["course"].pk for preview in previews}, {self.course.pk, other.pk})
        for preview in previews:
            instructor = preview["recipient"]
            self.assertIn(
                f"SSF_decompte_moniteur_{instructor.first_name}_{instructor.last_name}.pdf", preview["attachments"]
            )
            self.assertFalse(any(name.endswith("-presences.pdf") for name in preview["attachments"]))

    def test_confirmation_without_instructors_disables_sending(self):
        self.course.instructors.clear()
        self.client.force_login(self.manager)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["instructor_previews"], [])
        self.assertContains(response, "Aucun mail ne sera envoyé")

    @mock.patch("mailer.tasks.send_instructors_email.delay")
    def test_post(self, _):
        request = self.factory.post(self.url, data={"send_copy": 0, "copy_all_admins": 0})
        request.user = self.manager
        process_request_for_middleware(request, SessionMiddleware)
        process_request_for_middleware(request, MessageMiddleware)
        response = mail_views.MailCourseInstructorsView.as_view()(request, course=self.course.pk)
        self.assertEqual(response.status_code, 302)

    @mock.patch("mailer.tasks.send_instructors_email.delay")
    def test_send_mail(self, sendmail_method):
        request = self.factory.post(self.url, data={})
        request.user = self.manager
        process_request_for_middleware(request, SessionMiddleware)
        process_request_for_middleware(request, MessageMiddleware)
        mail_views.MailCourseInstructorsView.as_view()(request, course=self.course.pk)
        self.assertEqual(sendmail_method.call_count, len(self.instructors))


# noinspection DuplicatedCode
class MailConfirmationParticipantsViewTest(BackendTestBase):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.instructors = FamilyUserFactory.create_batch(2)
        self.course = CourseFactory(instructors=self.instructors)
        self.year = SchoolYearFactory()
        self.children = ChildFactory.create_batch(10, school_year=self.year)
        self.registrations = [RegistrationFactory(course=self.course, child=child) for child in self.children]
        self.url = reverse("backend:course-mail-confirmation", kwargs={"course": self.course.pk})

    def test_rights(self):
        self.generic_test_rights(self.url)

    def test_get(self):
        request = self.factory.get(self.url)
        request.user = self.manager
        process_request_for_middleware(request, SessionMiddleware)
        response = mail_views.MailConfirmationParticipantsView.as_view()(request, course=self.course.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data["total"], len(self.registrations))
        self.assertEqual(response.context_data["has_prev"], False)

    def test_confirmation_identifies_family_child_and_send_scope(self):
        self.client.force_login(self.manager)
        with mock.patch("mailer.tasks.send_mail.delay") as send:
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        send.assert_not_called()
        registration = response.context["registration"]
        self.assertContains(response, registration.child.family.email)
        self.assertContains(response, registration.child.first_name)
        self.assertContains(response, "10 convocations prévues")
        self.assertContains(response, "Aucune pièce jointe")
        self.assertContains(response, "Confirmer l’envoi")
        self.assertContains(response, "Envoyer les 10 convocations aux familles")

    def test_multiple_courses_show_total_and_keep_course_navigation(self):
        other = CourseFactory()
        RegistrationFactory(course=other)
        self.client.force_login(self.manager)
        params = {"c": [self.course.pk, other.pk], "selected": other.pk}
        response = self.client.get(reverse("backend:courses-mail-confirmation"), params)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["delivery_total"], 11)
        self.assertEqual(response.context["total"], 1)
        self.assertContains(response, "11 convocations prévues")
        self.assertContains(response, "Message 1 / 1 pour ce cours")
        self.assertContains(response, f"c={self.course.pk}")
        self.assertContains(response, f"c={other.pk}")
        self.assertContains(response, f"selected={self.course.pk}")
        self.assertContains(response, "pas seulement le message affiché")

    def test_browse(self):
        request = self.factory.get(self.url, {"number": 2})
        request.user = self.manager
        process_request_for_middleware(request, SessionMiddleware)
        response = mail_views.MailConfirmationParticipantsView.as_view()(request, course=self.course.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data["has_prev"], True)
        self.assertEqual(response.context_data["mailidentifier"], 2)

    @mock.patch("mailer.tasks.send_mail.delay")
    def test_post(self, sendmail_method):
        request = self.factory.post(self.url, data={})
        request.user = self.manager
        process_request_for_middleware(request, SessionMiddleware)
        process_request_for_middleware(request, MessageMiddleware)
        response = mail_views.MailConfirmationParticipantsView.as_view()(request, course=self.course.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(sendmail_method.call_count, len(self.registrations))


class NotPaidYetViewTest(BackendTestBase):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.course = CourseFactory()
        self.year = SchoolYearFactory()
        self.children = ChildFactory.create_batch(10, school_year=self.year)
        self.registrations = [RegistrationFactory(course=self.course, child=child) for child in self.children]
        self.bills = [
            WaitingBillFactory(registrations=[registration], family=registration.child.family)
            for registration in self.registrations
        ]
        self.url = reverse("backend:mail-notpaidyet")

    def test_rights(self):
        self.generic_test_rights(self.url)

    def test_get(self):
        request = self.factory.get(self.url)
        request.user = self.manager
        process_request_for_middleware(request, SessionMiddleware)
        process_request_for_middleware(request, VersionMiddleware)
        response = mail_views.NotPaidYetView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data["total"], len(self.bills))
        self.assertEqual(response.context_data["has_prev"], False)

    @mock.patch("mailer.tasks.send_mail.delay")
    def test_post(self, sendmail_method):
        request = self.factory.post(self.url, data={})
        request.user = self.manager
        process_request_for_middleware(request, SessionMiddleware)
        process_request_for_middleware(request, VersionMiddleware)
        process_request_for_middleware(request, MessageMiddleware)
        response = mail_views.NotPaidYetView.as_view()(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(sendmail_method.call_count, len(self.bills))


class NeedConfirmationViewTest(BackendTestBase):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.course = CourseFactory()
        self.year = SchoolYearFactory()
        self.children = ChildFactory.create_batch(10, school_year=self.year)
        self.registrations = [WaitingRegistrationFactory(course=self.course, child=child) for child in self.children]
        self.url = reverse("backend:mail-needconfirmation")

    def test_rights(self):
        self.generic_test_rights(self.url)

    def test_get(self):
        request = self.factory.get(self.url)
        request.user = self.manager
        process_request_for_middleware(request, SessionMiddleware)
        response = mail_views.NeedConfirmationView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data["total"], len(self.registrations))
        self.assertEqual(response.context_data["has_prev"], False)

    @mock.patch("mailer.tasks.send_mail.delay")
    def test_post(self, sendmail_method):
        request = self.factory.post(self.url, data={})
        request.user = self.manager
        process_request_for_middleware(request, SessionMiddleware)
        process_request_for_middleware(request, MessageMiddleware)
        response = mail_views.NeedConfirmationView.as_view()(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(sendmail_method.call_count, len(self.registrations))
