from django.core.urlresolvers import reverse

import mock

from .factories import ActivityFactory, CourseFactory
from mailer.views import MailMixin
from profiles.tests.factories import FamilyUserFactory, SchoolYearFactory, DEFAULT_PASS
from registrations.tests.factories import ChildFactory, RegistrationFactory
from sportfac.utils import TenantTestCase as TestCase

from profiles.models import SchoolYear

class ActivityViewsTests(TestCase):
    def setUp(self):
        super(ActivityViewsTests, self).setUp()
        self.activity = ActivityFactory()
        self.user = FamilyUserFactory()

    def tearDown(self):
        pass

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

    @mock.patch.object(MailMixin, 'mail')
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
        url = self.course.get_custom_mail_rinstructors_url()
     
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
        self.client.login(username=self.instructor.email, password=DEFAULT_PASS)
        response = self.client.get(url)
        # Instructors of course can get access
        self.assertEqual(response.status_code, 200)
        # confirm page
        response = self.client.post(url, data={}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(mail_method.called_once())
