from django.core.urlresolvers import reverse
from django.test import TestCase, override_settings

import mock

from mailer.views import MailMixin
from .factories import ActivityFactory, CourseFactory
from profiles.tests.factories.users import ChildFactory, FamilyUserFactory, DEFAULT_PASS
from profiles.tests.factories.registrations import RegistrationFactory

class ActivityViewsTests(TestCase):
    def setUp(self):
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
        registration=RegistrationFactory(child=child, course=course)
        url = self.activity.get_absolute_url()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        

class CourseViewsTests(TestCase):
    def setUp(self):
        self.responsible = FamilyUserFactory()
        self.course = CourseFactory(responsible=self.responsible)
        self.family = FamilyUserFactory()
        self.child = ChildFactory(family=self.family)
        self.registration = RegistrationFactory(course=self.course, child=self.child)
        self.other_user = FamilyUserFactory()
    
    def test_detail_access(self):
        url = self.course.get_absolute_url()
        response = self.client.get(url)
        #anonymous users cannot see details
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
        self.client.login(username=self.responsible.email, password=DEFAULT_PASS)
        url = reverse('activities:my-courses')
        response = self.client.get(url)
        # Responsible of course can get access
        self.assertEqual(response.status_code, 200)
        
    def test_mail_participants_access(self):
        url = self.course.get_custom_mail_responsible_url()
        
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

    @mock.patch.object(MailMixin, 'mail')
    def test_mail_participants(self, mail_method):
        url = self.course.get_custom_mail_responsible_url()
        self.client.login(username=self.responsible.email, password=DEFAULT_PASS)
        response = self.client.get(url)
        # Responsible of course can get access
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
        url = self.course.get_custom_mail_responsible_url()
     
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
    
    @mock.patch.object(MailMixin, 'mail')
    def test_send_documents(self, mail_method):
        url = self.course.get_mail_infos_url()
        self.client.login(username=self.responsible.email, password=DEFAULT_PASS)
        response = self.client.get(url)
        # Responsible of course can get access
        self.assertEqual(response.status_code, 200)
        # confirm page
        response = self.client.post(url, data={}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(mail_method.called_once())
