from datetime import time
from datetime import timedelta
from unittest import mock

from django.core.files.base import ContentFile
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from django.utils.timezone import now
from dynamic_preferences.registries import global_preferences_registry
from faker import Faker

from absences.models import Absence
from absences.tests.factories import SessionFactory
from activities.tests.factories import AllocationAccountFactory
from activities.tests.factories import CourseFactory
from profiles.tests.factories import CityFactory
from profiles.tests.factories import FamilyUserFactory
from sportfac.utils import TenantTestCase

from ..models import Bill
from ..models import Registration
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

    @override_settings(KEPCHUP_EXPLICIT_SESSION_DATES=False)
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

    @override_settings(KEPCHUP_USE_ABSENCES=True)
    @mock.patch("registrations.tasks.create_future_absences_for_registration.delay")
    def test_save_defers_absence_creation_to_a_task(self, mock_delay):
        # save() schedules the task via transaction.on_commit(), which TestCase's own
        # wrapping transaction never actually fires on its own - capture it explicitly.
        with self.captureOnCommitCallbacks(execute=True):
            registration = RegistrationFactory()
        mock_delay.assert_called_once_with(registration.pk)
        # nothing in the immediate request/response path needs Absence rows to exist yet
        self.assertEqual(Absence.objects.count(), 0)


class CreateFutureAbsencesTestCase(TenantTestCase):
    def setUp(self):
        self.registration = RegistrationFactory()
        self.past_session = SessionFactory(course=self.registration.course, date=now().date() - timedelta(days=7))
        self.future_session1 = SessionFactory(course=self.registration.course, date=now().date() + timedelta(days=7))
        self.future_session2 = SessionFactory(course=self.registration.course, date=now().date() + timedelta(days=14))

    def test_creates_absences_for_future_sessions_only(self):
        self.registration.create_future_absences()
        sessions_with_absence = set(
            Absence.objects.filter(child=self.registration.child).values_list("session_id", flat=True)
        )
        self.assertEqual(sessions_with_absence, {self.future_session1.id, self.future_session2.id})

    def test_created_absences_default_to_present(self):
        self.registration.create_future_absences()
        absence = Absence.objects.get(child=self.registration.child, session=self.future_session1)
        self.assertEqual(absence.status, Absence.STATUS.present)
        self.assertIsNotNone(absence.status_changed)

    def test_is_idempotent_and_does_not_touch_existing_absences(self):
        self.registration.create_future_absences()
        absence = Absence.objects.get(child=self.registration.child, session=self.future_session1)
        absence.status = Absence.STATUS.absent
        absence.save()

        self.registration.create_future_absences()

        self.assertEqual(Absence.objects.filter(child=self.registration.child).count(), 2)
        absence.refresh_from_db()
        self.assertEqual(absence.status, Absence.STATUS.absent)

    def test_is_a_noop_for_canceled_registrations(self):
        # Regression test: create_future_absences_for_registration's task re-reads the
        # registration from the DB and runs after cancel()'s delete_future_absences() has
        # already run - without this guard it would silently resurrect the absences.
        self.registration.status = self.registration.STATUS.canceled

        self.registration.create_future_absences()

        self.assertEqual(Absence.objects.filter(child=self.registration.child).count(), 0)


class DeleteFutureAbsencesTestCase(TenantTestCase):
    def setUp(self):
        self.registration = RegistrationFactory()
        self.past_session = SessionFactory(course=self.registration.course, date=now().date() - timedelta(days=7))
        self.future_session1 = SessionFactory(course=self.registration.course, date=now().date() + timedelta(days=7))
        self.future_session2 = SessionFactory(course=self.registration.course, date=now().date() + timedelta(days=14))
        self.registration.create_future_absences()

    def test_deletes_future_absences_only(self):
        past_absence = Absence.objects.create(child=self.registration.child, session=self.past_session)

        self.registration.delete_future_absences()

        self.assertFalse(
            Absence.objects.filter(
                child=self.registration.child, session__in=[self.future_session1, self.future_session2]
            ).exists()
        )
        self.assertTrue(Absence.objects.filter(pk=past_absence.pk).exists())

    def test_does_not_touch_other_childrens_absences(self):
        other_registration = RegistrationFactory(course=self.registration.course)
        other_registration.create_future_absences()

        self.registration.delete_future_absences()

        self.assertTrue(Absence.objects.filter(child=other_registration.child, session=self.future_session1).exists())

    def test_query_count_does_not_scale_with_number_of_sessions(self):
        # Regression test for the old per-session loop: the query count must stay constant
        # no matter how many future sessions exist, instead of growing with each one.
        for i in range(10):
            SessionFactory(course=self.registration.course, date=now().date() + timedelta(days=21 + i))
        self.registration.create_future_absences()

        with self.assertNumQueries(4):
            self.registration.delete_future_absences()


