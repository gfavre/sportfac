from datetime import date

from bs4 import BeautifulSoup
from diplomas.views import BatchCreateView
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.test import override_settings
from django.urls import reverse

from activities.tests.factories import CourseFactory
from backend import views
from profiles.tests.factories import FamilyUserFactory
from registrations.tests.factories import ChildFactory
from sportfac.utils import TenantTestCase

from .base import fake_registrations_open_middleware


class CreationLayoutTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.manager = FamilyUserFactory(is_manager=True)
        self.family = FamilyUserFactory()
        self.course = CourseFactory()
        self.cases = [
            (views.ActivityCreateView, {}, "activity-list"),
            (views.CourseCreateView, {}, "course-list"),
            (views.AllocationAccountCreateView, {}, "allocation-list"),
            (views.FunctionCreateView, {}, "function-list"),
            (views.TransportCreateView, {}, "transport-list"),
            (views.TeacherCreateView, {}, "teacher-list"),
            (views.BuildingCreateView, {}, "building-list"),
            (views.ChildCreateView, {}, "child-list"),
            (views.ChildCreateView, {"user": self.family.pk}, self.family.get_backend_url()),
            (views.YearCreateView, {}, "year-list"),
            (views.WaitingSlotCreateView, {"course_id": self.course.pk}, self.course.get_backend_url()),
            (
                views.PaySlipMontreux,
                {"course": self.course.pk, "instructor": self.manager.pk},
                self.course.get_backend_url(),
            ),
            (BatchCreateView, {}, "diploma-list"),
        ]

    def request(self, user=None, data=None):
        factory = RequestFactory()
        request = factory.get("/create") if data is None else factory.post("/create", data)
        request.user = self.manager if user is None else user
        fake_registrations_open_middleware(request)
        return request

    @override_settings(KEPCHUP_DIPLOMAS=True)
    def test_creation_pages_have_one_form_and_consistent_actions(self):
        for view, kwargs, destination in self.cases:
            with self.subTest(view=view.__name__, kwargs=kwargs):
                response = view.as_view()(self.request(), **kwargs)
                if hasattr(response, "render"):
                    response.render()
                self.assertEqual(response.status_code, 200)
                soup = BeautifulSoup(response.content, "html.parser")
                forms = soup.select("form.paper-prepare-form")
                self.assertEqual(len(forms), 1)
                form = forms[0]
                self.assertIsNone(form.find("form"))
                self.assertEqual(len(form.select('button[type="submit"], input[type="submit"]')), 1)
                actions = form.select_one(".paper-prepare-actions")
                self.assertIsNotNone(actions)
                target = destination if destination.startswith("/") else reverse("backend:" + destination)
                self.assertEqual(actions.select_one("a")["href"], target)
                self.assertIsNotNone(soup.select_one("h1 i, h2 i"))

    @override_settings(KEPCHUP_DIPLOMAS=True)
    def test_creation_pages_require_backend_access(self):
        for view, kwargs, _ in self.cases:
            for user in (AnonymousUser(), self.family):
                with self.subTest(view=view.__name__, user=user):
                    self.assertEqual(view.as_view()(self.request(user=user), **kwargs).status_code, 302)

    def test_invalid_activity_still_shows_errors_and_creation_actions(self):
        response = views.ActivityCreateView.as_view()(self.request(data={})).render()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context_data["form"].errors)
        self.assertContains(response, "paper-prepare-actions")

    def test_agenda_creation_modal_uses_shared_layout_and_permissions(self):
        view = views.AppointmentsManagementView.as_view()
        response = view(self.request()).render()
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, "html.parser")
        form = soup.select_one("#calendar-modal form.paper-prepare-form")
        self.assertIsNotNone(form)
        self.assertEqual(len(form.select('button[type="submit"]')), 1)
        self.assertIsNotNone(form.select_one(".paper-prepare-actions"))
        for user in (AnonymousUser(), self.family):
            self.assertEqual(view(self.request(user=user)).status_code, 302)

    def test_activity_creation_respects_optional_account_setting(self):
        for enabled in (False, True):
            with self.subTest(enabled=enabled), override_settings(KEPCHUP_ENABLE_ALLOCATION_ACCOUNTS=enabled):
                response = views.ActivityCreateView.as_view()(self.request()).render()
                if enabled:
                    self.assertContains(response, 'name="allocation_account"')
                else:
                    self.assertNotContains(response, 'name="allocation_account"')

    def test_child_update_keeps_its_existing_submit_button(self):
        child = ChildFactory()
        response = views.ChildUpdateView.as_view()(self.request(), child=child.pk).render()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="action" value="save"')

    def test_child_creation_defaults_to_french(self):
        for kwargs in ({}, {"user": self.family.pk}):
            with self.subTest(kwargs=kwargs):
                response = views.ChildCreateView.as_view()(self.request(), **kwargs).render()
                soup = BeautifulSoup(response.content, "html.parser")
                self.assertEqual(soup.select_one('select[name="language"] option[selected]')["value"], "F")

    def test_invalid_child_creation_preserves_selected_language(self):
        response = views.ChildCreateView.as_view()(self.request(data={"language": "I"})).render()
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, "html.parser")
        self.assertEqual(soup.select_one('select[name="language"] option[selected]')["value"], "I")

    @override_settings(KEPCHUP_EXPLICIT_SESSION_DATES=True)
    def test_pay_slip_initial_dates_keep_swiss_format(self):
        self.course.add_session(date(2026, 2, 7))
        response = views.PaySlipMontreux.as_view()(
            self.request(), course=self.course.pk, instructor=self.manager.pk
        ).render()
        self.assertContains(response, 'value="07.02.2026"', count=2)
