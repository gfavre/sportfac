import random
from datetime import date, timedelta
from unittest import mock

from django.conf import settings

from activities.tests.factories import CourseFactory
from dynamic_preferences.registries import global_preferences_registry
from profiles.tests.factories import SchoolYearFactory
from registrations.models import Registration
from registrations.tests.factories import ChildFactory
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIRequestFactory

from sportfac.utils import TenantTestCase

from ..serializers import RegistrationSerializer


class RegistrationSerializerTest(TenantTestCase):
    def setUp(self):
        # Set up necessary data
        self.child = ChildFactory()
        self.school_year = SchoolYearFactory()
        self.age_min = random.randint(6, 12)
        self.age_max = self.age_min + 1

        self.course = CourseFactory(
            schoolyear_min=self.school_year.year,
            schoolyear_max=self.school_year.year,
            age_min=self.age_min,
            age_max=self.age_max,
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

    def test_registration_out_of_school_year(self):
        """Test if the child's school year is not allowed in the course"""
        settings.KEPCHUP_LIMIT_BY_SCHOOL_YEAR = True
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

    def test_registration_age_too_young(self):
        """Test if the child's birth date is outside the allowed range"""
        settings.KEPCHUP_LIMIT_BY_SCHOOL_YEAR = False

        too_young_birth_date = date.today() - timedelta(days=365 * (self.age_min - 1))
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

    def test_registration_age_too_old(self):
        """Test if the child's birth date is outside the allowed range"""
        settings.KEPCHUP_LIMIT_BY_SCHOOL_YEAR = False

        too_old_birth_date = date.today() - timedelta(days=365 * (self.age_max + 1))  # One year older than the max age
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
        global_preferences_registry.manager()["MAX_REGISTRATIONS"] = 1
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
