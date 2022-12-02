# -*- coding: utf-8 -*-
from __future__ import absolute_import
from datetime import time

from django.test import override_settings

from faker import Faker

from activities.tests.factories import AllocationAccountFactory, CourseFactory
from profiles.tests.factories import CityFactory, FamilyUserFactory
from sportfac.utils import TenantTestCase
from .factories import BillFactory, ChildFactory, RegistrationFactory

fake = Faker(locale='fr_CH')


class RegistrationTestCase(TenantTestCase):
    def setUp(self):
        super(RegistrationTestCase, self).setUp()
        self.user = FamilyUserFactory()
        self.child1 = ChildFactory(family=self.user)
        self.child2 = ChildFactory(family=self.user)
        self.price = fake.pyint(50, 150)
        self.price_local = self.price - 10
        self.price_family = self.price_local
        self.price_local_family = self.price_local - 10

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
        self.user.zipcode = "1271"
        course = CourseFactory(
            price=self.price, price_local=self.price_local,
            price_family=self.price_family, price_local_family=self.price_local_family
        )
        registration = RegistrationFactory(course=course, child=self.child1)
        self.assertEqual(registration.price, self.price)

    @override_settings(KEPCHUP_USE_DIFFERENTIATED_PRICES=True, KEPCHUP_LOCAL_ZIPCODES=['1272'])
    def test_price_category_for_family(self):
        self.user.zipcode = "1271"
        course1 = CourseFactory(
            price=self.price, price_local=self.price_local,
            price_family=self.price_family, price_local_family=self.price_local_family
        )
        course2 = CourseFactory(
            activity=course1.activity,
            price=self.price, price_local=self.price_local,
            price_family=self.price_family, price_local_family=self.price_local_family
        )
        registration1 = RegistrationFactory(course=course1, child=self.child1)
        registration2 = RegistrationFactory(course=course2, child=self.child2)
        self.assertEqual(registration1.price, self.price)
        self.assertEqual(registration2.price, self.price_family)

    @override_settings(KEPCHUP_USE_DIFFERENTIATED_PRICES=True, KEPCHUP_LOCAL_ZIPCODES=['1272'])
    def test_price_category_for_local(self):
        self.user.zipcode = "1272"
        course = CourseFactory(
            price=self.price, price_local=self.price_local,
            price_family=self.price_family, price_local_family=self.price_local_family
        )
        registration = RegistrationFactory(course=course, child=self.child1)
        self.assertEqual(registration.price, self.price_local)

    @override_settings(KEPCHUP_USE_DIFFERENTIATED_PRICES=True)
    def test_price_category_for_local_with_override(self):
        city = CityFactory()
        self.user.zipcode = city.zipcode
        course = CourseFactory(
            price=self.price, price_local=self.price_local,
            price_family=self.price_family, price_local_family=self.price_local_family
        )
        course.local_city_override.add(city)
        registration = RegistrationFactory(course=course, child=self.child1)
        self.assertEqual(registration.price, self.price_local)

    @override_settings(KEPCHUP_USE_DIFFERENTIATED_PRICES=True, KEPCHUP_LOCAL_ZIPCODES=['1272'])
    def test_price_category_for_local_siblings(self):
        self.user.zipcode = "1272"
        course1 = CourseFactory(
            price=self.price, price_local=self.price_local,
            price_family=self.price_family, price_local_family=self.price_local_family
        )
        course2 = CourseFactory(
            activity=course1.activity,
            price=self.price, price_local=self.price_local,
            price_family=self.price_family, price_local_family=self.price_local_family
        )
        registration1 = RegistrationFactory(course=course1, child=self.child1)
        registration2 = RegistrationFactory(course=course2, child=self.child2)
        self.assertEqual(registration1.price, self.price_local)
        self.assertEqual(registration2.price, self.price_local_family)

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


class BillTestCase(TenantTestCase):
    def setUp(self):
        self.bill = BillFactory()

    def test_code_for_reasonably_long_names(self):
        self.bill.family.last_name = u'Bartholomey-Bolay'
        self.bill.update_billing_identifier()
        self.assertTrue(len(self.bill.billing_identifier) <= 20)

    def test_code_for_non_secable_long_names(self):
        self.bill.family.last_name = u'Wolfeschlegelsteinhausenbergerdorff'
        self.bill.update_billing_identifier()

        self.assertTrue(len(self.bill.billing_identifier) <= 20)
        self.assertIn(self.bill.family.last_name.lower()[10], self.bill.billing_identifier)

    def test_code_for_secable_long_names(self):
        self.bill.family.last_name = u'Diego José Francisco de Paula Juan Nepomuceno María de los Remedios Cipriano de la Santísima Trinidad Ruiz y Picasso'
        self.bill.update_billing_identifier()
        self.assertTrue(len(self.bill.billing_identifier) <= 20)
        self.assertIn(self.bill.family.last_name.split(' ')[0].lower(), self.bill.billing_identifier)
