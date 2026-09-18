from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory
from django.test import override_settings

from backend.views.registration_views import GenerateBibsView
from profiles.tests.factories import FamilyUserFactory
from registrations.models import Transport
from registrations.tests.factories import RegistrationFactory
from sportfac.utils import TenantTestCase

from .base import fake_registrations_open_middleware


@override_settings(KEPCHUP_EXPLICIT_SESSION_DATES=False)
class GenerateBibsViewTests(TenantTestCase):
    def test_autosave_returns_updated_readiness_without_changing_other_children(self):
        first = RegistrationFactory(transport=None)
        other = RegistrationFactory(transport=None)
        car = Transport.objects.create(name="Bus", bib_prefix=3)
        request = self.request(
            FamilyUserFactory(is_manager=True), "post", {"action": "assign", f"child_{first.child_id}": str(car.pk)}
        )
        request.META["HTTP_X_REQUESTED_WITH"] = "XMLHttpRequest"
        response = GenerateBibsView.as_view()(request)
        self.assertEqual(response["X-Bib-Saved"], "true")
        self.assertContains(response, "Enregistrement", status_code=200)
        self.assertEqual(response.context_data["ready_count"], 1)
        self.assertEqual(response.context_data["children_count"], 2)
        self.assertEqual([entry["child"].pk for entry in response.context_data["children"]], [first.child_id])
        first.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(first.transport_id, car.pk)
        self.assertIsNone(other.transport_id)
        self.assertEqual(first.child.bib_number, "")

    def test_invalid_autosave_does_not_report_success(self):
        registration = RegistrationFactory(transport=None)
        request = self.request(
            FamilyUserFactory(is_manager=True), "post", {"action": "assign", f"child_{registration.child_id}": "-1"}
        )
        request.META["HTTP_X_REQUESTED_WITH"] = "XMLHttpRequest"
        response = GenerateBibsView.as_view()(request)
        self.assertNotIn("X-Bib-Saved", response)
        self.assertTrue(response.context_data["assignment_form"].errors)
        registration.refresh_from_db()
        self.assertIsNone(registration.transport_id)

    def request(self, user, method="get", data=None):
        request = getattr(RequestFactory(), method)("/backend/transport/generate-bibs/", data or {})
        request.user = user
        request.session = {}
        request._messages = FallbackStorage(request)
        fake_registrations_open_middleware(request)
        return request

    def test_manager_confirmation_page_and_post(self):
        manager = FamilyUserFactory(is_manager=True)
        child = RegistrationFactory(transport=Transport.objects.create(name="Bus", bib_prefix=3)).child
        response = GenerateBibsView.as_view()(self.request(manager))
        self.assertContains(response, "csrfmiddlewaretoken", status_code=200)
        child.refresh_from_db()
        self.assertEqual(child.bib_number, "")
        response = GenerateBibsView.as_view()(self.request(manager, "post"))
        self.assertEqual(response.status_code, 302)
        child.refresh_from_db()
        self.assertEqual(child.bib_number, "301")
        response = GenerateBibsView.as_view()(self.request(manager, "post"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context_data["form"].non_field_errors())
        response = GenerateBibsView.as_view()(self.request(manager, "post", {"overwrite": "on"}))
        self.assertEqual(response.status_code, 302)

    def test_parent_anonymous_and_restricted_manager_cannot_generate(self):
        for user in (AnonymousUser(), FamilyUserFactory(), FamilyUserFactory(is_restricted_manager=True)):
            for method in ("get", "post"):
                with self.subTest(user=user, method=method):
                    response = GenerateBibsView.as_view()(self.request(user, method))
                    self.assertEqual(response.status_code, 302)

    def test_missing_assignments_are_grouped_per_child_with_edit_links(self):
        first = RegistrationFactory(transport=None)
        second = RegistrationFactory(child=first.child, transport=None)
        RegistrationFactory(status="canceled", transport=None)
        response = GenerateBibsView.as_view()(self.request(FamilyUserFactory(is_manager=True)))
        self.assertEqual(response.context_data["children_count"], 1)
        self.assertEqual(len(response.context_data["pending_children"]), 1)
        self.assertFalse(response.context_data["can_generate"])
        self.assertContains(response, first.update_url)
        self.assertContains(response, second.update_url)
        self.assertContains(response, " disabled")

    def test_conflicting_cars_and_missing_prefix_are_shown(self):
        car = Transport.objects.create(name="Sans préfixe")
        first = RegistrationFactory(transport=car)
        response = GenerateBibsView.as_view()(self.request(FamilyUserFactory(is_manager=True)))
        self.assertContains(response, "Préfixe du car manquant")
        self.assertContains(response, f'<a href="{car.update_url}">Préfixe du car manquant</a>', html=True)
        self.assertContains(response, car.update_url)
        RegistrationFactory(child=first.child, transport=Transport.objects.create(name="Autre", bib_prefix=4))
        response = GenerateBibsView.as_view()(self.request(FamilyUserFactory(is_manager=True)))
        self.assertContains(response, "Plusieurs cars affectés au même enfant")

    def test_empty_population_cannot_be_generated(self):
        manager = FamilyUserFactory(is_manager=True)
        response = GenerateBibsView.as_view()(self.request(manager))
        self.assertContains(response, "Aucun enfant avec une inscription active")
        self.assertFalse(response.context_data["can_generate"])
        response = GenerateBibsView.as_view()(self.request(manager, "post"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context_data["form"].non_field_errors())

    def test_assignments_update_all_active_registrations_without_generating_bibs(self):
        first = RegistrationFactory(transport=None)
        second = RegistrationFactory(child=first.child, transport=None)
        canceled = RegistrationFactory(child=first.child, transport=None, status="canceled")
        other = RegistrationFactory(transport=None)
        car = Transport.objects.create(name="Bus", bib_prefix=3)
        response = GenerateBibsView.as_view()(
            self.request(
                FamilyUserFactory(is_manager=True),
                "post",
                {"action": "assign", f"child_{first.child_id}": str(car.pk), f"child_{other.child_id}": str(car.pk)},
            )
        )
        self.assertEqual(response.status_code, 302)
        for registration in (first, second, other):
            registration.refresh_from_db()
            self.assertEqual(registration.transport_id, car.pk)
            self.assertEqual(registration.child.bib_number, "")
        canceled.refresh_from_db()
        self.assertIsNone(canceled.transport_id)

    def test_blank_conflict_choice_preserves_existing_assignments(self):
        first = RegistrationFactory(transport=Transport.objects.create(name="A", bib_prefix=1))
        second = RegistrationFactory(child=first.child, transport=Transport.objects.create(name="B", bib_prefix=2))
        initial = [first.transport_id, second.transport_id]
        response = GenerateBibsView.as_view()(
            self.request(
                FamilyUserFactory(is_manager=True), "post", {"action": "assign", f"child_{first.child_id}": ""}
            )
        )
        self.assertEqual(response.status_code, 302)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual([first.transport_id, second.transport_id], initial)

    def test_invalid_car_rejects_entire_assignment_submission(self):
        first = RegistrationFactory(transport=None)
        second = RegistrationFactory(transport=None)
        car = Transport.objects.create(name="Bus", bib_prefix=3)
        response = GenerateBibsView.as_view()(
            self.request(
                FamilyUserFactory(is_manager=True),
                "post",
                {"action": "assign", f"child_{first.child_id}": str(car.pk), f"child_{second.child_id}": "-1"},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context_data["assignment_form"].errors)
        first.refresh_from_db()
        self.assertIsNone(first.transport_id)

    def test_parent_cannot_assign(self):
        registration = RegistrationFactory(transport=None)
        car = Transport.objects.create(name="Bus", bib_prefix=3)
        response = GenerateBibsView.as_view()(
            self.request(
                FamilyUserFactory(), "post", {"action": "assign", f"child_{registration.child_id}": str(car.pk)}
            )
        )
        self.assertEqual(response.status_code, 302)
        registration.refresh_from_db()
        self.assertIsNone(registration.transport_id)
