from unittest.mock import patch
from urllib.parse import urlencode

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.test import SimpleTestCase
from django.test import override_settings
from django.urls import resolve
from django.urls import reverse

from activities.tests.factories import CourseFactory
from backend.views import activity_views
from backend.views import course_views
from backend.views import registration_views
from backend.views import teacher_views
from backend.views import user_views
from backend.views.mixins import LIST_RETURN_NAMES
from backend.views.mixins import ListReturnMixin
from profiles.tests.factories import FamilyUserFactory
from registrations.models import Transport
from registrations.tests.factories import BillFactory
from registrations.tests.factories import RegistrationFactory
from schools.tests.factories import TeacherFactory
from sportfac.utils import TenantTestCase

from .base import fake_registrations_open_middleware


class ListReturnURLTests(SimpleTestCase):
    def get_return(self, value):
        view = ListReturnMixin()
        view.request = RequestFactory().get("/edit/", {"list_return": value})
        return view.get_list_return_url()

    def test_each_supported_list_preserves_filters(self):
        query = urlencode({"q": "ski & été", "page": 3, "length": 50, "panes": "[]", "status": "paid"})
        for name in LIST_RETURN_NAMES:
            with self.subTest(name=name):
                target = reverse(f"backend:{name}") + "?" + query
                self.assertEqual(self.get_return(target), target)

    def test_unsafe_or_unrelated_destinations_are_ignored(self):
        for target in (
            "https://example.com/backend/user/",
            "//example.com/backend/user/",
            "/backend/user/../",
            "/backend/course/1/delete/",
            "javascript:alert(1)",
            "https://[",
            "\n/backend/user/",
        ):
            with self.subTest(target=target):
                self.assertIsNone(self.get_return(target))

    def test_nested_return_and_unrelated_parameters_are_removed(self):
        target = reverse("backend:user-list")
        self.assertEqual(self.get_return(target + "?q=ski&list_return=evil&next=evil"), target + "?q=ski")


@override_settings(KEPCHUP_EXPLICIT_SESSION_DATES=False)
class ListReturnViewTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.manager = FamilyUserFactory(is_manager=True)
        self.parent = FamilyUserFactory()
        self.course = CourseFactory()
        self.bill = BillFactory()
        self.registration = RegistrationFactory(course=self.course, bill=self.bill)
        self.teacher = TeacherFactory()
        self.transport = Transport.objects.create(name="Bus")
        self.target = reverse("backend:instructor-list") + "?" + urlencode({"q": "ski & été", "page": 2})
        self.views = [
            (activity_views.ActivityDetailView, {"activity": self.course.activity.slug}),
            (activity_views.ActivityUpdateView, {"activity": self.course.activity.slug}),
            (course_views.CourseDetailView, {"course": self.course.pk}),
            (course_views.CourseUpdateView, {"course": self.course.pk}),
            (teacher_views.TeacherDetailView, {"pk": self.teacher.pk}),
            (teacher_views.TeacherUpdateView, {"pk": self.teacher.pk}),
            (user_views.UserDetailView, {"pk": self.parent.pk}),
            (user_views.InstructorDetailView, {"pk": self.parent.pk}),
            (user_views.UserUpdateView, {"pk": self.parent.pk}),
            (user_views.ChildDetailView, {"child": self.registration.child.pk}),
            (user_views.ChildUpdateView, {"child": self.registration.child.pk}),
            (registration_views.RegistrationDetailView, {"pk": self.registration.pk}),
            (registration_views.RegistrationUpdateView, {"pk": self.registration.pk}),
            (registration_views.BillDetailView, {"pk": self.bill.pk}),
            (registration_views.BillUpdateView, {"pk": self.bill.pk}),
            (registration_views.TransportDetailView, {"pk": self.transport.pk}),
            (registration_views.TransportUpdateView, {"pk": self.transport.pk}),
        ]

    def request(self, user):
        request = RequestFactory().get("/edit/", {"list_return": self.target})
        request.user = user
        fake_registrations_open_middleware(request)
        return request

    def test_details_and_edit_forms_render_return_link(self):
        for view, kwargs in self.views:
            with self.subTest(view=view.__name__):
                response = view.as_view()(self.request(self.manager), **kwargs)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context_data["list_return_url"], self.target)
                self.assertContains(response, "list-return-url")

    def test_supported_list_templates_load_url_state_helper(self):
        for name in LIST_RETURN_NAMES:
            with self.subTest(name=name):
                url = reverse(f"backend:{name}")
                request = self.request(self.manager)
                response = resolve(url).func(request)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "backend/js/datatable-url-state.js")

    def test_return_parameter_does_not_bypass_permissions(self):
        for view, kwargs in self.views:
            for user in (AnonymousUser(), self.parent):
                with self.subTest(view=view.__name__, user=user):
                    response = view.as_view()(self.request(user), **kwargs)
                    self.assertEqual(response.status_code, 302)
                    self.assertTrue(response.url.startswith(reverse("profiles:auth_login")))

    def test_all_update_views_return_to_originating_list(self):
        for view_class, kwargs in self.views:
            if "Update" not in view_class.__name__:
                continue
            with self.subTest(view=view_class.__name__):
                view = view_class()
                view.setup(self.request(self.manager), **kwargs)
                self.assertEqual(view.get_success_url(), self.target)

    @patch("django.contrib.messages.success")
    def test_successful_transport_edit_redirects_to_filtered_list(self, _):
        url = reverse("backend:transport-update", kwargs={"pk": self.transport.pk})
        request = RequestFactory().post(url + "?" + urlencode({"list_return": self.target}), {"name": "Bus modifié"})
        request.user = self.manager
        fake_registrations_open_middleware(request)
        response = registration_views.TransportUpdateView.as_view()(request, pk=self.transport.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.target)
        self.transport.refresh_from_db()
        self.assertEqual(self.transport.name, "Bus modifié")

    def test_invalid_form_keeps_return_context(self):
        request = self.request(self.manager)
        request.method = "POST"
        request.POST = {"name": ""}
        response = registration_views.TransportUpdateView.as_view()(request, pk=self.transport.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data["list_return_url"], self.target)
