# -*- coding: utf-8 -*-
from __future__ import absolute_import
from datetime import date, time

from django.conf import settings
from django.test import override_settings

from mock import patch
import faker

from absences.models import Session
from absences.tests.factories import SessionFactory
from registrations.tests.factories import RegistrationFactory
from sportfac.utils import TenantTestCase as TestCase
from ..models import Course
from .factories import ActivityFactory, CourseFactory

fake = faker.Faker()


class ActivityTest(TestCase):
    def setUp(self):
        super(ActivityTest, self).setUp()
        self.activity = ActivityFactory()

    def test_backend_absences_url(self):
        self.assertTrue(len(self.activity.backend_absences_url) > 0)

    def test_backend_url(self):
        self.assertTrue(len(self.activity.backend_url) > 0)

    def test_delete_url(self):
        self.assertTrue(len(self.activity.delete_url) > 0)

    def test_participants(self):
        registration = RegistrationFactory(course__activity=self.activity)
        self.assertEqual(self.activity.participants.count(), 1)

    def test_update_url(self):
        self.assertTrue(len(self.activity.update_url) > 0)

    def test_get_absolute_url(self):
        self.assertTrue(len(self.activity.get_absolute_url()) > 0)

    def test_get_backend_url(self):
        self.assertTrue(len(self.activity.get_backend_url()) > 0)

    def test_get_delete_url(self):
        self.assertTrue(len(self.activity.get_delete_url()) > 0)

    def test_get_update_url(self):
        self.assertTrue(len(self.activity.get_update_url()) > 0)

    def test_str(self):
        activity = ActivityFactory()
        self.assertEqual(str(activity), activity.name)


