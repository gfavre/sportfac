"""Tests for `manage.py cleanup_course_data`
(backend/management/commands/cleanup_course_data.py).
"""
from io import StringIO
from unittest import mock

from django.core.management import call_command

from activities.models import Course
from activities.tests.factories import CourseFactory
from backend.management.commands.cleanup_course_data import Command
from registrations.tests.factories import RegistrationFactory
from sportfac.utils import TenantTestCase
from waiting_slots.tests.factories import WaitingSlotFactory


def _run(*, override_openness=False):
    # TenantTestCase creates exactly one YearTenant, so it's always choice "1" in the
    # interactive tenant picker.
    answers = ["1", "y"]
    out = StringIO()
    with mock.patch("builtins.input", side_effect=answers):
        args = ["--override-openness"] if override_openness else []
        call_command("cleanup_course_data", *args, stdout=out)
    return out.getvalue()


class PromptYesNoTest(TenantTestCase):
    # Same regression as reset_course_counters.PromptYesNoTest: the [y/N] hint must not be
    # translated, or the French "oui" ("o") silently reads as a no.
    def setUp(self):
        super().setUp()
        self.command = Command()

    def test_accepts_y(self):
        with mock.patch("builtins.input", return_value="y"):
            self.assertTrue(self.command._prompt_yes_no("Proceed?"))

    def test_french_oui_reprompts_instead_of_silently_declining(self):
        with mock.patch("builtins.input", side_effect=["o", "y"]):
            self.assertTrue(self.command._prompt_yes_no("Proceed?"))


class RecomputeCountersTest(TenantTestCase):
    def test_nb_participants_is_recounted_from_actual_registrations(self):
        course = CourseFactory(max_participants=5)
        RegistrationFactory(course=course)
        RegistrationFactory(course=course)
        # Simulate drift: a stale denormalized value that doesn't reflect the two real
        # registrations just created above (factories write straight to the DB, bypassing
        # whatever would normally keep this in sync).
        Course.objects.filter(pk=course.pk).update(nb_participants=99)

        _run()

        course.refresh_from_db()
        self.assertEqual(course.nb_participants, 2)

    def test_has_waiting_list_is_recounted_from_actual_waiting_slots(self):
        course = CourseFactory(max_participants=5)
        WaitingSlotFactory(course=course)
        # Simulate drift: exactly the Oron BOXE.2 incident referenced in Course.save() -
        # has_waiting_list stuck at False (or True) independently of whether a real
        # WaitingSlot exists.
        Course.objects.filter(pk=course.pk).update(has_waiting_list=False)

        _run()

        course.refresh_from_db()
        self.assertTrue(course.has_waiting_list)

    def test_no_waiting_slots_clears_a_stuck_flag(self):
        course = CourseFactory(max_participants=5)
        Course.objects.filter(pk=course.pk).update(has_waiting_list=True)

        _run()

        course.refresh_from_db()
        self.assertFalse(course.has_waiting_list)

    def test_allow_new_participants_is_left_untouched_by_default(self):
        # allow_new_participants is a manual staff choice ("more restrictive than the
        # course being full"), not derived data - without --override-openness it must
        # survive untouched even when it disagrees with the course's fullness.
        full_course = CourseFactory(max_participants=1, allow_new_participants=True)
        RegistrationFactory(course=full_course)
        closed_but_not_full = CourseFactory(max_participants=5, allow_new_participants=False)

        _run(override_openness=False)

        full_course.refresh_from_db()
        closed_but_not_full.refresh_from_db()
        self.assertTrue(full_course.allow_new_participants)
        self.assertFalse(closed_but_not_full.allow_new_participants)


class OverrideOpennessTest(TenantTestCase):
    def test_full_course_is_closed(self):
        course = CourseFactory(max_participants=1, allow_new_participants=True)
        RegistrationFactory(course=course)

        _run(override_openness=True)

        course.refresh_from_db()
        self.assertFalse(course.allow_new_participants)

    def test_non_full_course_is_opened_even_if_manually_closed(self):
        # Deliberate: --override-openness overwrites a manual staff closure that predates
        # the course being full - this is the explicit trade-off the flag is for.
        course = CourseFactory(max_participants=5, allow_new_participants=False)

        _run(override_openness=True)

        course.refresh_from_db()
        self.assertTrue(course.allow_new_participants)
