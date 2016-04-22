"""
Tests for profiles app.
"""
from datetime import time
from django.test import TestCase
from django.contrib.auth.models import Group

from profiles.models import Registration, Child, SchoolYear, FamilyUser
from backend import MANAGERS_GROUP
from activities.models import Course

from .factories.users import FamilyUserFactory, SchoolYearFactory, TeacherFactory, ChildFactory
from .factories.registrations import RegistrationFactory
from activities.tests.factories import CourseFactory

class RegistrationTestCase(TestCase):
    def setUp(self):
        self.user = FamilyUserFactory()
        self.year = SchoolYearFactory()
        self.teacher = TeacherFactory()
        self.teacher.years.add(self.year)
        self.child1 = ChildFactory(school_year=self.year, teacher=self.teacher, family=self.user)
        self.child2 = ChildFactory(school_year=self.year, teacher=self.teacher, family=self.user)
    
    def test_overlap(self):
        """
        Tests overlapping detection
        """
        course1 = CourseFactory(day=1, 
                                start_time=time(hour=12, minute=0), 
                                end_time=time(hour=13, minute=0))
        same_hour = CourseFactory(day=1, 
                                  start_time=time(hour=12, minute=0), 
                                  end_time=time(hour=13, minute=0))
        quarter_later = CourseFactory(day=1, 
                                      start_time=time(hour=12, minute=15), 
                                      end_time=time(hour=13, minute=0))
        
        RegistrationFactory
        registration1 = RegistrationFactory(course=course1, child=self.child1)
        registration2 = RegistrationFactory(course=course1, child=self.child2)
        
        # different children registering same course is ok
        self.assertFalse(registration1.overlap(registration2))
        self.assertFalse(registration2.overlap(registration1))

        # same child, same course: overlap
        self.assertTrue(registration1.overlap(registration1))
        
class FamilyUserTestCase(TestCase):

    def setUp(self):
        self.superuser = FamilyUserFactory(is_superuser=True, is_admin=True)
        self.admin = FamilyUserFactory(is_admin=True)
        self.manager = FamilyUserFactory()
        managers, created = Group.objects.get_or_create(name=MANAGERS_GROUP)
        self.manager.groups.add(managers)
        self.user = FamilyUserFactory()
    
    def test_manager_rights(self):
        self.assertTrue(self.superuser.is_manager)
        self.assertTrue(self.admin.is_manager)
        self.assertTrue(self.manager.is_manager)
        self.assertFalse(self.user.is_manager)
           
