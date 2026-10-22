from datetime import timedelta
from unittest import TestCase

from activities.templatetags.duration import short_duration


class ShortDurationTests(TestCase):
    def test_compact_durations(self):
        for minutes, expected in [(0, "0mn"), (45, "45mn"), (60, "1h"), (65, "1h05mn"), (90, "1h30mn")]:
            with self.subTest(minutes=minutes):
                self.assertEqual(short_duration(timedelta(minutes=minutes)), expected)

    def test_durations_over_one_day(self):
        self.assertEqual(short_duration(timedelta(days=1, minutes=45)), "24h45mn")

    def test_missing_duration(self):
        self.assertEqual(short_duration(None), "n/a")
        self.assertEqual(short_duration(""), "n/a")

    def test_invalid_duration(self):
        self.assertEqual(short_duration("invalid"), "")