class CourseTest(TestCase):
    def setUp(self):
        super(CourseTest, self).setUp()
        self.course = CourseFactory()

    def test_ages(self):
        ages = self.course.ages
        self.assertEqual(ages[0], self.course.age_min)
        self.assertEqual(ages[1], self.course.age_max)
        self.assertTrue(sorted(ages) == ages)

    def test_ages_default_values(self):
        self.course.age_min = None
        self.course.age_max = None
        ages = self.course.ages
        self.assertEqual(ages[0], settings.KEPCHUP_AGES[0])
        self.assertEqual(ages[-1], settings.KEPCHUP_AGES[-1])

    def test_ages_label(self):
        labels = self.course.ages_label
        self.assertEqual(len(labels), 1 + self.course.age_max - self.course.age_min)

    def test_available_places(self):
        RegistrationFactory.create_batch(size=self.course.max_participants, course=self.course)
        self.assertEqual(self.course.available_places, 0)

    def test_backend_absences_url(self):
        self.assertTrue(len(self.course.backend_absences_url) > 0)

    def test_backend_url(self):
        self.assertTrue(len(self.course.backend_url) > 0)

    def test_count_participants(self):
        self.assertEqual(self.course.count_participants, 0)

    def test_day_name_course(self):
        self.assertTrue(len(self.course.day_name) > 0)
        self.assertFalse(self.course.day_name.isdigit())

    def test_day_name_camp(self):
        self.course.course_type = 'camp'
        self.assertTrue(len(self.course.day_name) > 0)
        self.assertIn('-', self.course.day_name)

    def test_days_names(self):
        self.course.start_time_mon = '10:00'
        self.course.start_time_tue = '10:00'
        self.course.start_time_wed = '10:00'
        self.course.start_time_thu = '10:00'
        self.course.start_time_fri = '10:00'
        self.course.start_time_sat = '10:00'
        self.course.start_time_sun = '10:00'
        self.assertEqual(len(self.course.days_names), 7)
        self.assertFalse(self.course.days_names[0].isdigit())

    def test_delete_url(self):
        self.assertTrue(len(self.course.delete_url) > 0)

    def test_duration_course(self):
        self.course.start_time = time(10, 0)
        self.course.end_time = time(12, 0)
        duration = self.course.duration
        self.assertEqual(duration.seconds, 2 * 3600)

    def test_duration_multicourse(self):
        self.course.course_type = 'multicourse'
        self.course.start_time_mon = time(10, 0)
        self.course.end_time_mon = time(12, 0)
        self.course.start_time_sun = time(10, 0)
        self.course.end_time_sun = time(15, 0)
        duration = self.course.duration
        self.assertEqual(duration.seconds, 5 * 3600)

    @override_settings(KEPCHUP_EXPLICIT_SESSION_DATES=False)
    def test_duration_camp(self):
        self.course.course_type = 'camp'
        self.course.start_date = date(2022, 1, 1)
        self.course.end_date = date(2022, 1, 5)
        duration = self.course.duration
        self.assertEqual(duration.days, 5)

    @override_settings(KEPCHUP_EXPLICIT_SESSION_DATES=True)
    def test_duration_camp_explicit_session_dates(self):
        self.course.course_type = 'camp'
        SessionFactory(course=self.course, date=date(2022, 1, 1))
        SessionFactory(course=self.course, date=date(2022, 1, 2))
        SessionFactory(course=self.course, date=date(2022, 1, 3))
        duration = self.course.duration
        self.assertEqual(duration.days, 3)

    def test_full(self):
        RegistrationFactory.create_batch(size=self.course.max_participants, course=self.course)
        self.assertTrue(self.course.full)

    def test_js_name(self):
        self.assertTrue(len(self.course.get_js_name) > 0)

    def test_has_issue(self):
        RegistrationFactory.create_batch(size=self.course.max_participants + 1, course=self.course)
        self.assertTrue(self.course.has_issue)

    def test_has_participants(self):
        self.assertFalse(self.course.has_participants)
        RegistrationFactory(course=self.course)
        self.assertTrue(self.course.has_participants)

    def test_start_hours(self):
        self.course.start_time_mon = '10:00'
        self.course.start_time_tue = '10:00'
        self.course.start_time_wed = '10:00'
        self.course.start_time_thu = '10:00'
        self.course.start_time_fri = '10:00'
        self.course.start_time_sat = '10:00'
        self.course.start_time_sun = '10:00'
        self.assertEqual(len(self.course.start_hours), 7)

    def test_is_course(self):
        self.course.course_type = 'course'
        self.assertTrue(self.course.is_course)
        self.assertFalse(self.course.is_camp)
        self.assertFalse(self.course.is_multi_course)

    def test_is_camp(self):
        self.course.course_type = 'camp'
        self.assertFalse(self.course.is_course)
        self.assertTrue(self.course.is_camp)
        self.assertFalse(self.course.is_multi_course)

    def test_is_multi_course(self):
        self.course.course_type = 'multicourse'
        self.assertFalse(self.course.is_course)
        self.assertFalse(self.course.is_camp)
        self.assertTrue(self.course.is_multi_course)

    def test_add_session_fill_absences(self):
        with patch.object(Session, 'fill_absences') as mock_fill_absences:
            self.course.add_session(date(2022, 1, 1))
            self.assertTrue(mock_fill_absences.called)

    def test_add_session_creates_session(self):
        self.course.add_session(date(2022, 1, 1))
        self.assertEqual(Session.objects.count(), 1)
        session = Session.objects.first()
        self.assertEqual(session.course, self.course)

    @override_settings(KEPCHUP_ABSENCES_RELATE_TO_ACTIVITIES=True)
    def test_add_session_creates_session_related_to_activity(self):
        self.course.add_session(date(2022, 1, 1))
        self.assertEqual(Session.objects.count(), 1)
        session = Session.objects.first()
        self.assertEqual(session.activity, self.course.activity)
        self.assertEqual(session.course, self.course)

    @override_settings(KEPCHUP_EXPLICIT_SESSION_DATES=True)
    def test_add_session_update_course_dates(self):
        adate = fake.future_date()
        self.course.add_session(adate)
        self.course.refresh_from_db()
        self.assertEqual(self.course.end_date, adate)

    def test_save_updates_participants(self):
        with patch.object(Course, 'update_nb_participants') as mock_update_nb_participants:
            self.course.save()
            mock_update_nb_participants.assert_called_once()
        self.course.refresh_from_db()

    @override_settings(KEPCHUP_EXPLICIT_SESSION_DATES=True)
    def test_save_updates_dates_from_sessions(self):
        with patch.object(Course, 'update_dates_from_sessions') as mock_update_dates_from_sessions:
            self.course.save()
            mock_update_dates_from_sessions.assert_called_once()

    def test_save_updates_min_birth_date(self):
        self.course.age_min = 5
        self.course.start_date = date(2022, 1, 1)
        self.course.min_birth_date = None
        self.course.save()
        self.assertEqual(self.course.min_birth_date, date(2017, 1, 1))

    def test_save_updates_max_birth_date(self):
        self.course.age_max = 10
        self.course.start_date = date(2022, 1, 1)
        self.course.max_birth_date = None
        self.course.save()
        self.assertEqual(self.course.max_birth_date, date(2011, 1, 1))

    def test_str(self):
        self.assertTrue(len(str(self.course)) > 0)