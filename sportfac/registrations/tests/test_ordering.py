from types import SimpleNamespace

from django.test import SimpleTestCase
from django.test import override_settings

from registrations.ordering import order_participants_by_bib


class ParticipantOrderingTests(SimpleTestCase):
    def registration(self, pk, bib, last_name="Martin", first_name="Alice"):
        return SimpleNamespace(
            pk=pk, child=SimpleNamespace(bib_number=bib, last_name=last_name, first_name=first_name)
        )

    @override_settings(KEPCHUP_BIB_NUMBERS=True)
    def test_numeric_bibs_then_missing_or_invalid_bibs_with_name_tiebreakers(self):
        registrations = [
            self.registration(1, "100"),
            self.registration(2, "10", "Zulu"),
            self.registration(3, "2"),
            self.registration(4, ""),
            self.registration(5, None, "Albert"),
            self.registration(6, "invalid", "Zulu"),
            self.registration(7, "10", "Albert"),
        ]
        self.assertEqual([r.pk for r in order_participants_by_bib(registrations)], [3, 7, 2, 1, 5, 4, 6])
        self.assertEqual([r.pk for r in registrations], list(range(1, 8)))
        self.assertEqual(order_participants_by_bib([]), [])

    @override_settings(KEPCHUP_BIB_NUMBERS=False)
    def test_disabled_bibs_sort_by_surname_then_first_name(self):
        registrations = [
            self.registration(1, "2", "Zulu"),
            self.registration(2, "100", "Albert", "Zoé"),
            self.registration(3, "200", "Albert", "Alice"),
        ]
        self.assertEqual([r.pk for r in order_participants_by_bib(iter(registrations))], [3, 2, 1])
