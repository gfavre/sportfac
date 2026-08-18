from django.test import override_settings

from sportfac.utils import TenantTestCase as TestCase

from ..resources import CourseResource
from .factories import CourseFactory


class CourseResourceDehydrateLimitationsTests(TestCase):
    # Regression tests: dehydrate_limitations() used to crash (KeyError) exporting a
    # course with no restriction on the active axis, since it indexed
    # settings.KEPCHUP_YEAR_NAMES[None] (school-year mode) unconditionally instead of
    # checking has_school_year_restriction/has_age_restriction first.

    @override_settings(KEPCHUP_LIMIT_BY_SCHOOL_YEAR=True)
    def test_school_year_unrestricted_course(self):
        with override_settings(KEPCHUP_EXPLICIT_SESSION_DATES=False):
            course = CourseFactory(schoolyear_min=None, schoolyear_max=None)

        self.assertEqual(CourseResource().dehydrate_limitations(course), "")

    @override_settings(KEPCHUP_LIMIT_BY_SCHOOL_YEAR=False)
    def test_age_unrestricted_course(self):
        with override_settings(KEPCHUP_EXPLICIT_SESSION_DATES=False):
            course = CourseFactory(age_min=None, age_max=None)

        self.assertEqual(CourseResource().dehydrate_limitations(course), "")
