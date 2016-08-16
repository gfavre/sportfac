# -*- coding: utf-8 -*-
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.urlresolvers import reverse
from django.test.client import RequestFactory

from activities.tests.factories import CourseFactory
from profiles.tests.factories import FamilyUserFactory, SchoolYearFactory, DEFAULT_PASS
from registrations.models import Bill
from registrations.tests.factories import RegistrationFactory, ChildFactory, BillFactory
from sportfac.utils import TenantTestCase


class BackendTestBase(TenantTestCase):
    def setUp(self):
        super(BackendTestBase, self).setUp()
        self.factory = RequestFactory()
        self.user = FamilyUserFactory()
        self.manager = FamilyUserFactory()           
        self.manager.is_manager = True
    
    def generic_test_rights(self, url):
        # anonymous access
        response = self.tenant_client.get(url)
        self.assertEqual(response.status_code, 302)

        # basic user access        
        self.tenant_client.login(username=self.user.email, password=DEFAULT_PASS)
        response = self.tenant_client.get(url)
        self.assertEqual(response.status_code, 302)
        
        # manager access
        self.tenant_client.login(username=self.manager.email, password=DEFAULT_PASS)
        response = self.tenant_client.get(url)        
        self.assertEqual(response.status_code, 200)

      
class CourseViewsTests(BackendTestBase):
        
    def test_list(self):
        url = reverse('backend:course-list')
        self.generic_test_rights(url)
    
    def test_create(self):
        url = reverse('backend:course-create')
        self.generic_test_rights(url)


class ActivitiesViewsTests(BackendTestBase):
        
    def test_list(self):
        url = reverse('backend:activity-list')
        self.generic_test_rights(url)
    
    def test_create(self):
        url = reverse('backend:activity-create')
        self.generic_test_rights(url)


class TeachersViewsTests(BackendTestBase):
        
    def test_list(self):
        url = reverse('backend:teacher-list')
        self.generic_test_rights(url)
    
    def test_create(self):
        url = reverse('backend:teacher-create')
        self.generic_test_rights(url)


class UsersViewsTests(BackendTestBase):
        
    def test_list(self):
        url = reverse('backend:user-list')
        self.generic_test_rights(url)

    def test_managers_list(self):
        url = reverse('backend:manager-list')
        self.generic_test_rights(url)

    def test_instructors_list(self):
        url = reverse('backend:instructor-list')
        self.generic_test_rights(url)
    
    def test_create(self):
        url = reverse('backend:user-create')
        self.generic_test_rights(url)

    def test_create_manager(self):
        url = reverse('backend:manager-create')
        self.generic_test_rights(url)



class RegistrationsViewsTests(BackendTestBase):
        
    def test_list(self):
        url = reverse('backend:registration-list')
        self.generic_test_rights(url)
    
    def test_create(self):
        url = reverse('backend:registration-create')
        self.generic_test_rights(url)



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
        
        