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
