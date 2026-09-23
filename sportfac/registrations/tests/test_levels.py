from django.template import Context
from django.template import Template
from django.test import SimpleTestCase
from django.utils.translation import override

from registrations.levels import diploma_evaluation
from registrations.levels import level_description
from registrations.levels import level_menu_label


class LevelDescriptionTests(SimpleTestCase):
    def setUp(self):
        language = override("fr")
        language.__enter__()
        self.addCleanup(language.__exit__, None, None, None)

    def test_labels_follow_active_language(self):
        with override("en"):
            self.assertEqual(level_description("A 1A"), "Alpine skiing, level 1, needs improvement")
            self.assertEqual(level_description("S 2B"), "Snowboarding, level 2, good")
            self.assertEqual(diploma_evaluation("Ski", "A 7C"), "Alpine skiing, level 7, confirmed")
        self.assertEqual(level_description("A 1A"), "Ski alpin, niveau 1, à améliorer")

    def test_all_documented_levels(self):
        for prefix, sport in (("A", "Ski alpin"), ("S", "Snowboard")):
            for number in range(1, 8):
                for suffix, label in (("A", "à améliorer"), ("B", "bien"), ("C", "confirmé")):
                    code = f"{prefix} {number}{suffix}"
                    expected = f"{sport}, niveau {number}, {label}"
                    with self.subTest(code=code):
                        self.assertEqual(level_description(code), expected)
                        self.assertEqual(diploma_evaluation("Course name", code), expected)
                        self.assertEqual(level_menu_label(code), f"{code} — {expected}")

    def test_spacing_and_special_codes(self):
        self.assertEqual(level_description(" A 1 A "), "Ski alpin, niveau 1, à améliorer")
        for code in ("NP", "CM", "ABS", "NPA", "NPB", "NPC", "A 8A", "unknown", ""):
            self.assertEqual(level_description(code), code)
            self.assertEqual(level_menu_label(code), code)
        self.assertEqual(diploma_evaluation("Ski", "NP"), "Ski — NP")
        self.assertEqual(diploma_evaluation("Ski", ""), "")

    def test_menu_keeps_stored_value(self):
        template = Template('{% load registrations %}<option value="{{ code }}">{{ code|level_menu_label }}</option>')
        self.assertEqual(
            template.render(Context({"code": "S 7C"})),
            '<option value="S 7C">S 7C — Snowboard, niveau 7, confirmé</option>',
        )
