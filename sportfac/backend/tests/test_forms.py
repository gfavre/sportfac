import datetime

from django.test import override_settings

from activities.tests.factories import CourseFactory
from registrations.models import Registration
from registrations.tests.factories import ChildFactory
from sportfac.utils import TenantTestCase

from ..forms import RegistrationForm


class RegistrationFormCourseQuerysetTests(TenantTestCase):
    # Regression tests: CourseSelectMixin used to filter the course dropdown with
    # schoolyear_min__lte=.../min_birth_date__gte=... (etc.) directly - SQL NULL
    # comparisons are never true, so a course with no restriction on the relevant axis
    # silently never showed up as a selectable choice for any child, in the staff
    # backend's own "add registration" form.

    @override_settings(KEPCHUP_LIMIT_BY_SCHOOL_YEAR=True)
    def test_school_year_unrestricted_course_is_selectable(self):
        with override_settings(KEPCHUP_EXPLICIT_SESSION_DATES=False):
            unrestricted_course = CourseFactory(schoolyear_min=None, schoolyear_max=None)
        child = ChildFactory()

        form = RegistrationForm(instance=Registration(child=child))

        self.assertIn(unrestricted_course, form.fields["course"].queryset)

    @override_settings(KEPCHUP_LIMIT_BY_SCHOOL_YEAR=False, KEPCHUP_EXPLICIT_SESSION_DATES=False)
    def test_age_unrestricted_course_is_selectable(self):
        unrestricted_course = CourseFactory(age_min=None, age_max=None)
        child = ChildFactory()

        form = RegistrationForm(instance=Registration(child=child))

        self.assertIn(unrestricted_course, form.fields["course"].queryset)

    @override_settings(KEPCHUP_LIMIT_BY_SCHOOL_YEAR=False, KEPCHUP_EXPLICIT_SESSION_DATES=False)
    def test_minimum_age_only_course_is_selectable_for_an_older_child(self):
        # Regression test (LTDP support report, "SSF - Sauvetage - 8P-Rac12", 2026-08): a
        # course can restrict only one side (a minimum age, deliberately no maximum) -
        # max_birth_date is then None, and `max_birth_date__lte=...` ANDed straight into
        # the same filter made that side's SQL comparison NULL/UNKNOWN, excluding the
        # course from this dropdown for every child regardless of eligibility.
        one_sided_course = CourseFactory(age_min=8, age_max=None)
        much_older_child = ChildFactory(birth_date=datetime.date(1990, 1, 1))

        form = RegistrationForm(instance=Registration(child=much_older_child))

        self.assertIn(one_sided_course, form.fields["course"].queryset)

    @override_settings(KEPCHUP_LIMIT_BY_SCHOOL_YEAR=True, KEPCHUP_EXPLICIT_SESSION_DATES=True)
    def test_school_year_unrestricted_course_is_selectable_with_explicit_session_dates(self):
        # Coverage gap found 2026-08-18 auditing Montreux's real settings combo (school
        # year + explicit session dates together, never combined in a test before) - a
        # real Session, not a passed-in start_date (which KEPCHUP_EXPLICIT_SESSION_DATES
        # wipes on save() anyway), is what an actual open-for-registration course has.
        unrestricted_course = CourseFactory(schoolyear_min=None, schoolyear_max=None)
        unrestricted_course.add_session(datetime.date.today())
        child = ChildFactory()

        form = RegistrationForm(instance=Registration(child=child))

        self.assertIn(unrestricted_course, form.fields["course"].queryset)
