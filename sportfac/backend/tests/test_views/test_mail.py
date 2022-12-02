# -*- coding: utf-8 -*-
from __future__ import absolute_import
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import Http404
from django.test.client import RequestFactory
from django.urls import reverse

import faker
import mock

from activities.tests.factories import CourseFactory
from mailer.models import MailArchive
from mailer.tests.factories import MailArchiveFactory
from profiles.models import FamilyUser
from profiles.tests.factories import FamilyUserFactory, SchoolYearFactory
from registrations.models import Bill
from registrations.tests.factories import (BillFactory, ChildFactory,
                                           RegistrationFactory,
                                           WaitingBillFactory,
                                           WaitingRegistrationFactory)
from sportfac.middleware import RegistrationOpenedMiddleware, VersionMiddleware
from sportfac.utils import add_middleware_to_request

from ...views import mail_views
from .base import BackendTestBase


fake = faker.Factory.create()


class MailViewsTests(BackendTestBase):

    def test_list(self):
        url = reverse('backend:archive')
        self.generic_test_rights(url)

    def test_confirmation(self):
        self.year = SchoolYearFactory()
        self.child = ChildFactory(family=self.user, school_year=self.year)
        self.registration = RegistrationFactory(child=self.child)
        self.registration.set_waiting()
        self.registration.save()
        url = reverse('backend:mail-needconfirmation')
        self.generic_test_rights(url)

    def test_notpaid(self):
        url = reverse('backend:mail-notpaidyet')
        self.year = SchoolYearFactory()
        self.child = ChildFactory(family=self.user, school_year=self.year)
        self.course = CourseFactory(price=20)
        self.registration = RegistrationFactory(child=self.child, course=self.course)
        self.bill = BillFactory(family=self.user, registrations=[self.registration])
        self.bill.status = Bill.STATUS.waiting
        self.bill.save()
        self.generic_test_rights(url)

    def test_custom(self):
        url = reverse('backend:custom-mail-custom-users')
        self.generic_test_rights(url)


# noinspection DuplicatedCode
class MailCreateViewTests(BackendTestBase):
    def setUp(self):
        super(MailCreateViewTests, self).setUp()
        self.factory = RequestFactory()
        self.other_users = FamilyUserFactory.create_batch(4)
        self.instructors = FamilyUserFactory.create_batch(2)
        self.course = CourseFactory(instructors=self.instructors)
        self.url = reverse('backend:custom-mail-custom-users')

    def test_rights(self):
        self.generic_test_rights(self.url)

    def test_get(self):
        request = self.factory.get(self.url)
        request.user = self.manager
        request = add_middleware_to_request(request, SessionMiddleware)
        response = mail_views.MailCreateView.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_nb_recipients(self):
        data = {'subject': fake.sentence(),
                'message': fake.paragraph()}
        request = self.factory.post(self.url, data=data)
        request.user = self.manager
        request = add_middleware_to_request(request, SessionMiddleware)
        request.session['mail-userids'] = [str(user.pk) for user in self.other_users]
        request.session.save()
        mail_views.MailCreateView.as_view()(request)
        archive = MailArchive.objects.first()
        self.assertEqual(len(archive.recipients), len(self.other_users))
        self.assertEqual(len(archive.bcc_recipients), 0)

    def test_send_copy(self):
        data = {'subject': fake.sentence(),
                'message': fake.paragraph(),
                'send_copy': '1'}
        request = self.factory.post(self.url, data=data)
        request.user = self.manager
        request = add_middleware_to_request(request, SessionMiddleware)
        request.session['mail-userids'] = [str(user.pk) for user in self.other_users]
        request.session.save()
        mail_views.MailCreateView.as_view()(request)
        archive = MailArchive.objects.first()
        self.assertEqual(len(archive.recipients), len(self.other_users))
        self.assertEqual(len(archive.bcc_recipients), 1)

    def test_send_all_admin_copy(self):
        data = {'subject': fake.sentence(),
                'message': fake.paragraph(),
                'send_copy': '1',
                'copy_all_admins': '1'
                }
        request = self.factory.post(self.url, data=data)
        request.user = self.manager
        request = add_middleware_to_request(request, SessionMiddleware)
        request.session['mail-userids'] = [str(user.pk) for user in self.other_users]
        request.session.save()
        mail_views.MailCreateView.as_view()(request)
        archive = MailArchive.objects.first()
        self.assertEqual(len(archive.recipients), len(self.other_users))
        self.assertEqual(len(archive.bcc_recipients), FamilyUser.managers_objects.count())


