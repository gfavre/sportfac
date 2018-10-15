# -*- coding:utf-8 -*-
import json

from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from django.core.urlresolvers import reverse
from django.http import Http404
from django.test import RequestFactory

import mock
import faker

from profiles.tests.factories import FamilyUserFactory, SchoolYearFactory, DEFAULT_PASS
from mailer.models import MailArchive
from mailer.tests.factories import MailArchiveFactory
from registrations.tests.factories import ChildFactory, RegistrationFactory
from sportfac.utils import TenantTestCase as TestCase, add_middleware_to_request
from .factories import ActivityFactory, CourseFactory
from ..views import MailUsersView, CustomParticipantsCustomMailView, CustomMailPreview, MailCourseInstructorsView


fake = faker.Factory.create()


class ActivityViewsTests(TestCase):
    def setUp(self):
        super(ActivityViewsTests, self).setUp()
        self.activity = ActivityFactory()
        self.user = FamilyUserFactory()

    def test_detail_view(self):
        url = self.activity.get_absolute_url()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_detail_user_registered(self):
        self.client.login(username=self.user.email, password=DEFAULT_PASS)
        child = ChildFactory(family=self.user)
        course = CourseFactory(activity=self.activity)
        RegistrationFactory(child=child, course=course)
        url = self.activity.get_absolute_url()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class CourseViewsTests(TestCase):
    def setUp(self):
        super(CourseViewsTests, self).setUp()
        self.instructor = FamilyUserFactory()
        self.course = CourseFactory(instructors=(self.instructor,))
        self.family = FamilyUserFactory()
        self.year = SchoolYearFactory()
        self.child = ChildFactory(family=self.family, school_year=self.year)
        self.registration = RegistrationFactory(course=self.course, child=self.child)
        self.other_user = FamilyUserFactory()

    def test_detail_access(self):
        url = self.course.get_absolute_url()
        response = self.client.get(url)
        # anonymous users cannot see details
        self.assertEqual(response.status_code, 302)
        self.client.login(username=self.other_user.email, password=DEFAULT_PASS)
        response = self.client.get(url)
        # Logged in users who are not registered cannot see details
        self.assertEqual(response.status_code, 302)

    def test_detail_view(self):
        self.client.login(username=self.family.email, password=DEFAULT_PASS)
        url = self.course.get_absolute_url()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_my_courses_access(self):
        url = reverse('activities:my-courses')
        response = self.client.get(url)
        # anonymous users cannot see my-courses
        self.assertEqual(response.status_code, 302)

        self.client.login(username=self.other_user.email, password=DEFAULT_PASS)
        response = self.client.get(url)
        # basic logged in users cannot see my-courses
        self.assertEqual(response.status_code, 302)

        self.client.login(username=self.family.email, password=DEFAULT_PASS)
        response = self.client.get(url)
        # members of course cannot see my-courses
        self.assertEqual(response.status_code, 302)

    def test_my_courses(self):
        self.client.login(username=self.instructor.email, password=DEFAULT_PASS)
        url = reverse('activities:my-courses')
        response = self.client.get(url)
        # Instructor of course can get access
        self.assertEqual(response.status_code, 200)

    def test_mail_participants_access(self):
        url = self.course.get_custom_mail_instructors_url()

        response = self.client.get(url)
        # anonymous users send emails
        self.assertEqual(response.status_code, 302)

        self.client.login(username=self.other_user.email, password=DEFAULT_PASS)
        response = self.client.get(url)
        # basic logged in users cannot ssend emails
        self.assertEqual(response.status_code, 302)

        self.client.login(username=self.family.email, password=DEFAULT_PASS)
        response = self.client.get(url)
        # members of course cannot send emails
        self.assertEqual(response.status_code, 302)

    @mock.patch('mailer.tasks.send_mail')
    def test_mail_participants(self, mail_method):
        url = self.course.get_custom_mail_instructors_url()
        self.client.login(username=self.instructor.email, password=DEFAULT_PASS)
        response = self.client.get(url)
        # Instructors of course can get access
        self.assertEqual(response.status_code, 200)
        response = self.client.post(url, data={'subject': '1234', 'message': '1234'})
        self.assertEqual(response.status_code, 302)
        preview_url = response.url
        response = self.client.get(preview_url)
        # preview page
        self.assertEqual(response.status_code, 200)
        response = self.client.post(preview_url, data={}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(mail_method.called_once())

    def test_send_documents_access(self):
        url = self.course.get_custom_mail_instructors_url()

        response = self.client.get(url)
        # anonymous users send emails
        self.assertEqual(response.status_code, 302)

        self.client.login(username=self.other_user.email, password=DEFAULT_PASS)
        response = self.client.get(url)
        # basic logged in users cannot ssend emails
        self.assertEqual(response.status_code, 302)

        self.client.login(username=self.family.email, password=DEFAULT_PASS)
        response = self.client.get(url)
        # members of course cannot send emails
        self.assertEqual(response.status_code, 302)

    @mock.patch('mailer.tasks.send_instructors_email')
    def test_send_documents(self, mail_method):
        url = self.course.get_mail_infos_url()
        self.client.login(username=self.instructor.email, password=DEFAULT_PASS)
        response = self.client.get(url)
        # Instructors of course can get access
        self.assertEqual(response.status_code, 200)
        # confirm page
        response = self.client.post(url, data={}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(mail_method.called_once())


class MailUsersViewTest(TestCase):
    def setUp(self):
        super(MailUsersViewTest, self).setUp()
        self.factory = RequestFactory()
        self.instructor = FamilyUserFactory()
        self.course = CourseFactory(instructors=(self.instructor,))
        self.url = reverse('activities:select-participants', kwargs={'course': self.course.pk})

    def test_not_instructor_user(self):
        request = self.factory.post(self.url, data={})
        request.user = FamilyUserFactory()
        response = MailUsersView.as_view()(request, course=self.course.pk)
        # only instructors can use this function
        self.assertEquals(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('login')))

    def test_session_creation(self):
        payload = [u'1', u'2', u'3']
        request = self.factory.post(self.url, data={'data': json.dumps(payload)})
        request.user = self.instructor
        request = add_middleware_to_request(request, SessionMiddleware)
        request.session.save()
        response = MailUsersView.as_view()(request, course=self.course.pk)
        self.assertIn('mail-userids', request.session.keys())
        self.assertEqual(set(request.session['mail-userids']), set(payload))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(response.url.startswith(reverse('login')))


class CustomParticipantsCustomMailViewTest(TestCase):
    def setUp(self):
        super(CustomParticipantsCustomMailViewTest, self).setUp()
        self.factory = RequestFactory()
        self.instructors = FamilyUserFactory.create_batch(3)
        self.instructor = self.instructors[0]
        self.other_users = FamilyUserFactory.create_batch(4)
        self.course = CourseFactory(instructors=self.instructors)
        self.url = reverse('activities:mail-custom-participants-custom', kwargs={'course': self.course.pk})

    def test_not_instructor_user(self):
        request = self.factory.get(self.url, data={})
        request.user = FamilyUserFactory()
        response = CustomParticipantsCustomMailView.as_view()(request, course=self.course.pk)
        # only instructors can use this function
        self.assertEquals(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('login')))

    def test_get(self):
        request = self.factory.get(self.url)
        request.user = self.instructor
        request = add_middleware_to_request(request, SessionMiddleware)
        response = CustomParticipantsCustomMailView.as_view()(request, course=self.course.pk)
        self.assertEqual(response.status_code, 200)

    def test_recipients(self):
        request = self.factory.get(self.url)
        request.user = self.instructor
        request = add_middleware_to_request(request, SessionMiddleware)
        request.session['mail-userids'] = [user.pk for user in self.other_users]
        request.session.save()
        response = CustomParticipantsCustomMailView.as_view()(request, course=self.course.pk)
        self.assertEqual(response.status_code, 200)
        self.assertIn('recipients', response.context_data)
        self.assertEqual(len(response.context_data['recipients']), len(self.other_users))

    def test_post(self):
        data = {'subject': fake.sentence(),
                'message': fake.paragraph()}
        request = self.factory.post(self.url, data=data)
        request.user = self.instructor
        request = add_middleware_to_request(request, SessionMiddleware)
        request.session['mail-userids'] = [user.pk for user in self.other_users]
        request.session.save()
        response = CustomParticipantsCustomMailView.as_view()(request, course=self.course.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('activities:mail-preview', kwargs={'course': self.course.pk}))

    def test_archive_saving(self):
        data = {'subject': fake.sentence(),
                'message': fake.paragraph()}
        request = self.factory.post(self.url, data=data)
        request.user = self.instructor
        request = add_middleware_to_request(request, SessionMiddleware)
        request.session['mail-userids'] = [user.pk for user in self.other_users]
        request.session.save()
        CustomParticipantsCustomMailView.as_view()(request, course=self.course.pk)
        self.assertEqual(MailArchive.objects.count(), 1)
        self.assertIn('mail', request.session)
        archive_id = request.session['mail']
        archive = MailArchive.objects.get(pk=archive_id)
        self.assertEqual(archive.subject, data['subject'])

    def test_nb_recipients(self):
        data = {'subject': fake.sentence(),
                'message': fake.paragraph()}
        request = self.factory.post(self.url, data=data)
        request.user = self.instructor
        request = add_middleware_to_request(request, SessionMiddleware)
        request.session['mail-userids'] = [user.pk for user in self.other_users]
        request.session.save()
        CustomParticipantsCustomMailView.as_view()(request, course=self.course.pk)
        archive = MailArchive.objects.first()
        self.assertEqual(len(archive.recipients), len(self.other_users))
        self.assertEqual(len(archive.bcc_recipients), 0)

    def test_send_copy(self):
        data = {'subject': fake.sentence(),
                'message': fake.paragraph(),
                'send_copy': '1'}
        request = self.factory.post(self.url, data=data)
        request.user = self.instructor
        request = add_middleware_to_request(request, SessionMiddleware)
        request.session['mail-userids'] = [user.pk for user in self.other_users]
        request.session.save()
        CustomParticipantsCustomMailView.as_view()(request, course=self.course.pk)
        archive = MailArchive.objects.first()
        self.assertEqual(len(archive.recipients), len(self.other_users))
        self.assertEqual(len(archive.bcc_recipients), 1)

    def test_send_all_instructors_copy(self):
        data = {'subject': fake.sentence(),
                'message': fake.paragraph(),
                'send_copy': '1',
                'copy_all_instructors': '1'
                }
        request = self.factory.post(self.url, data=data)
        request.user = self.instructor
        request = add_middleware_to_request(request, SessionMiddleware)
        request.session['mail-userids'] = [user.pk for user in self.other_users]
        request.session.save()
        CustomParticipantsCustomMailView.as_view()(request, course=self.course.pk)
        archive = MailArchive.objects.first()
        self.assertEqual(len(archive.recipients), len(self.other_users))
        self.assertEqual(len(archive.bcc_recipients), self.course.instructors.count())


