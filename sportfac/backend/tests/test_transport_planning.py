from datetime import date

from django.test import RequestFactory
from django.test import override_settings

from absences.tests.factories import SessionFactory
from activities.tests.factories import CourseFactory
from backend.transport_planning import transport_occupancy
from backend.views.registration_views import TransportListView
from profiles.tests.factories import FamilyUserFactory
from registrations.forms import TransportForm
from registrations.models import Transport
from registrations.tests.factories import RegistrationFactory
from sportfac.utils import TenantTestCase

from .test_views.base import fake_registrations_open_middleware


@override_settings(KEPCHUP_EXPLICIT_SESSION_DATES=True)
class TransportPlanningTests(TenantTestCase):
    def test_occupancy_counts_children_once_per_date_and_keeps_canceled_out(self):
        car = Transport.objects.create(name="Car", capacity=2)
        first_course = CourseFactory()
        first_course.sessions.all().delete()
        second_course = CourseFactory()
        second_course.sessions.all().delete()
        SessionFactory(course=first_course, date=date(2026, 12, 5))
        SessionFactory(course=second_course, date=date(2026, 12, 12))
        first = RegistrationFactory(transport=car, course=first_course)
        same_day_course = CourseFactory()
        same_day_course.sessions.all().delete()
        SessionFactory(course=same_day_course, date=date(2026, 12, 5))
        RegistrationFactory(transport=car, course=same_day_course, child=first.child)
        RegistrationFactory(transport=car, course=second_course)
        RegistrationFactory(transport=car, course=first_course, status="canceled")
        occupancy = transport_occupancy([car])[car.pk]
        self.assertEqual(occupancy["peak"], 1)
        self.assertEqual(occupancy["remaining"], 1)
        self.assertEqual(occupancy["undated_count"], 0)
        self.assertFalse(occupancy["over_capacity"])

    def test_unknown_dates_and_missing_capacity_are_explicit(self):
        car = Transport.objects.create(name="Car")
        course = CourseFactory()
        course.sessions.all().delete()
        RegistrationFactory(transport=car, course=course)
        course.sessions.all().delete()
        with override_settings(KEPCHUP_EXPLICIT_SESSION_DATES=True):
            occupancy = transport_occupancy([car])[car.pk]
        self.assertIsNone(occupancy["remaining"])
        self.assertIsNone(occupancy["peak_date"])
        self.assertEqual(occupancy["undated_count"], 1)

    def test_capacity_form_remains_optional_and_rejects_negative_values(self):
        self.assertTrue(TransportForm(data={"name": "Car"}).is_valid())
        form = TransportForm(data={"name": "Car", "capacity": -1})
        self.assertFalse(form.is_valid())
        self.assertIn("capacity", form.errors)

    def test_car_list_counts_children_not_registrations(self):
        car = Transport.objects.create(name="Car")
        first = RegistrationFactory(transport=car)
        RegistrationFactory(transport=car, child=first.child)
        RegistrationFactory(transport=car, status="canceled")
        request = RequestFactory().get("/backend/registrations/transport")
        request.user = FamilyUserFactory(is_manager=True)
        fake_registrations_open_middleware(request)
        response = TransportListView.as_view()(request)
        self.assertEqual(response.context_data["transport_list"][0].children_count, 1)
        self.assertContains(response, "Enfants affectés", status_code=200)

    def test_capacity_warning_uses_dated_children_and_does_not_change_registrations(self):
        car = Transport.objects.create(name="Car", capacity=1)
        course = CourseFactory()
        first = RegistrationFactory(transport=car, course=course)
        RegistrationFactory(transport=car, course=course)
        course.sessions.all().delete()
        SessionFactory(course=course, date=date(2026, 12, 5))
        with override_settings(KEPCHUP_EXPLICIT_SESSION_DATES=True):
            occupancy = transport_occupancy([car])[car.pk]
        self.assertEqual(occupancy["peak"], 2)
        self.assertTrue(occupancy["over_capacity"])
        self.assertEqual(occupancy["remaining"], 0)
        first.refresh_from_db()
        self.assertEqual(first.transport_id, car.pk)

    def test_parent_cannot_access_planning_list(self):
        request = RequestFactory().get("/backend/registrations/transport")
        request.user = FamilyUserFactory()
        fake_registrations_open_middleware(request)
        self.assertEqual(TransportListView.as_view()(request).status_code, 302)
