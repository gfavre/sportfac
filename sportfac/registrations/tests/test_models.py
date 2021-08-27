from datetime import time

from django.test import override_settings

from .factories import ChildFactory, RegistrationFactory
from activities.tests.factories import CourseFactory
from profiles.tests.factories import FamilyUserFactory
from sportfac.utils import TenantTestCase


class RegistrationTestCase(TenantTestCase):
    def setUp(self):
        super(RegistrationTestCase, self).setUp()
        self.user = FamilyUserFactory()
        self.child1 = ChildFactory(family=self.user)
        self.child2 = ChildFactory(family=self.user)
    
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

    @override_settings(KEPCHUP_USE_DIFFERENTIATED_PRICES=True, KEPCHUP_LOCAL_ZIPCODES=['1272'])
    def test_price_category_for_local_siblings(self):
        self.user.zipcode = '1272'
        course1 = CourseFactory()
        course2 = CourseFactory(activity=course1.activity)
        registration1 = RegistrationFactory(course=course1, child=self.child1)
        registration2 = RegistrationFactory(course=course1, child=self.child2)
        price, label = registration2.get_price_category()
        self.assertEqual(price, course2.price_local_family)