class CustomMailPreviewTest(TestCase):
    def setUp(self):
        super(CustomMailPreviewTest, self).setUp()
        self.factory = RequestFactory()
        self.instructors = FamilyUserFactory.create_batch(2)
        self.instructor = self.instructors[0]
        self.other_users = FamilyUserFactory.create_batch(4)
        self.course = CourseFactory(instructors=self.instructors)
        self.archive = MailArchiveFactory(recipients=[user.pk for user in self.other_users],
                                          bcc_recipients=[user.pk for user in self.instructors],)
        self.url = reverse('activities:mail-preview', kwargs={'course': self.course.pk})

    def test_not_instructor_user(self):
        request = self.factory.get(self.url)
        request.user = FamilyUserFactory()
        response = CustomMailPreview.as_view()(request, course=self.course.pk)
        # only instructors can use this function
        self.assertEquals(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('login')))

    def test_no_archive(self):
        request = self.factory.get(self.url)
        request.user = self.instructor
        request = add_middleware_to_request(request, SessionMiddleware)
        with self.assertRaises(Http404):
            CustomMailPreview.as_view()(request, course=self.course.pk)

    def test_get(self):
        request = self.factory.get(self.url)
        request.user = self.instructor
        request = add_middleware_to_request(request, SessionMiddleware)
        request.session['mail'] = self.archive.pk
        request.session.save()
        response = CustomMailPreview.as_view()(request, course=self.course.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context_data['to_email']), len(self.other_users))
        self.assertEqual(len(response.context_data['bcc_email']), len(self.instructors))

    @mock.patch('mailer.tasks.send_mail.delay')
    def test_post(self, sendmail_method):
        request = self.factory.post(self.url, data={})
        request.user = self.instructor
        request = add_middleware_to_request(request, SessionMiddleware)
        request = add_middleware_to_request(request, MessageMiddleware)
        request.session['mail'] = self.archive.pk
        request.session.save()
        response = CustomMailPreview.as_view()(request, course=self.course.pk)
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('mail', request.session)
        self.assertNotIn('mail-userids', request.session)
        self.assertEqual(sendmail_method.call_count, len(self.instructors) + len(self.other_users))

    @mock.patch('mailer.tasks.send_mail.delay')
    def test_adresses(self, sendmail_method):
        request = self.factory.post(self.url, data={})
        request.user = self.instructor
        request = add_middleware_to_request(request, SessionMiddleware)
        request = add_middleware_to_request(request, MessageMiddleware)
        request.session['mail'] = self.archive.pk
        request.session.save()
        response = CustomMailPreview.as_view()(request, course=self.course.pk)
        self.assertEqual(response.status_code, 302)
        for (args, kwargs) in sendmail_method.call_args_list:
            self.assertIn(self.instructor.email, kwargs['reply_to'][0])


