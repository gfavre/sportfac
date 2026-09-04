"""Tests for `manage.py reset_course_counters` (backend/management/commands/
reset_course_counters.py).
"""
from unittest import TestCase
from unittest import mock

from backend.management.commands.reset_course_counters import Command


class PromptYesNoTest(TestCase):
    # Regression test: the prompt used to be `input(_("Proceed? [y/N] "))` compared
    # against the literal "y" - but gettext() renders that whole string in the active
    # language (fr-CH by default in this project), which translates the hint to
    # "[O/N]". Typing "o" (the French "oui", exactly what the on-screen hint told the
    # user to type) then never matched "y", so the command silently aborted no matter
    # the case. The [y/N] hint is now deliberately left untranslated and compared as-is.

    def setUp(self):
        self.command = Command()

    def _answer(self, value):
        with mock.patch("builtins.input", return_value=value):
            return self.command._prompt_yes_no("Proceed?")

    def test_accepts_lowercase_y(self):
        self.assertTrue(self._answer("y"))

    def test_accepts_uppercase_y(self):
        self.assertTrue(self._answer("Y"))

    def test_french_oui_is_not_mistaken_for_yes(self):
        # "o"/"O" (French "oui") must NOT be silently read as a yes - it isn't what the
        # untranslated [y/N] hint asks for. It re-prompts instead (covered below), it
        # doesn't quietly abort.
        with mock.patch("builtins.input", side_effect=["o", "y"]):
            self.assertTrue(self.command._prompt_yes_no("Proceed?"))

    def test_empty_answer_declines(self):
        self.assertFalse(self._answer(""))

    def test_n_declines(self):
        self.assertFalse(self._answer("n"))

    def test_unrecognized_answer_reprompts_instead_of_aborting(self):
        with mock.patch("builtins.input", side_effect=["o", "maybe", "y"]):
            self.assertTrue(self.command._prompt_yes_no("Proceed?"))