# noinspection DuplicatedCode
class MailPreviewTest(BackendTestBase):
    def setUp(self):
        super(MailPreviewTest, self).setUp()
        self.factory = RequestFactory()
        self.instructors = FamilyUserFactory.create_batch(2)
        self.other_users = FamilyUserFactory.create_batch(4)
        self.course = CourseFactory(instructors=self.instructors)
        self.archive = MailArchiveFactory(recipients=[str(user.pk) for user in self.other_users],
                                          bcc_recipients=[str(user.pk) for user in FamilyUser.managers_objects.all()],)
        self.url = reverse('backend:custom-mail-custom-users-preview',)

    def test_no_archive(self):
        request = self.factory.get(self.url)
        request.user = self.manager
        request = add_middleware_to_request(request, SessionMiddleware)
        with self.assertRaises(Http404):
            mail_views.MailPreview.as_view()(request)

    def test_get(self):
        request = self.factory.get(self.url)
        request.user = self.manager
        request = add_middleware_to_request(request, SessionMiddleware)
        request.session['mail'] = self.archive.pk
        request.session.save()
        response = mail_views.MailPreview.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context_data['to_email']), len(self.other_users))
        self.assertEqual(len(response.context_data['bcc_email']), FamilyUser.managers_objects.count())

    @mock.patch('mailer.tasks.send_mail.delay')
    def test_post(self, sendmail_method):
        request = self.factory.post(self.url, data={})
        request.user = self.manager
        request = add_middleware_to_request(request, SessionMiddleware)
        request = add_middleware_to_request(request, MessageMiddleware)
        request.session['mail'] = self.archive.pk
        request.session.save()
        response = mail_views.MailPreview.as_view()(request)
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('mail', request.session)
        self.assertNotIn('mail-userids', request.session)
        self.assertEqual(sendmail_method.call_count, FamilyUser.managers_objects.count() + len(self.other_users))


# noinspection DuplicatedCode
class ParticipantsMailCreateViewTests(BackendTestBase):
    def setUp(self):
        super(ParticipantsMailCreateViewTests, self).setUp()
        self.factory = RequestFactory()
        self.instructors = FamilyUserFactory.create_batch(2)
        self.course = CourseFactory(instructors=self.instructors)
        self.year = SchoolYearFactory()
        self.children = ChildFactory.create_batch(10, school_year=self.year)
        self.registrations = [RegistrationFactory(course=self.course, child=child) for child in self.children]
        self.url = reverse('backend:mail-participants-custom', kwargs={'course': self.course.pk})

    def test_rights(self):
        self.generic_test_rights(self.url)

    def test_get(self):
        request = self.factory.get(self.url)
        request.user = self.manager
        request = add_middleware_to_request(request, SessionMiddleware)
        response = mail_views.MailCreateView.as_view()(request, course=self.course.pk)
        self.assertEqual(response.status_code, 200)

    def test_nb_recipients(self):
        data = {'subject': fake.sentence(),
                'message': fake.paragraph()}
        request = self.factory.post(self.url, data=data)
        request.user = self.manager
        request = add_middleware_to_request(request, SessionMiddleware)
        mail_views.ParticipantsMailCreateView.as_view()(request, course=self.course.pk)
        archive = MailArchive.objects.first()
        self.assertEqual(len(archive.recipients), len(self.registrations))
        self.assertEqual(len(archive.bcc_recipients), 0)

    def test_send_copy(self):
        data = {'subject': fake.sentence(),
                'message': fake.paragraph(),
                'send_copy': '1'}
        request = self.factory.post(self.url, data=data)
        request.user = self.manager
        request = add_middleware_to_request(request, SessionMiddleware)
        mail_views.ParticipantsMailCreateView.as_view()(request, course=self.course.pk)
        archive = MailArchive.objects.first()
        self.assertEqual(len(archive.recipients), len(self.registrations))
        self.assertEqual(len(archive.bcc_recipients), 1)

    def test_send_all_instructors_copy(self):
        data = {'subject': fake.sentence(),
                'message': fake.paragraph(),
                'copy_all_instructors': '1'}
        request = self.factory.post(self.url, data=data)
        request.user = self.manager
        request = add_middleware_to_request(request, SessionMiddleware)
        mail_views.ParticipantsMailCreateView.as_view()(request, course=self.course.pk)
        archive = MailArchive.objects.first()
        self.assertEqual(len(archive.recipients), len(self.registrations))
        self.assertEqual(len(archive.bcc_recipients), len(self.instructors))