class MailCourseInstructorsViewTest(TestCase):
    def setUp(self):
        super(MailCourseInstructorsViewTest, self).setUp()
        self.factory = RequestFactory()
        self.instructors = FamilyUserFactory.create_batch(2)
        self.instructor = self.instructors[0]
        self.course = CourseFactory(instructors=self.instructors)
        self.url = reverse('activities:mail-instructors', kwargs={'course': self.course.pk})

    def test_not_instructor_user(self):
        request = self.factory.get(self.url)
        request.user = FamilyUserFactory()
        response = MailCourseInstructorsView.as_view()(request, course=self.course.pk)
        # only instructors can use this function
        self.assertEquals(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('login')))

    def test_get(self):
        request = self.factory.get(self.url)
        request.user = self.instructor
        request = add_middleware_to_request(request, SessionMiddleware)
        response = MailCourseInstructorsView.as_view()(request, course=self.course.pk)
        self.assertEqual(response.status_code, 200)

    @mock.patch('mailer.tasks.send_instructors_email.delay')
    def test_post(self, sendmail_method):
        request = self.factory.post(self.url, data={})
        request.user = self.instructor
        request = add_middleware_to_request(request, SessionMiddleware)
        request = add_middleware_to_request(request, MessageMiddleware)
        response = MailCourseInstructorsView.as_view()(request, course=self.course.pk)
        self.assertEqual(response.status_code, 302)

    @mock.patch('mailer.tasks.send_instructors_email.delay')
    def test_send_mail(self, sendmail_method):
        request = self.factory.post(self.url, data={})
        request.user = self.instructor
        request = add_middleware_to_request(request, SessionMiddleware)
        request = add_middleware_to_request(request, MessageMiddleware)
        MailCourseInstructorsView.as_view()(request, course=self.course.pk)
        self.assertEqual(sendmail_method.call_count, 1)

    @mock.patch('mailer.tasks.send_instructors_email.delay')
    def test_send_mail_copy(self, sendmail_method):
        request = self.factory.post(self.url, data={
            'copy_all_instructors': '1'
        })
        request.user = self.instructor
        request = add_middleware_to_request(request, SessionMiddleware)
        request = add_middleware_to_request(request, MessageMiddleware)
        MailCourseInstructorsView.as_view()(request, course=self.course.pk)
        self.assertEqual(sendmail_method.call_count, self.course.instructors.count())
