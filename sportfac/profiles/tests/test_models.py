from activities.tests.factories import CourseFactory
from registrations.models import Child
from registrations.models import RegistrationsProfile
from registrations.tests.factories import ChildFactory
from sportfac.utils import TenantTestCase as TestCase

from ..models import FamilyUser
from .factories import FamilyUserFactory


def _scrub_stale_email(pk):
    """Rename a test-only FamilyUser out of any email collision it was left in.

    Not .delete(): see callers for why a real delete crashes here.
    """
    FamilyUser.objects.filter(pk=pk).update(email=f"stale-{pk}@cleanup.invalid")


class FamilyUserTests(TestCase):
    def setUp(self):
        super().setUp()
        self.family_user = FamilyUserFactory()

    def test_save_creates_profile(self):
        if hasattr(self.family_user, "profile"):
            self.family_user.profile.delete()
        self.family_user.save(create_profile=True)
        self.assertEqual(RegistrationsProfile.objects.count(), 1)
        self.family_user.refresh_from_db()
        self.assertIsNotNone(self.family_user.profile)

    def test_soft_delete_unset_instructor(self):
        course = CourseFactory(instructors=[self.family_user])
        self.family_user.soft_delete()
        course.refresh_from_db()
        self.assertNotIn(self.family_user, course.instructors.all())

    def test_soft_delete_sets_inactive(self):
        self.family_user.soft_delete()
        self.assertFalse(self.family_user.is_active)

    def test_soft_delete_removes_children(self):
        ChildFactory(family=self.family_user)
        self.family_user.soft_delete()
        self.assertEqual(Child.objects.count(), 0)

    def test_save_lowercases_email(self):
        # Regression test: BaseUserManager.normalize_email (used by create_user) only
        # lowercases the domain part of the email, per RFC - the local part kept whatever
        # case the user typed at signup. That silently broke login for anyone typing their
        # email back in a different case later (e.g. at password reset time, which itself
        # matches case-insensitively - see Django's PasswordResetForm.get_users), since
        # ModelBackend's lookup was an exact match. Lowercasing on every save, regardless
        # of entry point, is the fix.
        self.family_user.email = "Some.User@EXAMPLE.com"
        self.family_user.save()
        self.family_user.refresh_from_db()
        self.assertEqual(self.family_user.email, "some.user@example.com")

    def test_get_by_natural_key_is_case_insensitive(self):
        # Companion to test_save_lowercases_email above: covers accounts that were saved
        # with mixed-case emails before this fix existed, and haven't been re-saved since -
        # login must still find them regardless of the case the user logs in with.
        FamilyUser.objects.filter(pk=self.family_user.pk).update(email="Some.User@example.com")
        found = FamilyUser.objects.get_by_natural_key("some.user@example.com")
        self.assertEqual(found.pk, self.family_user.pk)

    def test_get_by_natural_key_exact_match_wins_over_case_variant_duplicate(self):
        # Regression test: real, pre-existing accounts differing only by email case exist
        # in production (two active accounts for the same person - almost certainly earlier
        # victims of this very bug re-registering rather than resetting their password).
        # A bare __iexact lookup would match both and raise MultipleObjectsReturned,
        # crashing a login that used to work fine (via the old exact-match lookup) for
        # whichever casing was actually typed. Trying an exact match first must keep that
        # working.
        FamilyUser.objects.filter(pk=self.family_user.pk).update(email="Some.User@example.com")
        other = FamilyUserFactory(email="some.user@example.com")
        # FastTenantTestCase shares one schema across the whole run without rolling back
        # between tests (see its own docstring) - leaving this pair of accounts colliding
        # by email would otherwise leak into e.g. test_management_commands.py's
        # merge_family_accounts tests, which enumerate every colliding group in the schema.
        # Renaming (not .delete()): FamilyUser.delete() hits a pre-existing schema issue
        # (profiles_familyuser_groups.familyuser_id is still `integer`, not `uuid`, in at
        # least this test schema) that crashes Django's deletion collector - unrelated to
        # what's being tested here, so sidestepped rather than fixed in passing.
        self.addCleanup(_scrub_stale_email, self.family_user.pk)
        self.addCleanup(_scrub_stale_email, other.pk)

        found_exact = FamilyUser.objects.get_by_natural_key("Some.User@example.com")
        self.assertEqual(found_exact.pk, self.family_user.pk)
        found_other = FamilyUser.objects.get_by_natural_key("some.user@example.com")
        self.assertEqual(found_other.pk, other.pk)

    def test_get_by_natural_key_fails_closed_on_ambiguous_case_variant_duplicate(self):
        # Companion to the test above: a login attempt whose casing matches NEITHER
        # duplicate exactly must fail cleanly (account not found), not crash the request
        # with an unhandled MultipleObjectsReturned.
        FamilyUser.objects.filter(pk=self.family_user.pk).update(email="Some.User@example.com")
        other = FamilyUserFactory()
        FamilyUser.objects.filter(pk=other.pk).update(email="SOME.USER@example.com")
        self.addCleanup(_scrub_stale_email, self.family_user.pk)
        self.addCleanup(_scrub_stale_email, other.pk)

        with self.assertRaises(FamilyUser.DoesNotExist):
            FamilyUser.objects.get_by_natural_key("some.user@example.com")