# noinspection DuplicatedCode
class ParticipantsMailPreviewTest(BackendTestBase):
    def setUp(self):
        super(ParticipantsMailPreviewTest, self).setUp()
        self.factory = RequestFactory()
        self.instructors = FamilyUserFactory.create_batch(2)
        self.course = CourseFactory(instructors=self.instructors)
        self.year = SchoolYearFactory()
        self.children = ChildFactory.create_batch(10, school_year=self.year)
        self.registrations = [RegistrationFactory(course=self.course, child=child) for child in self.children]
        self.archive = MailArchiveFactory(recipients=[str(child.family.pk) for child in self.children],
                                          bcc_recipients=[str(user.pk) for user in self.instructors],)
        self.url = reverse('backend:mail-participants-custom-preview', kwargs={'course': self.course.pk})

    def test_no_archive(self):
        request = self.factory.get(self.url)
        request.user = self.manager
        request = add_middleware_to_request(request, SessionMiddleware)
        with self.assertRaises(Http404):
            mail_views.ParticipantsMailPreview.as_view()(request, course=self.course.pk)

    def test_get(self):
        request = self.factory.get(self.url)
        request.user = self.manager
        request = add_middleware_to_request(request, SessionMiddleware)
        request.session['mail'] = self.archive.pk
        request.session.save()
        response = mail_views.ParticipantsMailPreview.as_view()(request, course=self.course.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context_data['to_email']), len(self.children))
        self.assertEqual(len(response.context_data['bcc_email']), len(self.instructors))

    @mock.patch('mailer.tasks.send_mail.delay')
    def test_post(self, sendmail_method):
        request = self.factory.post(self.url, data={})
        request.user = self.manager
        request = add_middleware_to_request(request, SessionMiddleware)
        request = add_middleware_to_request(request, MessageMiddleware)
        request.session['mail'] = self.archive.pk
        request.session.save()
        response = mail_views.ParticipantsMailPreview.as_view()(request, course=self.course.pk)
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('mail', request.session)
        self.assertNotIn('mail-userids', request.session)
        self.assertEqual(sendmail_method.call_count, len(self.instructors) + len(self.children))


class MailCourseInstructorsViewTest(BackendTestBase):
    def setUp(self):
        super(MailCourseInstructorsViewTest, self).setUp()
        self.factory = RequestFactory()
        self.instructors = FamilyUserFactory.create_batch(2)
        self.course = CourseFactory(instructors=self.instructors)
        self.url = reverse('backend:course-mail-instructors', kwargs={'course': self.course.pk})

    def test_rights(self):
        self.generic_test_rights(self.url)

    def test_get(self):
        request = self.factory.get(self.url)
        request.user = self.manager
        request = add_middleware_to_request(request, SessionMiddleware)
        response = mail_views.MailCourseInstructorsView.as_view()(request, course=self.course.pk)
        self.assertEqual(response.status_code, 200)

    @mock.patch('mailer.tasks.send_instructors_email.delay')
    def test_post(self, _):
        request = self.factory.post(self.url, data={
            'send_copy': 0,
            'copy_all_admins': 0
        })
        request.user = self.manager
        request = add_middleware_to_request(request, SessionMiddleware)
        request = add_middleware_to_request(request, MessageMiddleware)
        response = mail_views.MailCourseInstructorsView.as_view()(request, course=self.course.pk)
        self.assertEqual(response.status_code, 302)

    @mock.patch('mailer.tasks.send_instructors_email.delay')
    def test_send_mail(self, sendmail_method):
        request = self.factory.post(self.url, data={})
        request.user = self.manager
        request = add_middleware_to_request(request, SessionMiddleware)
        request = add_middleware_to_request(request, MessageMiddleware)
        mail_views.MailCourseInstructorsView.as_view()(request, course=self.course.pk)
        self.assertEqual(sendmail_method.call_count, len(self.instructors))


