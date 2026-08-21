import uuid
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.utils import timezone

from activities.models import CoursesInstructors
from activities.tests.factories import ActivityFactory
from activities.tests.factories import CourseFactory
from registrations.models import RegistrationsProfile
from registrations.tests.factories import ChildFactory
from sportfac.utils import TenantTestCase as TestCase

from ..models import FamilyUser
from .factories import FamilyUserFactory


def _scrub_stale_email(pk):
    """Rename a test-only FamilyUser out of any email collision it was left in.

    Not .delete(): FamilyUser.delete() hits a pre-existing schema issue
    (profiles_familyuser_groups.familyuser_id is still `integer`, not `uuid`, in at least
    this test schema) that crashes Django's deletion collector - unrelated to what's being
    tested here, so sidestepped rather than fixed in passing.
    """
    FamilyUser.objects.filter(pk=pk).update(email=f"stale-{pk}@cleanup.invalid")


class LowercaseFamilyEmailsTests(TestCase):
    # FastTenantTestCase reuses one schema across the whole test run without rolling back
    # between tests (see django_tenants.test.cases.FastTenantTestCase's own docstring) - a
    # fixed literal email shared across test methods here previously collided with rows
    # other test methods (in this file and elsewhere) left behind. A UUID-derived local
    # part keeps every test's data unique for the lifetime of the whole suite run.
    def _unique_email(self):
        return f"Some.User.{uuid.uuid4().hex}@Example.com"

    def _call(self, *args):
        out = StringIO()
        call_command("lowercase_family_emails", *args, stdout=out)
        return out.getvalue()

    def test_lowercases_mixed_case_email(self):
        mixed_case = self._unique_email()
        user = FamilyUserFactory()
        FamilyUser.objects.filter(pk=user.pk).update(email=mixed_case)

        self._call()

        user.refresh_from_db()
        self.assertEqual(user.email, mixed_case.lower())

    def test_dry_run_does_not_save(self):
        mixed_case = self._unique_email()
        user = FamilyUserFactory()
        FamilyUser.objects.filter(pk=user.pk).update(email=mixed_case)

        output = self._call("--dry-run")

        user.refresh_from_db()
        self.assertEqual(user.email, mixed_case)
        self.assertIn("Would fix", output)

    def test_skips_and_reports_case_variant_collision(self):
        # Regression test: two accounts differing only by email case - the same real
        # situation found in production (see profiles.0026's docstring) - must be left
        # untouched, not merged automatically, since picking a winner is a human call.
        mixed_case = self._unique_email()
        user_a = FamilyUserFactory()
        FamilyUser.objects.filter(pk=user_a.pk).update(email=mixed_case)
        user_b = FamilyUserFactory()
        FamilyUser.objects.filter(pk=user_b.pk).update(email=mixed_case.upper())
        # Left unresolved on purpose (see docstring above) - clean it up so it doesn't leak
        # into MergeFamilyAccountsTests below, which enumerates every colliding group in
        # this same shared schema (see FastTenantTestCase's docstring, noted above).
        self.addCleanup(_scrub_stale_email, user_a.pk)
        self.addCleanup(_scrub_stale_email, user_b.pk)

        output = self._call()

        user_a.refresh_from_db()
        user_b.refresh_from_db()
        self.assertEqual(user_a.email, mixed_case)
        self.assertEqual(user_b.email, mixed_case.upper())
        self.assertIn(str(user_a.pk), output)
        self.assertIn(str(user_b.pk), output)

    def test_rerun_is_idempotent(self):
        mixed_case = self._unique_email()
        user = FamilyUserFactory()
        FamilyUser.objects.filter(pk=user.pk).update(email=mixed_case)

        self._call()
        self._call()  # must not raise (e.g. re-lowercasing an already-lowercase email)

        user.refresh_from_db()
        self.assertEqual(user.email, mixed_case.lower())


