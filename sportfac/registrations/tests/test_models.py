from datetime import time

from django.test import override_settings
from dynamic_preferences.registries import global_preferences_registry
from faker import Faker

from activities.tests.factories import AllocationAccountFactory
from activities.tests.factories import CourseFactory
from profiles.tests.factories import CityFactory
from profiles.tests.factories import FamilyUserFactory
from sportfac.utils import TenantTestCase

from .factories import BillFactory
from .factories import ChildFactory
from .factories import RegistrationFactory


fake = Faker(locale="fr_CH")


class RegistrationTestCase(TenantTestCase):
    def setUp(self):
        super().setUp()
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
        course1 = CourseFactory(day=1, start_time=time(hour=12, minute=0), end_time=time(hour=13, minute=0))
        # same_hour = CourseFactory(day=1, start_time=time(hour=12, minute=0), end_time=time(hour=13, minute=0))
        # quarter_later = CourseFactory(day=1, start_time=time(hour=12, minute=15), end_time=time(hour=13, minute=0))

        registration1 = RegistrationFactory(course=course1, child=self.child1)
        registration2 = RegistrationFactory(course=course1, child=self.child2)

        # different children registering same course is ok
        self.assertFalse(registration1.overlap(registration2))
        self.assertFalse(registration2.overlap(registration1))

        # same child, same course: overlap
        self.assertTrue(registration1.overlap(registration1))

    @override_settings(KEPCHUP_PRICING_MODE="simple", KEPCHUP_LOCAL_ZIPCODES=["1272"])
    def test_get_price_category_no_differentiated_prices(self):
        self.user.zipcode = "1272"
        course1 = CourseFactory()
        course2 = CourseFactory(activity=course1.activity)
        RegistrationFactory(course=course1, child=self.child1)
        registration2 = RegistrationFactory(course=course2, child=self.child2)
        price, label = registration2.get_price_category()
        self.assertEqual(price, course2.price)

    @override_settings(KEPCHUP_PRICING_MODE="family_local", KEPCHUP_LOCAL_ZIPCODES=["1272"])
    def test_price_category_for_normal_people(self):
        self.user.zipcode = "1271"
        course = CourseFactory(
            price=self.price,
            price_local=self.price_local,
            price_family=self.price_family,
            price_local_family=self.price_local_family,
        )
        registration = RegistrationFactory(course=course, child=self.child1)
        self.assertEqual(registration.price, self.price)

    @override_settings(KEPCHUP_PRICING_MODE="family_local", KEPCHUP_LOCAL_ZIPCODES=["1272"])
    def test_price_category_for_family(self):
        self.user.zipcode = "1271"
        course1 = CourseFactory(
            price=self.price,
            price_local=self.price_local,
            price_family=self.price_family,
            price_local_family=self.price_local_family,
        )
        course2 = CourseFactory(
            activity=course1.activity,
            price=self.price,
            price_local=self.price_local,
            price_family=self.price_family,
            price_local_family=self.price_local_family,
        )
        registration1 = RegistrationFactory(course=course1, child=self.child1)
        registration2 = RegistrationFactory(course=course2, child=self.child2)
        self.assertEqual(registration1.price, self.price)
        self.assertEqual(registration2.price, self.price_family)

    @override_settings(KEPCHUP_PRICING_MODE="family_local", KEPCHUP_LOCAL_ZIPCODES=["1272"])
    def test_price_category_for_local(self):
        self.user.zipcode = "1272"
        course = CourseFactory(
            price=self.price,
            price_local=self.price_local,
            price_family=self.price_family,
            price_local_family=self.price_local_family,
        )
        registration = RegistrationFactory(course=course, child=self.child1)
        self.assertEqual(registration.price, self.price_local)

    @override_settings(KEPCHUP_PRICING_MODE="family_local")
    def test_price_category_for_local_with_override(self):
        city = CityFactory()
        self.user.zipcode = city.zipcode
        course = CourseFactory(
            price=self.price,
            price_local=self.price_local,
            price_family=self.price_family,
            price_local_family=self.price_local_family,
        )
        course.local_city_override.add(city)
        registration = RegistrationFactory(course=course, child=self.child1)
        self.assertEqual(registration.price, self.price_local)

    @override_settings(KEPCHUP_PRICING_MODE="family_local", KEPCHUP_LOCAL_ZIPCODES=["1272"])
    def test_price_category_for_local_siblings(self):
        self.user.zipcode = "1272"
        course1 = CourseFactory(
            price=self.price,
            price_local=self.price_local,
            price_family=self.price_family,
            price_local_family=self.price_local_family,
        )
        course2 = CourseFactory(
            activity=course1.activity,
            price=self.price,
            price_local=self.price_local,
            price_family=self.price_family,
            price_local_family=self.price_local_family,
        )
        registration1 = RegistrationFactory(course=course1, child=self.child1)
        registration2 = RegistrationFactory(course=course2, child=self.child2)
        self.assertEqual(registration1.price, self.price_local)
        self.assertEqual(registration2.price, self.price_local_family)

    @override_settings(KEPCHUP_PRICING_MODE="family_local", KEPCHUP_LOCAL_ZIPCODES=[("1820", "Montreux")])
    def test_price_category_for_local_zipcode_city_tuple_match(self):
        self.user.zipcode = "1820"
        self.user.city = "Montreux"
        course = CourseFactory(
            price=self.price,
            price_local=self.price_local,
            price_family=self.price_family,
            price_local_family=self.price_local_family,
        )
        registration = RegistrationFactory(course=course, child=self.child1)
        self.assertEqual(registration.price, self.price_local)

    @override_settings(KEPCHUP_PRICING_MODE="family_local", KEPCHUP_LOCAL_ZIPCODES=[("1820", "Montreux")])
    def test_price_category_for_non_local_same_zipcode_different_city(self):
        self.user.zipcode = "1820"
        self.user.city = "Veytaux"
        course = CourseFactory(
            price=self.price,
            price_local=self.price_local,
            price_family=self.price_family,
            price_local_family=self.price_local_family,
        )
        registration = RegistrationFactory(course=course, child=self.child1)
        self.assertEqual(registration.price, self.price)

    @override_settings(KEPCHUP_PRICING_MODE="family_local", KEPCHUP_LOCAL_ZIPCODES=[("1820", "Montreux")])
    def test_price_category_for_local_city_case_insensitive(self):
        self.user.zipcode = "1820"
        self.user.city = "MONTREUX"
        course = CourseFactory(
            price=self.price,
            price_local=self.price_local,
            price_family=self.price_family,
            price_local_family=self.price_local_family,
        )
        registration = RegistrationFactory(course=course, child=self.child1)
        self.assertEqual(registration.price, self.price_local)

    @override_settings(
        KEPCHUP_PRICING_MODE="family_local",
        KEPCHUP_LOCAL_ZIPCODES=["1814", ("1820", "Montreux"), ("1820", "Territet")],
    )
    def test_price_category_mixed_format_plain_zipcode(self):
        self.user.zipcode = "1814"
        self.user.city = "La Tour-de-Peilz"
        course = CourseFactory(
            price=self.price,
            price_local=self.price_local,
            price_family=self.price_family,
            price_local_family=self.price_local_family,
        )
        registration = RegistrationFactory(course=course, child=self.child1)
        self.assertEqual(registration.price, self.price_local)

    @override_settings(
        KEPCHUP_PRICING_MODE="family_local",
        KEPCHUP_LOCAL_ZIPCODES=["1814", ("1820", "Montreux"), ("1820", "Territet")],
    )
    def test_price_category_mixed_format_tuple_match(self):
        self.user.zipcode = "1820"
        self.user.city = "Territet"
        course = CourseFactory(
            price=self.price,
            price_local=self.price_local,
            price_family=self.price_family,
            price_local_family=self.price_local_family,
        )
        registration = RegistrationFactory(course=course, child=self.child1)
        self.assertEqual(registration.price, self.price_local)

    @override_settings(
        KEPCHUP_PRICING_MODE="family_local",
        KEPCHUP_LOCAL_ZIPCODES=["1814", ("1820", "Montreux"), ("1820", "Territet")],
    )
    def test_price_category_mixed_format_non_local(self):
        self.user.zipcode = "1820"
        self.user.city = "Veytaux"
        course = CourseFactory(
            price=self.price,
            price_local=self.price_local,
            price_family=self.price_family,
            price_local_family=self.price_local_family,
        )
        registration = RegistrationFactory(course=course, child=self.child1)
        self.assertEqual(registration.price, self.price)

    @override_settings(KEPCHUP_PRICING_MODE="family")
    def test_price_category_family_mode_first_child(self):
        course = CourseFactory(price=self.price, price_family=self.price_family)
        registration = RegistrationFactory(course=course, child=self.child1)
        self.assertEqual(registration.price, self.price)

    @override_settings(KEPCHUP_PRICING_MODE="family")
    def test_price_category_family_mode_second_child(self):
        course1 = CourseFactory(price=self.price, price_family=self.price_family)
        course2 = CourseFactory(activity=course1.activity, price=self.price, price_family=self.price_family)
        registration1 = RegistrationFactory(course=course1, child=self.child1)
        registration2 = RegistrationFactory(course=course2, child=self.child2)
        self.assertEqual(registration1.price, self.price)
        self.assertEqual(registration2.price, self.price_family)

    @override_settings(KEPCHUP_PRICING_MODE="family_local_3_levels", KEPCHUP_LOCAL_ZIPCODES=["1272"])
    def test_price_category_3_levels_external(self):
        self.user.zipcode = "1271"
        child3 = ChildFactory(family=self.user)
        child4 = ChildFactory(family=self.user)
        price_family_3rd = self.price_family - 10
        courses = [
            CourseFactory(
                price=self.price,
                price_local=self.price_local,
                price_family=self.price_family,
                price_local_family=self.price_local_family,
                price_family_3rd=price_family_3rd,
                price_local_family_3rd=price_family_3rd - 10,
            )
        ]
        courses += [
            CourseFactory(
                activity=courses[0].activity,
                price=self.price,
                price_local=self.price_local,
                price_family=self.price_family,
                price_local_family=self.price_local_family,
                price_family_3rd=price_family_3rd,
                price_local_family_3rd=price_family_3rd - 10,
            )
            for __ in range(3)
        ]
        registrations = [
            RegistrationFactory(course=course, child=child)
            for course, child in zip(courses, [self.child1, self.child2, child3, child4])
        ]
        self.assertEqual(registrations[0].price, self.price)
        self.assertEqual(registrations[1].price, self.price_family)
        self.assertEqual(registrations[2].price, price_family_3rd)
        self.assertEqual(registrations[3].price, price_family_3rd)

    @override_settings(KEPCHUP_PRICING_MODE="family_local_3_levels", KEPCHUP_LOCAL_ZIPCODES=["1272"])
    def test_price_category_3_levels_local(self):
        self.user.zipcode = "1272"
        child3 = ChildFactory(family=self.user)
        price_local_family_3rd = self.price_local_family - 10
        courses = [
            CourseFactory(
                price=self.price,
                price_local=self.price_local,
                price_family=self.price_family,
                price_local_family=self.price_local_family,
                price_family_3rd=self.price_family - 10,
                price_local_family_3rd=price_local_family_3rd,
            )
        ]
        courses += [
            CourseFactory(
                activity=courses[0].activity,
                price=self.price,
                price_local=self.price_local,
                price_family=self.price_family,
                price_local_family=self.price_local_family,
                price_family_3rd=self.price_family - 10,
                price_local_family_3rd=price_local_family_3rd,
            )
            for __ in range(2)
        ]
        registrations = [
            RegistrationFactory(course=course, child=child)
            for course, child in zip(courses, [self.child1, self.child2, child3])
        ]
        self.assertEqual(registrations[0].price, self.price_local)
        self.assertEqual(registrations[1].price, self.price_local_family)
        self.assertEqual(registrations[2].price, price_local_family_3rd)

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
        self.bill.family.last_name = "Bartholomey-Bolay"
        self.bill.update_billing_identifier()
        self.assertTrue(len(self.bill.billing_identifier) <= 20)

    def test_code_for_non_secable_long_names(self):
        self.bill.family.last_name = "Wolfeschlegelsteinhausenbergerdorff"
        self.bill.update_billing_identifier()

        self.assertTrue(len(self.bill.billing_identifier) <= 20)
        self.assertIn(self.bill.family.last_name.lower()[10], self.bill.billing_identifier)

    def test_code_for_secable_long_names(self):
        self.bill.family.last_name = (
            "Diego José Francisco de Paula Juan Nepomuceno María de "
            "los Remedios Cipriano de la Santísima Trinidad Ruiz y Picasso"
        )
        self.bill.update_billing_identifier()
        self.assertTrue(len(self.bill.billing_identifier) <= 20)
        self.assertIn(self.bill.family.last_name.split(" ")[0].lower(), self.bill.billing_identifier)

    def test_qr_invoice_empty_without_payment_preferences(self):
        preferences = global_preferences_registry.manager()
        preferences["payment__IBAN"] = ""
        preferences["payment__ADDRESS"] = ""
        self.bill.payment_method = self.bill.METHODS.iban
        self.bill.save()
        self.assertEqual(self.bill.qr_invoice, "")

    def test_qr_invoice_generated_for_wire_transfer(self):
        preferences = global_preferences_registry.manager()
        preferences["payment__IBAN"] = "CH9300762011623852957"
        preferences["payment__ADDRESS"] = "Commune de Coppet\nGrand-Rue 34\n1296 Coppet"
        self.bill.payment_method = self.bill.METHODS.iban
        self.bill.save()
        self.assertIn("<svg", self.bill.qr_invoice)

    def test_qr_invoice_empty_for_non_wire_transfer(self):
        preferences = global_preferences_registry.manager()
        preferences["payment__IBAN"] = "CH9300762011623852957"
        preferences["payment__ADDRESS"] = "Commune de Coppet\nGrand-Rue 34\n1296 Coppet"
        self.bill.payment_method = self.bill.METHODS.datatrans
        self.bill.save()
        self.assertEqual(self.bill.qr_invoice, "")
