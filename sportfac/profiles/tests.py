"""
Tests for profiles app.
"""
from datetime import time
from django.test import TestCase
from django.contrib.auth.models import Group

#from django_dynamic_fixture import G

from .models import Registration, Child, SchoolYear, FamilyUser
from backend import MANAGERS_GROUP
from activities.models import Course

class RegistrationTestCase(TestCase):
    
    def test_overlap(self):
        """
        Tests overlapping detection
        """
        year = G(SchoolYear)
        child1, child2 = G(Child, school_year=year), G(Child, school_year=year)
        
        course1 = G(Course, day=1, start_time=time(hour=12, minute=0), 
                                   end_time=time(hour=13, minute=0))
        same_hour = G(Course, day=1, start_time=time(hour=12, minute=0), 
                                   end_time=time(hour=13, minute=0))
        quarter_later = G(Course, day=1, start_time=time(hour=12, minute=15), 
                                   end_time=time(hour=13, minute=0))
        course3 = G(Course, day=1, start_time=time(hour=15, minute=0), 
                                   end_time=time(hour=13, minute=0))
        course4 = G(Course, day=2, start_time=time(hour=11, minute=0), 
                                   end_time=time(hour=13, minute=0))
                                        
        registration1 = G(Registration, course=course1, child=child1)
        registration2 = G(Registration, course=course1, child=child2)
        
        
        # different children registering same course is ok
        self.assertFalse(registration1.overlap(registration2))
        self.assertFalse(registration2.overlap(registration1))

        # same child, same course: overlap
        self.assertTrue(registration1.overlap(registration1))
        
        # Courses 
        registration3 = G(Registration, course=same_hour, child=child1)
        self.assertTrue(registration1.overlap(registration3))

        
        
class FamilyUserTestCase(TestCase):

    def setUp(self):
        self.superuser = FamilyUser.objects.create(
                            email='superadmin@site.com',
                            first_name='superadmin',
                            last_name='superadmin',
                            zipcode=1000,
                            city='Lausanne',
                            is_superuser=True,
                            is_admin=True)
        self.admin = FamilyUser.objects.create(
                            email='admin@site.com',
                            first_name='admin',
                            last_name='admin',
                            zipcode=1000,
                            city='Lausanne',
                            is_superuser=False,
                            is_admin=True)
        self.manager = FamilyUser.objects.create(
                            email='manager@site.com',
                            first_name='manager',
                            last_name='manager',
                            zipcode=1000,
                            city='Lausanne',
                            is_superuser=False,
                            is_admin=False)
        managers, created = Group.objects.get_or_create(name=MANAGERS_GROUP)
        self.manager.groups.add(managers)
        
        self.user = FamilyUser.objects.create(
                            email='user@site.com',
                            first_name='user',
                            last_name='user',
                            zipcode=1000,
                            city='Lausanne',
                            is_superuser=False,
                            is_admin=False)
        
        
    
    def test_manager_rights(self):
        self.assertTrue(self.superuser.is_manager)
        self.assertTrue(self.admin.is_manager)
        self.assertTrue(self.manager.is_manager)
        self.assertFalse(self.user.is_manager)
           