class MergeFamilyAccountsTests(TestCase):
    def _unique_email(self):
        return f"Some.User.{uuid.uuid4().hex}@Example.com"

    def _make_duplicate_pair(self, winner_last_login, loser_last_login):
        """A case-variant duplicate pair, winner logged in more recently than loser.

        loser.date_joined is forced a year into the past (rather than left at its
        near-simultaneous factory default) so the "most recent login, falling back to
        date_joined" suggestion is unambiguous regardless of how fast the test runs -
        with both accounts created microseconds apart otherwise, timing could flip which
        one the command suggests first.
        """
        mixed_case = self._unique_email()
        winner = FamilyUserFactory(last_login=winner_last_login)
        FamilyUser.objects.filter(pk=winner.pk).update(email=mixed_case.lower())
        loser = FamilyUserFactory(last_login=loser_last_login)
        FamilyUser.objects.filter(pk=loser.pk).update(
            email=mixed_case, date_joined=timezone.now() - timedelta(days=365)
        )
        # A merge that's declined/skipped/dry-run leaves this pair colliding - clean up
        # unconditionally (harmless no-op for a test that did merge - the loser's email is
        # already mangled by soft_delete() by then) so it can't leak into a later test's own
        # merge_family_accounts run in this same shared, non-rolled-back schema.
        self.addCleanup(_scrub_stale_email, winner.pk)
        self.addCleanup(_scrub_stale_email, loser.pk)
        return winner, loser

    def _call(self, *args, input_values=None):
        out = StringIO()
        with patch("builtins.input", side_effect=input_values or []):
            call_command("merge_family_accounts", *args, stdout=out)
        return out.getvalue()

    def test_dry_run_reassigns_nothing(self):
        winner, loser = self._make_duplicate_pair(timezone.now(), None)
        child = ChildFactory(family=loser)

        self._call("--dry-run")

        child.refresh_from_db()
        loser.refresh_from_db()
        self.assertEqual(child.family_id, loser.pk)
        self.assertTrue(loser.is_active)

    def test_confirmed_merge_reassigns_child_and_soft_deletes_loser(self):
        winner, loser = self._make_duplicate_pair(timezone.now(), None)
        child = ChildFactory(family=loser)

        # default winner suggestion accepted (blank answer), then confirm the merge
        self._call(input_values=["", "y"])

        child.refresh_from_db()
        loser.refresh_from_db()
        self.assertEqual(child.family_id, winner.pk)
        self.assertFalse(loser.is_active)
        self.assertTrue(loser.email.startswith("deleted_"))

    def test_declining_confirmation_leaves_data_untouched(self):
        winner, loser = self._make_duplicate_pair(timezone.now(), None)
        child = ChildFactory(family=loser)

        self._call(input_values=["", "n"])

        child.refresh_from_db()
        loser.refresh_from_db()
        self.assertEqual(child.family_id, loser.pk)
        self.assertTrue(loser.is_active)

    def test_skipping_a_group_leaves_it_untouched(self):
        winner, loser = self._make_duplicate_pair(timezone.now(), None)
        child = ChildFactory(family=loser)

        self._call(input_values=["s"])

        child.refresh_from_db()
        loser.refresh_from_db()
        self.assertEqual(child.family_id, loser.pk)
        self.assertTrue(loser.is_active)

    def test_operator_can_override_the_suggested_winner(self):
        # accounts() lists the more-recent login first (suggested #1) - picking "2" instead
        # must keep the *other* account and merge the suggested one into it.
        suggested, override = self._make_duplicate_pair(timezone.now(), None)
        child = ChildFactory(family=override)

        self._call(input_values=["2", "y"])

        child.refresh_from_db()
        suggested.refresh_from_db()
        self.assertEqual(child.family_id, override.pk)
        self.assertFalse(suggested.is_active)

    def test_courses_instructors_moved_when_no_conflict(self):
        winner, loser = self._make_duplicate_pair(timezone.now(), None)
        course = CourseFactory()
        ci = CoursesInstructors.objects.create(course=course, instructor=loser)

        self._call(input_values=["", "y"])

        ci.refresh_from_db()
        self.assertEqual(ci.instructor_id, winner.pk)

    def test_courses_instructors_dropped_on_conflict(self):
        # Both winner and loser are already instructors on the same course - the unique
        # (course, instructor) constraint means the loser's row can only be dropped, not
        # moved, or the merge would crash instead of completing.
        winner, loser = self._make_duplicate_pair(timezone.now(), None)
        course = CourseFactory()
        CoursesInstructors.objects.create(course=course, instructor=winner)
        loser_ci = CoursesInstructors.objects.create(course=course, instructor=loser)

        self._call(input_values=["", "y"])

        self.assertFalse(CoursesInstructors.objects.filter(pk=loser_ci.pk).exists())
        self.assertTrue(CoursesInstructors.objects.filter(course=course, instructor=winner).exists())

    def test_managed_activities_reassigned(self):
        winner, loser = self._make_duplicate_pair(timezone.now(), None)
        activity = ActivityFactory()
        activity.managers.add(loser)

        self._call(input_values=["", "y"])

        activity.refresh_from_db()
        self.assertIn(winner, activity.managers.all())
        self.assertNotIn(loser, activity.managers.all())

    def test_registration_profile_dropped_for_loser_and_refreshed_for_winner(self):
        winner, loser = self._make_duplicate_pair(timezone.now(), None)
        self.assertTrue(RegistrationsProfile.objects.filter(user=loser).exists())

        self._call(input_values=["", "y"])

        self.assertFalse(RegistrationsProfile.objects.filter(user=loser).exists())
        self.assertTrue(RegistrationsProfile.objects.filter(user=winner).exists())

    def test_elevated_role_flag_on_loser_is_reported_but_not_copied(self):
        winner, loser = self._make_duplicate_pair(timezone.now(), None)
        FamilyUser.objects.filter(pk=loser.pk).update(is_manager=True)

        output = self._call(input_values=["", "y"])

        self.assertIn("is_manager", output)
        winner.refresh_from_db()
        self.assertFalse(winner.is_manager)
