from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.urls import reverse

from backend.views.site_views import WizardStepUpdateView
from profiles.tests.factories import FamilyUserFactory
from sportfac.utils import TenantTestCase
from wizard.tests.factories import WizardStepFactory

from .base import fake_registrations_open_middleware


class WizardStepUpdateTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.step = WizardStepFactory(slug="user-update", title="Coordonnées", link_display="Mes coordonnées")
        self.manager = FamilyUserFactory(is_manager=True)
        self.url = reverse("backend:wizard-step-update", kwargs={"slug": self.step.slug})
        self.view = WizardStepUpdateView.as_view()

    def request(self, data=None, user=None):
        factory = RequestFactory()
        request = factory.get(self.url) if data is None else factory.post(self.url, data)
        request.user = self.manager if user is None else user
        fake_registrations_open_middleware(request)
        return request

    def test_render_french_editor_and_actions_after_fields(self):
        response = self.view(self.request(), slug=self.step.slug).render()
        self.assertEqual(response.status_code, 200)
        for text in (
            "Modifier une étape",
            "Titre de l’étape",
            "Texte d’introduction",
            "Navigation entre les étapes",
            "Paramètres avancés",
            "Enregistrer les modifications",
            'class="icon-server"',
            'name="link_display"',
        ):
            self.assertContains(response, text)
        self.assertNotContains(response, "Update email")
        content = response.content.decode()
        self.assertLess(content.index('name="slug"'), content.index('type="submit"'))

    def test_permissions_for_get_and_post(self):
        for user in (AnonymousUser(), FamilyUserFactory(), FamilyUserFactory(is_restricted_manager=True)):
            for data in (None, {}):
                with self.subTest(user=user, data=data):
                    response = self.view(self.request(data=data, user=user), slug=self.step.slug)
                    self.assertEqual(response.status_code, 302)

    def test_save_content_and_navigation_label(self):
        data = {
            "title": "Vos coordonnées",
            "subtitle": "Famille",
            "lead": "Vérifiez vos coordonnées avant de continuer.",
            "description": "<p>Les informations utiles.</p>",
            "link_display": "Compléter mes coordonnées",
            "slug": self.step.slug,
        }
        response = self.view(self.request(data), slug=self.step.slug)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("backend:wizard-steps"))
        self.step.refresh_from_db()
        for field, value in data.items():
            self.assertEqual(getattr(self.step, field), value)

    def test_invalid_slug_reopens_advanced_settings_and_preserves_values(self):
        response = self.view(
            self.request({"title": "Coordonnées", "slug": "avec espaces", "link_display": "Mes coordonnées"}),
            slug=self.step.slug,
        ).render()
        self.assertEqual(response.status_code, 200)
        self.assertIn("slug", response.context_data["form"].errors)
        self.assertContains(response, '<details class="paper-prepare-card" open>')
        self.step.refresh_from_db()
        self.assertEqual(self.step.slug, "user-update")
