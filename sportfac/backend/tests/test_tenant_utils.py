"""Tests for backend.tenant_utils – denormalized field reset on period copy."""
from datetime import datetime
from datetime import timezone

from activities.tests.factories import CourseFactory
from sportfac.utils import TenantTestCase


class ResetCourseCountersTests(TenantTestCase):
    """
    The reset applied inside copy_activities (and the reset_course_counters command)
    must zero-out every denormalized field so that a freshly-copied period starts clean.
    """

    def _reset(self):
        from activities.models import Course

        Course.objects.all().update(
            uptodate=False,
            nb_participants=0,
            has_waiting_list=False,
            places_available_reminder_sent_on=None,
            announced_js=False,
            allow_new_participants=True,
        )

    def test_nb_participants_reset(self):
        course = CourseFactory(nb_participants=12)
        self._reset()
        course.refresh_from_db()
        self.assertEqual(course.nb_participants, 0)

    def test_uptodate_reset(self):
        course = CourseFactory(uptodate=True)
        self._reset()
        course.refresh_from_db()
        self.assertFalse(course.uptodate)

    def test_has_waiting_list_reset(self):
        """has_waiting_list=True carried over from old period must become False."""
        course = CourseFactory(has_waiting_list=True)
        self._reset()
        course.refresh_from_db()
        self.assertFalse(course.has_waiting_list)

    def test_places_available_reminder_sent_on_reset(self):
        """Reminder timestamp from old period must be cleared so reminders can fire again."""
        course = CourseFactory(places_available_reminder_sent_on=datetime(2025, 6, 1, tzinfo=timezone.utc))
        self._reset()
        course.refresh_from_db()
        self.assertIsNone(course.places_available_reminder_sent_on)

    def test_announced_js_reset(self):
        """J+S announcement is per-period; must be False in the new period."""
        course = CourseFactory(announced_js=True)
        self._reset()
        course.refresh_from_db()
        self.assertFalse(course.announced_js)

    def test_allow_new_participants_reset(self):
        """A manually-blocked course in the old period must re-open for the new period."""
        course = CourseFactory(allow_new_participants=False)
        self._reset()
        course.refresh_from_db()
        self.assertTrue(course.allow_new_participants)

    def test_all_fields_reset_at_once(self):
        """All six fields are reset in a single update – no field left behind."""
        course = CourseFactory(
            nb_participants=5,
            uptodate=True,
            has_waiting_list=True,
            places_available_reminder_sent_on=datetime(2025, 1, 1, tzinfo=timezone.utc),
            announced_js=True,
            allow_new_participants=False,
        )
        self._reset()
        course.refresh_from_db()
        self.assertEqual(course.nb_participants, 0)
        self.assertFalse(course.uptodate)
        self.assertFalse(course.has_waiting_list)
        self.assertIsNone(course.places_available_reminder_sent_on)
        self.assertFalse(course.announced_js)
        self.assertTrue(course.allow_new_participants)

    def test_reset_affects_all_courses(self):
        """Every course in the tenant is reset, not just the first one."""
        courses = CourseFactory.create_batch(3, has_waiting_list=True, nb_participants=10)
        self._reset()
        from activities.models import Course

        self.assertEqual(Course.objects.filter(has_waiting_list=True).count(), 0)
        self.assertEqual(Course.objects.filter(nb_participants__gt=0).count(), 0)
        self.assertEqual(len(courses), 3)  # sanity: 3 courses exist
