from django.test import TestCase
from sportfac.utils import TenantTestCase as TestCase

from .factories import ChildFactory, RegistrationFactory
from activities.tests.factories import CourseFactory
from profiles.tests.factories import FamilyUserFactory, SchoolYearFactory
from schools.tests.factories import TeacherFactory


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
        
        registration1 = RegistrationFactory(course=course1, child=self.child1)
        registration2 = RegistrationFactory(course=course1, child=self.child2)
        
        # different children registering same course is ok
        self.assertFalse(registration1.overlap(registration2))
        self.assertFalse(registration2.overlap(registration1))

        # same child, same course: overlap
        self.assertTrue(registration1.overlap(registration1))
