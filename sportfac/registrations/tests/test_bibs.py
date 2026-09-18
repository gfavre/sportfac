from django.core.exceptions import ValidationError
from django.test import override_settings

from registrations.bibs import generate_bibs
from registrations.forms import TransportForm
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

    def test_existing_bibs_require_explicit_replacement(self):
        child = self.register(child__bib_number="42")
        with self.assertRaises(ValidationError):
            generate_bibs()
        child.refresh_from_db()
        self.assertEqual(child.bib_number, "42")
        generate_bibs(overwrite=True)
        child.refresh_from_db()
        self.assertEqual(child.bib_number, "301")

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
