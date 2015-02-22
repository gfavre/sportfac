#!/usr/bin/python
# -*- coding: utf-8 -*-
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import RequestFactory

from sportfac.middleware import RegistrationOpenedMiddleware
import views

class BackendTestBase(TestCase):
    def setUp(self):
        # Every test needs access to the request factory.
        self.factory = RequestFactory()
        self.user = get_user_model().objects\
                                    .create_user(first_name='Average',
                                                 last_name='Joe',
                                                 zipcode='00000',
                                                 city='Atlantis', 
                                                 email='joe@localhost', 
                                                 password='top_secret')
        self.manager = get_user_model().objects\
                                       .create_user(first_name='M',
                                                    last_name='Anager',
                                                    zipcode='00000',
                                                    city='Atlantis', 
                                                    email='manager@localhost', 
                                                    password='top_secret')
                                                    
        self.manager.is_manager = True

    
    def generic_test_rights(self, url, view):
        request = self.factory.get(url)
        RegistrationOpenedMiddleware().process_request(request)
        request.user = AnonymousUser()
        response = view(request)
        self.assertEqual(response.status_code, 302)
        request.user = self.user
        response = view(request)
        self.assertEqual(response.status_code, 302)
        request.user = self.manager
        response = view(request)
        self.assertEqual(response.status_code, 200)

      
class CourseViewsTests(BackendTestBase):
        
    def test_list(self):
        url = reverse('backend:course-list')
        view = views.CourseListView.as_view()
        self.generic_test_rights(url, view)
    
    def test_create(self):
        url = reverse('backend:course-create')
        view = views.CourseCreateView.as_view()
        self.generic_test_rights(url, view)


class ActivitiesViewsTests(BackendTestBase):
        
    def test_list(self):
        url = reverse('backend:activity-list')
        view = views.ActivityListView.as_view()
        self.generic_test_rights(url, view)
    
    def test_create(self):
        url = reverse('backend:activity-create')
        view = views.ActivityCreateView.as_view()
        self.generic_test_rights(url, view)


class TeachersViewsTests(BackendTestBase):
        
    def test_list(self):
        url = reverse('backend:teacher-list')
        view = views.TeacherListView.as_view()
        self.generic_test_rights(url, view)
    
    def test_create(self):
        url = reverse('backend:teacher-create')
        view = views.TeacherCreateView.as_view()
        self.generic_test_rights(url, view)


class UsersViewsTests(BackendTestBase):
        
    def test_list(self):
        url = reverse('backend:user-list')
        view = views.UserListView.as_view()
        self.generic_test_rights(url, view)

    def test_managers_list(self):
        url = reverse('backend:manager-list')
        view = views.ManagerListView.as_view()
        self.generic_test_rights(url, view)

    def test_responsible_list(self):
        url = reverse('backend:responsible-list')
        view = views.ResponsibleListView.as_view()
        self.generic_test_rights(url, view)
    
    def test_create(self):
        url = reverse('backend:user-create')
        view = views.UserCreateView.as_view()
        self.generic_test_rights(url, view)

    def test_create_manager(self):
        url = reverse('backend:manager-create')
        view = views.ManagerCreateView.as_view()
        self.generic_test_rights(url, view)



class RegistrationsViewsTests(BackendTestBase):
        
    def test_list(self):
        url = reverse('backend:registration-list')
        view = views.RegistrationListView.as_view()
        self.generic_test_rights(url, view)
    
    def test_create(self):
        url = reverse('backend:registration-create')
        view = views.RegistrationCreateView.as_view()
        self.generic_test_rights(url, view)



class MailViewsTests(BackendTestBase):
        
    def test_list(self):
        url = reverse('backend:archive')
        view = views.MailArchiveListView.as_view()
        self.generic_test_rights(url, view)
    
    def test_confirmation(self):
        url = reverse('backend:mail-needconfirmation')
        view = views.NeedConfirmationView.as_view()
        self.generic_test_rights(url, view)
        
    def test_notpaid(self):
        url = reverse('backend:mail-notpaidyet')
        view = views.NotPaidYetView.as_view()
        self.generic_test_rights(url, view)        
        
    def test_custom(self):
        url = reverse('backend:custom-mail-custom-users')
        view = views.CustomUserCustomMailCreateView.as_view()
        self.generic_test_rights(url, view)        
        
        