class CancelTestCase(TenantTestCase):
    @override_settings(KEPCHUP_USE_ABSENCES=True)
    def test_cancel_deletes_future_absences(self):
        registration = RegistrationFactory()
        future_session = SessionFactory(course=registration.course, date=now().date() + timedelta(days=7))
        registration.create_future_absences()
        self.assertTrue(Absence.objects.filter(child=registration.child, session=future_session).exists())

        registration.cancel()

        self.assertFalse(Absence.objects.filter(child=registration.child, session=future_session).exists())

    @override_settings(KEPCHUP_USE_ABSENCES=False)
    def test_cancel_does_not_touch_absences_when_feature_disabled(self):
        registration = RegistrationFactory()
        future_session = SessionFactory(course=registration.course, date=now().date() + timedelta(days=7))
        Absence.objects.create(child=registration.child, session=future_session)

        registration.cancel()

        self.assertTrue(Absence.objects.filter(child=registration.child, session=future_session).exists())

    @override_settings(KEPCHUP_USE_ABSENCES=True)
    def test_cancel_then_save_does_not_resurrect_absences_via_the_async_task(self):
        # End-to-end regression test: cancel() deletes future absences synchronously, but the
        # save() that persists the cancelation also schedules create_future_absences_for_registration
        # (async, via on_commit). Without the status guard in create_future_absences(), that
        # task would recreate the absences it should have skipped.
        from ..tasks import create_future_absences_for_registration

        registration = RegistrationFactory()
        future_session = SessionFactory(course=registration.course, date=now().date() + timedelta(days=7))
        registration.create_future_absences()
        self.assertTrue(Absence.objects.filter(child=registration.child, session=future_session).exists())

        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            registration.cancel()
            registration.save()
        self.assertFalse(Absence.objects.filter(child=registration.child, session=future_session).exists())

        # Simulate the Celery worker picking up the scheduled task after commit.
        create_future_absences_for_registration(registration.pk)

        self.assertFalse(Absence.objects.filter(child=registration.child, session=future_session).exists())
        self.assertTrue(callbacks)


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

    def test_pdf_cleared_when_qr_invoice_changes(self):
        self.assertTrue(self.bill.pdf)
        preferences = global_preferences_registry.manager()
        preferences["payment__IBAN"] = "CH9300762011623852957"
        preferences["payment__ADDRESS"] = "Commune de Coppet\nGrand-Rue 34\n1296 Coppet"
        self.bill.payment_method = self.bill.METHODS.iban
        self.bill.save()
        self.assertFalse(self.bill.pdf)

    def test_pdf_kept_when_qr_invoice_unchanged(self):
        # Preference state can leak between tests (dynamic_preferences caches values
        # outside the DB transaction rollback), so force a known, empty qr_invoice
        # baseline first rather than relying on whatever setUp's bill happened to get.
        preferences = global_preferences_registry.manager()
        preferences["payment__IBAN"] = ""
        self.bill.payment_method = self.bill.METHODS.iban
        self.bill.save()
        self.assertEqual(self.bill.qr_invoice, "")

        self.bill.pdf.save("test.pdf", ContentFile(b"%PDF-1.4 fake"), save=True)
        self.assertTrue(self.bill.pdf)


class BillSetPaidTestCase(TenantTestCase):
    def setUp(self):
        self.bill = BillFactory()
        self.registrations = [
            RegistrationFactory(bill=self.bill, price=100, status=Registration.STATUS.confirmed) for _ in range(3)
        ]

    def test_marks_all_registrations_and_rentals_as_paid(self):
        self.bill.set_paid()

        for registration in self.registrations:
            registration.refresh_from_db()
            self.assertTrue(registration.paid)
        self.bill.refresh_from_db()
        self.assertEqual(self.bill.status, Bill.STATUS.paid)
        self.assertIsNotNone(self.bill.payment_date)

    def test_query_count_does_not_scale_with_number_of_registrations(self):
        # Regression test: set_paid() used to loop through Registration.save(), each of which
        # cascaded into a full Bill.save() - O(N) queries for an N-registration bill. A bill
        # with 3 registrations (setUp) and one with 12 must now cost the same number of queries.
        big_bill = BillFactory()
        for _ in range(12):
            RegistrationFactory(bill=big_bill, price=100, status=Registration.STATUS.confirmed)

        with CaptureQueriesContext(connection) as small_queries:
            self.bill.set_paid()
        with CaptureQueriesContext(connection) as big_queries:
            big_bill.set_paid()

        self.assertEqual(len(small_queries.captured_queries), len(big_queries.captured_queries))

    def test_does_not_change_course_participant_count(self):
        course = self.registrations[0].course
        course.refresh_from_db()
        nb_participants_before = course.nb_participants

        self.bill.set_paid()

        course.refresh_from_db()
        self.assertEqual(course.nb_participants, nb_participants_before)


class BillCloseTestCase(TenantTestCase):
    def setUp(self):
        self.bill = BillFactory()

    def test_marks_valid_registrations_as_paid(self):
        valid_registration = RegistrationFactory(bill=self.bill, price=100, status=Registration.STATUS.valid)
        waiting_registration = RegistrationFactory(bill=self.bill, price=100, status=Registration.STATUS.waiting)

        self.bill.close()

        valid_registration.refresh_from_db()
        waiting_registration.refresh_from_db()
        self.assertTrue(valid_registration.paid)
        self.assertFalse(waiting_registration.paid)

        self.bill.save()
        self.assertTrue(self.bill.pdf)
