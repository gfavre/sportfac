from datetime import time

from django.test import override_settings

from activities.tests.factories import CourseFactory, AllocationAccountFactory
from profiles.tests.factories import CityFactory, FamilyUserFactory
from sportfac.utils import TenantTestCase
from .factories import ChildFactory, RegistrationFactory


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

    @override_settings(KEPCHUP_USE_DIFFERENTIATED_PRICES=False, KEPCHUP_LOCAL_ZIPCODES=['1272'])
    def test_get_price_category_no_differentiated_prices(self):
        self.user.zipcode = '1272'
        course1 = CourseFactory()
        course2 = CourseFactory(activity=course1.activity)
        registration1 = RegistrationFactory(course=course1, child=self.child1)
        registration2 = RegistrationFactory(course=course2, child=self.child2)
        price, label = registration2.get_price_category()
        self.assertEqual(price, course2.price)

    @override_settings(KEPCHUP_USE_DIFFERENTIATED_PRICES=True, KEPCHUP_LOCAL_ZIPCODES=['1272'])
    def test_price_category_for_normal_people(self):
        self.user.zipcode = '1271'
        course = CourseFactory()
        registration = RegistrationFactory(course=course, child=self.child1)
        price, label = registration.get_price_category()
        self.assertEqual(price, course.price)

    @override_settings(KEPCHUP_USE_DIFFERENTIATED_PRICES=True, KEPCHUP_LOCAL_ZIPCODES=['1272'])
    def test_price_category_for_family(self):
        self.user.zipcode = '1271'
        course1 = CourseFactory()
        course2 = CourseFactory(activity=course1.activity)
        registration1 = RegistrationFactory(course=course1, child=self.child1)
        registration2 = RegistrationFactory(course=course2, child=self.child2)
        price, label = registration2.get_price_category()
        self.assertEqual(price, course2.price_family)

    @override_settings(KEPCHUP_USE_DIFFERENTIATED_PRICES=True, KEPCHUP_LOCAL_ZIPCODES=['1272'])
    def test_price_category_for_local(self):
        self.user.zipcode = '1272'
        course = CourseFactory()
        registration = RegistrationFactory(course=course, child=self.child1)
        price, label = registration.get_price_category()
        self.assertEqual(price, course.price_local)

    @override_settings(KEPCHUP_USE_DIFFERENTIATED_PRICES=True)
    def test_price_category_for_local_with_override(self):
        city = CityFactory()
        self.user.zipcode = city.zipcode
        course = CourseFactory()
        course.local_city_override.add(city)
        registration = RegistrationFactory(course=course, child=self.child1)
        price, label = registration.get_price_category()
        self.assertEqual(price, course.price_local)

    @override_settings(KEPCHUP_USE_DIFFERENTIATED_PRICES=True, KEPCHUP_LOCAL_ZIPCODES=['1272'])
    def test_price_category_for_local_siblings(self):
        self.user.zipcode = '1272'
        course1 = CourseFactory()
        course2 = CourseFactory(activity=course1.activity)
        registration1 = RegistrationFactory(course=course1, child=self.child1)
        registration2 = RegistrationFactory(course=course2, child=self.child2)
        price, label = registration2.get_price_category()
        self.assertEqual(price, course2.price_local_family)

    @override_settings(KEPCHUP_ENABLE_ALLOCATION_ACCOUNTS=True)
    def test_save_sets_allocation_account(self):
        account = AllocationAccountFactory()
        course = CourseFactory(activity__allocation_account=account)
        registration = RegistrationFactory(course=course)
        registration.allocation_account = None
        registration.save()
        registration.refresh_from_db()
        self.assertEqual(registration.allocation_account, account)

    @override_settings(KEPCHUP_NO_PAYMENT=False)
    def test_save_sets_price(self):
        registration = RegistrationFactory()
        registration.price = None
        registration.save()
        registration.refresh_from_db()
        self.assertEqual(registration.price, registration.course.price)
