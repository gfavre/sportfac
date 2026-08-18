import random
from datetime import date
from unittest import mock

from dateutil.relativedelta import relativedelta
from django.test import override_settings
from dynamic_preferences.registries import global_preferences_registry
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIRequestFactory

from activities.tests.factories import CourseFactory
from profiles.tests.factories import SchoolYearFactory
from registrations.models import Registration
from registrations.tests.factories import ChildFactory
from sportfac.utils import TenantTestCase

from ..serializers import RegistrationSerializer


class RegistrationSerializerTest(TenantTestCase):
    def setUp(self):
        # Set up necessary data
        self.child = ChildFactory()
        self.school_year = SchoolYearFactory()
        self.age_min = random.randint(6, 12)
        self.age_max = self.age_min + 1

        # Course.save() derives start_date/end_date (and thus min/max_birth_date) from
        # sessions when KEPCHUP_EXPLICIT_SESSION_DATES is on, wiping them since this
        # course has no sessions - force it off just for creation. start_date is pinned to
        # today (CourseFactory's default is a random date over the last decade) so
        # min_birth_date/max_birth_date are computed relative to the same "today" the
        # age-boundary tests below use to build their too-young/too-old birth dates.
        with override_settings(KEPCHUP_EXPLICIT_SESSION_DATES=False):
            self.course = CourseFactory(
                schoolyear_min=self.school_year.year,
                schoolyear_max=self.school_year.year,
                age_min=self.age_min,
                age_max=self.age_max,
                start_date=date.today(),
            )
        self.factory = APIRequestFactory()

    def test_successful_registration(self):
        """Test a successful registration"""
        self.course.allow_new_participants = True
        self.course.save()
        data = {
            "child": self.child.id,
            "course": self.course.id,
        }
        serializer = RegistrationSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    @mock.patch("activities.models.Course.full", new_callable=mock.PropertyMock)
    def test_course_full(self, mock_full):
        """Test if the course is marked as full"""
        self.course.allow_new_participants = True
        self.course.save()
        mock_full.return_value = True
        data = {
            "child": self.child.id,
            "course": self.course.id,
        }

        serializer = RegistrationSerializer(data=data)
        with self.assertRaises(ValidationError) as exc:
            serializer.is_valid(raise_exception=True)
        self.assertIn("Cours complet", str(exc.exception))

    @mock.patch("activities.models.Course.full", new_callable=mock.PropertyMock)
    def test_course_does_not_allow_new_participants(self, mock_full):
        """Test if the course is marked as full"""
        self.course.allow_new_participants = False
        self.course.save()
        mock_full.return_value = False
        data = {
            "child": self.child.id,
            "course": self.course.id,
        }
        serializer = RegistrationSerializer(data=data)
        with self.assertRaises(ValidationError) as exc:
            serializer.is_valid(raise_exception=True)
        self.assertIn("Cours complet", str(exc.exception))

    @override_settings(KEPCHUP_LIMIT_BY_SCHOOL_YEAR=True)
    def test_registration_out_of_school_year(self):
        """Test if the child's school year is not allowed in the course"""
        self.child.school_year = SchoolYearFactory(year=self.school_year.year + 1)
        self.child.save()

        data = {
            "child": self.child.id,
            "course": self.course.id,
        }

        serializer = RegistrationSerializer(data=data)
        with self.assertRaises(ValidationError) as exc:
            serializer.is_valid(raise_exception=True)
        self.assertIn("Ce cours n'est pas ouvert aux élèves de", str(exc.exception))

    @override_settings(KEPCHUP_LIMIT_BY_SCHOOL_YEAR=True)
    def test_registration_accepted_for_school_year_unrestricted_course(self):
        # Regression test: course.school_years returns [] (not "every year") for a
        # course with no school-year restriction, so `child.school_year.year not in
        # course.school_years` used to be True for every child - rejecting every
        # registration attempt on an unrestricted course instead of accepting all of
        # them.
        self.child.school_year = self.school_year
        self.child.save()
        with override_settings(KEPCHUP_EXPLICIT_SESSION_DATES=False):
            unrestricted_course = CourseFactory(schoolyear_min=None, schoolyear_max=None, start_date=date.today())
        data = {
            "child": self.child.id,
            "course": unrestricted_course.id,
        }

        serializer = RegistrationSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    @override_settings(KEPCHUP_LIMIT_BY_SCHOOL_YEAR=True, KEPCHUP_EXPLICIT_SESSION_DATES=True)
    def test_registration_accepted_for_school_year_unrestricted_course_with_explicit_session_dates(self):
        # Coverage gap found 2026-08-18 auditing Montreux's real settings combo (school
        # year + explicit session dates together, never combined in a test before) - a
        # real Session, not a passed-in start_date (which KEPCHUP_EXPLICIT_SESSION_DATES
        # wipes on save() anyway), is what an actual open-for-registration course has.
        self.child.school_year = self.school_year
        self.child.save()
        unrestricted_course = CourseFactory(schoolyear_min=None, schoolyear_max=None)
        unrestricted_course.add_session(date.today())
        data = {
            "child": self.child.id,
            "course": unrestricted_course.id,
        }

        serializer = RegistrationSerializer(data=data)

        self.assertTrue(serializer.is_valid(), serializer.errors)

    @override_settings(KEPCHUP_LIMIT_BY_SCHOOL_YEAR=False)
    def test_registration_age_too_young(self):
        """Test if the child's birth date is outside the allowed range"""
        too_young_birth_date = date.today() - relativedelta(years=self.age_min - 1)
        self.child.birth_date = too_young_birth_date
        self.child.save()

        data = {
            "child": self.child.id,
            "course": self.course.id,
        }

        serializer = RegistrationSerializer(data=data)
        with self.assertRaises(ValidationError) as exc:
            serializer.is_valid(raise_exception=True)
        self.assertIn("Ce cours n'est pas ouvert aux élèves de cet âge", str(exc.exception))

    @override_settings(KEPCHUP_LIMIT_BY_SCHOOL_YEAR=False)
    def test_registration_age_too_old(self):
        """Test if the child's birth date is outside the allowed range"""
        # course.max_birth_date is itself an inclusive boundary (Course.save() adds +1 to
        # age_max so a child on their (age_max+1)th birthday is still accepted) - go one
        # day further to land unambiguously outside the valid range.
        too_old_birth_date = self.course.max_birth_date - relativedelta(days=1)
        self.child.birth_date = too_old_birth_date
        self.child.save()

        data = {
            "child": self.child.id,
            "course": self.course.id,
        }

        serializer = RegistrationSerializer(data=data)
        with self.assertRaises(ValidationError) as exc:
            serializer.is_valid(raise_exception=True)
        self.assertIn("Ce cours n'est pas ouvert aux élèves de cet âge", str(exc.exception))

    def test_max_registrations_reached(self):
        """Test if the child has already reached the max number of registrations"""
        preferences = global_preferences_registry.manager()
        original_max_registrations = preferences["MAX_REGISTRATIONS"]
        # dynamic_preferences caches values outside the DB transaction rollback, so this
        # would otherwise leak into every later test in the same process - restore it.
        self.addCleanup(lambda: preferences.__setitem__("MAX_REGISTRATIONS", original_max_registrations))
        preferences["MAX_REGISTRATIONS"] = 1
        Registration.objects.create(
            child=self.child,
            course=CourseFactory(),
        )

        data = {
            "child": self.child.id,
            "course": self.course.id,
        }

        serializer = RegistrationSerializer(data=data)
        with self.assertRaises(ValidationError) as exc:
            serializer.is_valid(raise_exception=True)
        self.assertIn("Nombre maximum de participants atteint.", str(exc.exception))
