"""
Tests for profiles app.
"""
from datetime import time
from django.test import TestCase

from django_dynamic_fixture import G

from .models import Registration, Child, SchoolYear
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

        
        
        
