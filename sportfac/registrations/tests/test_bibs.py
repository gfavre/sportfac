from django.core.exceptions import ValidationError
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext

from activities.tests.factories import CourseFactory
from registrations.bibs import generate_bibs
from registrations.forms import TransportForm
from registrations.models import Child
from registrations.models import Registration
from registrations.models import Transport
from registrations.tests.factories import ChildFactory
from registrations.tests.factories import RegistrationFactory
from sportfac.utils import TenantTestCase


@override_settings(KEPCHUP_EXPLICIT_SESSION_DATES=False)
class GenerateBibsTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.car = Transport.objects.create(name="Car bleu", bib_prefix=3)

    def register(self, **kwargs):
        return RegistrationFactory(transport=self.car, **kwargs).child

    def test_one_bib_per_child_sorted_by_name_then_first_name(self):
        last = self.register(child__last_name="Zulu")
        second = self.register(child__last_name="Émile", child__first_name="Zoé")
        first = self.register(child__last_name="emile", child__first_name="Alfred")
        RegistrationFactory(child=first, transport=self.car)
        other = ChildFactory()
        canceled = RegistrationFactory(transport=None, status=Registration.STATUS.canceled).child
        self.assertEqual(generate_bibs(), 3)
        for child, expected in ((first, "301"), (second, "302"), (last, "303"), (other, ""), (canceled, "")):
            child.refresh_from_db()
            self.assertEqual(child.bib_number, expected)

    def test_existing_bibs_are_preserved_unless_replacement_is_requested(self):
        child = self.register(child__bib_number="42")
        self.assertEqual(generate_bibs(), 0)
        child.refresh_from_db()
        self.assertEqual(child.bib_number, "42")
        generate_bibs(overwrite=True)
        child.refresh_from_db()
        self.assertEqual(child.bib_number, "301")

    def test_later_registrations_do_not_renumber_existing_children(self):
        first = self.register(child__last_name="Zulu")
        self.assertEqual(generate_bibs(), 1)
        first.refresh_from_db()
        original_modified = first.modified
        newcomer = self.register(child__last_name="Alpha")
        self.assertEqual(generate_bibs(), 1)
        first.refresh_from_db()
        newcomer.refresh_from_db()
        self.assertEqual(first.bib_number, "301")
        self.assertEqual(first.modified, original_modified)
        self.assertEqual(newcomer.bib_number, "302")
        self.assertEqual(generate_bibs(), 0)

    def test_incremental_assignment_reserves_distributed_and_canceled_bibs(self):
        ChildFactory(bib_number="301")
        self.register(child__bib_number="302", status=Registration.STATUS.canceled)
        existing = self.register(child__bib_number="304")
        first = self.register(child__last_name="Alpha")
        second = self.register(child__last_name="Zulu")
        self.assertEqual(generate_bibs(), 2)
        for child, expected in ((first, "303"), (existing, "304"), (second, "305")):
            child.refresh_from_db()
            self.assertEqual(child.bib_number, expected)

    def test_duplicate_existing_bibs_block_incremental_assignment(self):
        first = self.register(child__bib_number="301")
        second = self.register(child__bib_number="301")
        newcomer = self.register()
        with self.assertRaises(ValidationError):
            generate_bibs()
        for child, expected in ((first, "301"), (second, "301"), (newcomer, "")):
            child.refresh_from_db()
            self.assertEqual(child.bib_number, expected)

    def test_existing_bib_colliding_with_child_outside_population_is_rejected(self):
        ChildFactory(bib_number="301")
        self.register(child__bib_number="301")
        with self.assertRaises(ValidationError):
            generate_bibs()

    def test_exhausted_number_range_leaves_every_car_unchanged(self):
        first = self.register()
        other_car = Transport.objects.create(name="Autre", bib_prefix=4)
        second = RegistrationFactory(transport=other_car).child
        reserved = ChildFactory.create_batch(99, family=first.family)
        for rank, child in enumerate(reserved, 1):
            child.bib_number = f"4{rank:02d}"
        Child.objects.bulk_update(reserved, ["bib_number"])
        with self.assertRaises(ValidationError):
            generate_bibs()
        for child in (first, second):
            child.refresh_from_db()
            self.assertEqual(child.bib_number, "")

    def test_explicit_replacement_reorders_the_whole_car(self):
        existing = self.register(child__last_name="Zulu", child__bib_number="301")
        newcomer = self.register(child__last_name="Alpha")
        self.assertEqual(generate_bibs(overwrite=True), 2)
        existing.refresh_from_db()
        newcomer.refresh_from_db()
        self.assertEqual(existing.bib_number, "302")
        self.assertEqual(newcomer.bib_number, "301")

    def test_missing_or_conflicting_transport_is_rejected(self):
        child = self.register()
        other = Transport.objects.create(name="Autre", bib_prefix=4)
        registration = RegistrationFactory(child=child, transport=other)
        for transport in (other, None):
            Registration.objects.filter(pk=registration.pk).update(transport=transport)
            with self.assertRaises(ValidationError):
                generate_bibs()
            child.refresh_from_db()
            self.assertEqual(child.bib_number, "")

    def test_missing_prefix_and_external_collision_leave_bibs_unchanged(self):
        child = self.register()
        self.car.bib_prefix = None
        self.car.save()
        with self.assertRaises(ValidationError):
            generate_bibs()
        self.car.bib_prefix = 3
        self.car.save()
        ChildFactory(bib_number="301")
        with self.assertRaises(ValidationError):
            generate_bibs(overwrite=True)
        child.refresh_from_db()
        self.assertEqual(child.bib_number, "")

    def test_duplicate_prefix_is_rejected_by_form(self):
        form = TransportForm(data={"name": "Autre", "bib_prefix": 3})
        self.assertFalse(form.is_valid())
        self.assertIn("bib_prefix", form.errors)

    def test_capacity_counts_children(self):
        children = ChildFactory.create_batch(100)
        course = RegistrationFactory(transport=self.car, child=children[0]).course
        Registration.objects.bulk_create(
            [Registration(child=child, course=course, transport=self.car) for child in children[1:]]
        )
        with self.assertRaises(ValidationError):
            generate_bibs()
        children[-1].registrations.all().delete()
        self.assertEqual(generate_bibs(), 99)

    def test_generating_400_bibs_uses_bounded_queries_and_one_bulk_update(self):
        first = ChildFactory()
        children = [first] + ChildFactory.create_batch(399, family=first.family)
        cars = [self.car] + [
            Transport.objects.create(name=f"Car {prefix}", bib_prefix=prefix) for prefix in range(4, 8)
        ]
        course = CourseFactory()
        Registration.objects.bulk_create(
            [
                Registration(child=child, course=course, transport=cars[index // 80])
                for index, child in enumerate(children)
            ]
        )

        with CaptureQueriesContext(connection) as queries:
            self.assertEqual(generate_bibs(), 400)

        # Count data queries, excluding transaction and tenant search_path statements.
        selects = [query for query in queries if query["sql"].lstrip().upper().startswith("SELECT ")]
        updates = [query for query in queries if query["sql"].lstrip().upper().startswith("UPDATE ")]
        self.assertEqual(len(selects), 4)
        self.assertEqual(len(updates), 1)
        self.assertEqual(
            set(Child.objects.filter(pk__in=[child.pk for child in children]).values_list("bib_number", flat=True)),
            {f"{car.bib_prefix}{rank:02d}" for car in cars for rank in range(1, 81)},
        )

    def test_preview_does_not_write_and_matches_incremental_generation(self):
        from registrations.bibs import prepare_bibs

        existing = self.register(child__bib_number="304")
        newcomer = self.register()
        plan = prepare_bibs()
        self.assertTrue(plan["can_generate"])
        self.assertEqual((plan["existing_count"], plan["new_count"]), (1, 1))
        self.assertEqual([(child.pk, child.bib_number) for child in plan["changed"]], [(newcomer.pk, "301")])
        newcomer.refresh_from_db()
        self.assertEqual(newcomer.bib_number, "")
        self.assertEqual(generate_bibs(), 1)
        newcomer.refresh_from_db()
        existing.refresh_from_db()
        self.assertEqual((newcomer.bib_number, existing.bib_number), ("301", "304"))

    def test_preview_reports_multiple_car_errors_and_duplicates_before_generation(self):
        from registrations.bibs import prepare_bibs

        first = self.register(child__bib_number="301")
        self.register(child__bib_number="301")
        RegistrationFactory(transport=None)
        empty_range = Transport.objects.create(name="Plage épuisée", bib_prefix=8)
        RegistrationFactory(transport=empty_range)
        for rank in range(1, 100):
            ChildFactory(family=first.family, bib_number=f"8{rank:02d}")
        plan = prepare_bibs()
        self.assertFalse(plan["can_generate"])
        messages = " ".join(error["message"] for error in plan["errors"])
        self.assertIn("plusieurs enfants", messages)
        self.assertIn("un seul car", messages)
        self.assertIn("plus de numéro", messages)

    def test_replacement_preview_resolves_active_duplicates_without_writing(self):
        from registrations.bibs import prepare_bibs

        first = self.register(child__bib_number="301")
        self.register(child__bib_number="301")
        plan = prepare_bibs(overwrite=True)
        self.assertTrue(plan["can_generate"])
        self.assertEqual(len(plan["changed"]), 2)
        self.assertEqual(Child.objects.filter(bib_number="301").count(), 2)
        RegistrationFactory(transport=None)
        with self.assertRaises(ValidationError):
            generate_bibs(overwrite=True)
        first.refresh_from_db()
        self.assertEqual(first.bib_number, "301")
