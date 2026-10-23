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
        self.assertEqual(response.status_code, 302)
        child.refresh_from_db()
        self.assertEqual(child.bib_number, "301")
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
        RegistrationFactory(child=first.child, transport=None)
        RegistrationFactory(status="canceled", transport=None)
        response = GenerateBibsView.as_view()(self.request(FamilyUserFactory(is_manager=True)))
        self.assertEqual(response.context_data["children_count"], 1)
        self.assertEqual(len(response.context_data["pending_children"]), 1)
        self.assertFalse(response.context_data["can_generate"])
        self.assertContains(response, " disabled")
        self.assertContains(response, "Traiter les affectations à compléter")

    def test_conflicting_cars_and_missing_prefix_are_shown(self):
        car = Transport.objects.create(name="Sans préfixe")
        first = RegistrationFactory(transport=car)
        response = GenerateBibsView.as_view()(self.request(FamilyUserFactory(is_manager=True)))
        self.assertContains(response, "Préfixe du car manquant")
        self.assertContains(response, f'<a href="{car.update_url}?from=bibs">Préfixe du car manquant</a>', html=True)
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

    def test_stale_assignment_submission_never_generates_bibs(self):
        child = RegistrationFactory(transport=Transport.objects.create(name="Bus", bib_prefix=3)).child
        response = GenerateBibsView.as_view()(
            self.request(FamilyUserFactory(is_manager=True), "post", {"action": "assign"})
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/assignments/", response.url)
        child.refresh_from_db()
        self.assertEqual(child.bib_number, "")

    def test_disabled_generation_explains_why_and_links_to_assignments(self):
        RegistrationFactory(transport=None)
        response = GenerateBibsView.as_view()(self.request(FamilyUserFactory(is_manager=True)))
        self.assertContains(response, "La génération est bloquée pour tous les cars.", status_code=200)
        self.assertContains(response, 'aria-describedby="bib-generation-blocked"')
        self.assertContains(response, "Corriger la répartition des enfants")

    def test_correction_links_target_pending_children_and_exact_child_not_profile(self):
        registration = RegistrationFactory(transport=None)
        response = GenerateBibsView.as_view()(self.request(FamilyUserFactory(is_manager=True)))
        self.assertContains(response, "?car=pending&amp;from=bibs", status_code=200)
        self.assertContains(response, f"?child={registration.child_id}&amp;from=bibs")
        self.assertNotContains(response, f'href="{registration.child.backend_url}"')

    def test_preflight_blocks_duplicate_bibs_before_submit(self):
        car = Transport.objects.create(name="Car", bib_prefix=3)
        RegistrationFactory(transport=car, child__bib_number="301")
        RegistrationFactory(transport=car, child__bib_number="301")
        response = GenerateBibsView.as_view()(self.request(FamilyUserFactory(is_manager=True)))
        self.assertFalse(response.context_data["can_generate"])
        self.assertContains(response, "Le dossard 301 est déjà attribué à plusieurs enfants.", status_code=200)

    def test_summary_separates_missing_numbers_and_preserved_numbers(self):
        car = Transport.objects.create(name="Car", bib_prefix=3)
        RegistrationFactory(transport=car, child__bib_number="701")
        RegistrationFactory(transport=car)
        response = GenerateBibsView.as_view()(self.request(FamilyUserFactory(is_manager=True)))
        self.assertContains(
            response, "1 enfant(s) recevront un numéro ; 1 conserveront leur dossard.", status_code=200
        )
        self.assertContains(response, "hors de la plage du car, conservé(s)")
        self.assertNotContains(response, 'type="checkbox"')
        self.assertContains(response, "Voir les numéros prévus")

    def test_replacement_has_its_own_preview_and_does_not_write_on_get(self):
        child = RegistrationFactory(
            transport=Transport.objects.create(name="Car", bib_prefix=3), child__bib_number="701"
        ).child
        request = self.request(FamilyUserFactory(is_manager=True))
        request.GET = request.GET.copy()
        request.GET["mode"] = "replace"
        response = GenerateBibsView.as_view()(request)
        self.assertContains(response, 'name="overwrite" value="on"', status_code=200)
        self.assertContains(response, "Recalculer tous les dossards")
        child.refresh_from_db()
        self.assertEqual(child.bib_number, "701")

    def test_success_returns_to_preparation_with_all_car_pdf_action(self):
        car = Transport.objects.create(name="Car", bib_prefix=3)
        RegistrationFactory(transport=car)
        manager = FamilyUserFactory(is_manager=True)
        response = GenerateBibsView.as_view()(self.request(manager, "post"))
        self.assertTrue(response.url.endswith("generate-bibs/"))
        response = GenerateBibsView.as_view()(self.request(manager))
        self.assertContains(response, 'name="t" value="%s"' % car.pk, status_code=200)
        self.assertContains(response, "Chaque enfant a un dossard.")

    def test_correcting_car_returns_to_bibs_and_preserves_access_checks(self):
        from backend.views.registration_views import TransportUpdateView

        car = Transport.objects.create(name="Sans préfixe")
        manager = FamilyUserFactory(is_manager=True)
        request = self.request(manager)
        request.GET = request.GET.copy()
        request.GET["from"] = "bibs"
        self.assertContains(TransportUpdateView.as_view()(request, pk=car.pk), 'name="capacity"', status_code=200)
        request = self.request(manager, "post", {"name": car.name, "bib_prefix": 3, "capacity": 48})
        request.GET = request.GET.copy()
        request.GET["from"] = "bibs"
        response = TransportUpdateView.as_view()(request, pk=car.pk)
        self.assertTrue(response.url.endswith("generate-bibs/"))
        car.refresh_from_db()
        self.assertEqual((car.bib_prefix, car.capacity), (3, 48))
        for method in ("get", "post"):
            response = TransportUpdateView.as_view()(self.request(FamilyUserFactory(), method), pk=car.pk)
            self.assertEqual(response.status_code, 302)