# noinspection DuplicatedCode
class MailConfirmationParticipantsViewTest(BackendTestBase):
    def setUp(self):
        super(MailConfirmationParticipantsViewTest, self).setUp()
        self.factory = RequestFactory()
        self.instructors = FamilyUserFactory.create_batch(2)
        self.course = CourseFactory(instructors=self.instructors)
        self.year = SchoolYearFactory()
        self.children = ChildFactory.create_batch(10, school_year=self.year)
        self.registrations = [RegistrationFactory(course=self.course, child=child) for child in self.children]
        self.url = reverse('backend:course-mail-confirmation', kwargs={'course': self.course.pk})

    def test_rights(self):
        self.generic_test_rights(self.url)

    def test_get(self):
        request = self.factory.get(self.url)
        request.user = self.manager
        request = add_middleware_to_request(request, SessionMiddleware)
        response = mail_views.MailConfirmationParticipantsView.as_view()(request, course=self.course.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['total'], len(self.registrations))
        self.assertEqual(response.context_data['has_prev'], False)

    def test_browse(self):
        request = self.factory.get(self.url, {'number': 2})
        request.user = self.manager
        request = add_middleware_to_request(request, SessionMiddleware)
        response = mail_views.MailConfirmationParticipantsView.as_view()(request, course=self.course.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['has_prev'], True)
        self.assertEqual(response.context_data['mailidentifier'], 2)

    @mock.patch('mailer.tasks.send_mail.delay')
    def test_post(self, sendmail_method):
        request = self.factory.post(self.url, data={})
        request.user = self.manager
        request = add_middleware_to_request(request, SessionMiddleware)
        request = add_middleware_to_request(request, MessageMiddleware)
        response = mail_views.MailConfirmationParticipantsView.as_view()(request, course=self.course.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(sendmail_method.call_count, len(self.registrations))


class NotPaidYetViewTest(BackendTestBase):
    def setUp(self):
        super(NotPaidYetViewTest, self).setUp()
        self.factory = RequestFactory()
        self.course = CourseFactory()
        self.year = SchoolYearFactory()
        self.children = ChildFactory.create_batch(10, school_year=self.year)
        self.registrations = [RegistrationFactory(course=self.course, child=child) for child in self.children]
        self.bills = [WaitingBillFactory(registrations=[registration], family=registration.child.family)
                      for registration in self.registrations]
        self.url = reverse('backend:mail-notpaidyet')

    def test_rights(self):
        self.generic_test_rights(self.url)

    def test_get(self):
        request = self.factory.get(self.url)
        request.user = self.manager
        request = add_middleware_to_request(request, SessionMiddleware)
        request = add_middleware_to_request(request, VersionMiddleware)
        request = add_middleware_to_request(request, RegistrationOpenedMiddleware)
        response = mail_views.NotPaidYetView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['total'], len(self.bills))
        self.assertEqual(response.context_data['has_prev'], False)

    @mock.patch('mailer.tasks.send_mail.delay')
    def test_post(self, sendmail_method):
        request = self.factory.post(self.url, data={})
        request.user = self.manager
        request = add_middleware_to_request(request, SessionMiddleware)
        request = add_middleware_to_request(request, VersionMiddleware)
        request = add_middleware_to_request(request, RegistrationOpenedMiddleware)
        request = add_middleware_to_request(request, MessageMiddleware)
        response = mail_views.NotPaidYetView.as_view()(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(sendmail_method.call_count, len(self.bills))


class NeedConfirmationViewTest(BackendTestBase):
    def setUp(self):
        super(NeedConfirmationViewTest, self).setUp()
        self.factory = RequestFactory()
        self.course = CourseFactory()
        self.year = SchoolYearFactory()
        self.children = ChildFactory.create_batch(10, school_year=self.year)
        self.registrations = [WaitingRegistrationFactory(course=self.course, child=child) for child in self.children]
        self.url = reverse('backend:mail-needconfirmation')

    def test_rights(self):
        self.generic_test_rights(self.url)

    def test_get(self):
        request = self.factory.get(self.url)
        request.user = self.manager
        request = add_middleware_to_request(request, SessionMiddleware)
        response = mail_views.NeedConfirmationView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['total'], len(self.registrations))
        self.assertEqual(response.context_data['has_prev'], False)

    @mock.patch('mailer.tasks.send_mail.delay')
    def test_post(self, sendmail_method):
        request = self.factory.post(self.url, data={})
        request.user = self.manager
        request = add_middleware_to_request(request, SessionMiddleware)
        request = add_middleware_to_request(request, MessageMiddleware)
        response = mail_views.NeedConfirmationView.as_view()(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(sendmail_method.call_count, len(self.registrations))
