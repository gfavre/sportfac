from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch

from django.conf import settings
from django.template.loader import render_to_string
from django.test import Client
from django.test import RequestFactory
from django.test import SimpleTestCase
from django.test import override_settings
from django.urls import reverse
from sekizai.context import SekizaiContext

from backend.views.health_views import ServerHealthView
from profiles.tests.factories import DEFAULT_PASS
from profiles.tests.factories import FamilyUserFactory

from .base import BackendTestBase


class ServerHealthViewTest(BackendTestBase):
    def setUp(self):
        super().setUp()
        self.url = reverse("backend:health")
        patcher = patch("backend.views.health_views.run_service_checks", return_value={})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_anonymous_denied(self):
        for url in (self.url, reverse("health"), "/health/"):
            response = self.tenant_client.get(url)
            self.assertEqual(response.status_code, 302)

    def test_manager_denied(self):
        # is_manager passes BackendMixin/KepchupStaffMixin elsewhere, but this view is
        # deliberately superuser-only.
        self.tenant_client.login(username=self.manager.email, password=DEFAULT_PASS)
        for url in (self.url, reverse("health"), "/health/"):
            response = self.tenant_client.get(url)
            self.assertEqual(response.status_code, 302)

    def test_superuser_sees_the_dashboard(self):
        superuser = FamilyUserFactory(is_superuser=True)
        self.tenant_client.login(username=superuser.email, password=DEFAULT_PASS)
        for url in (self.url, reverse("health"), "/health/"):
            response = self.tenant_client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertIn("results", response.context)
            self.assertIn("overall", response.context)
            self.assertIn("no-store", response["Cache-Control"])


class PrivateHealthAccessTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        templates = deepcopy(settings.TEMPLATES)
        templates[0]["OPTIONS"]["context_processors"] = []
        templates[0]["OPTIONS"]["loaders"] = [
            (
                "django.template.loaders.locmem.Loader",
                {
                    "backend/base.html": "{% block content %}{% endblock %}",
                    "impersonation.html": "",
                    "main-title.html": "",
                },
            ),
            "django.template.loaders.filesystem.Loader",
            "django.template.loaders.app_directories.Loader",
        ]
        config = override_settings(TEMPLATES=templates)
        config.enable()
        self.addCleanup(config.disable)

    @patch("backend.views.health_views.run_service_checks", return_value={})
    @patch("backend.views.health_views.run_checks", return_value={"database": {"level": "ok", "detail": {}}})
    def test_superuser_response_and_no_cache_on_both_routes(self, infrastructure, services):
        for url in (reverse("health"), reverse("backend:health"), "/health/"):
            request = self.factory.get(url)
            request.user = SimpleNamespace(is_authenticated=True, is_active=True, is_superuser=True)
            request.tenant = SimpleNamespace(schema_name="period_test")
            response = ServerHealthView.as_view()(request)
            self.assertEqual(response.status_code, 200)
            self.assertIn("no-store", response["Cache-Control"])
            self.assertEqual(response.context_data["schema_name"], "period_test")
        self.assertEqual(services.call_count, 3)

    @patch("backend.views.health_views.run_service_checks")
    @patch("backend.views.health_views.run_checks")
    def test_all_non_superusers_denied_before_checks(self, infrastructure, services):
        for role in (
            {"is_authenticated": False},
            {"is_staff": True},
            {"is_manager": True},
            {"is_superuser": True, "is_active": False},
            {},
        ):
            user = {"is_authenticated": True, "is_active": True, "is_superuser": False, **role}
            request = self.factory.get(reverse("health"))
            request.user = SimpleNamespace(**user)
            response = ServerHealthView.as_view()(request)
            self.assertEqual(response.status_code, 302)
        infrastructure.assert_not_called()
        services.assert_not_called()

    def test_menu_link_is_superuser_only_in_all_variants(self):
        from pathlib import Path

        from django.conf import settings
        from django.template import engines

        paths = [Path(settings.SITE_ROOT) / "templates/navbar.html"]
        paths += list((Path(settings.SITE_ROOT) / "themes").glob("*/templates/navbar.html"))
        for path in paths:
            with self.subTest(template=path):
                template = engines["django"].from_string(path.read_text())
                for superuser in (False, True):
                    user = SimpleNamespace(is_authenticated=True, is_superuser=superuser, is_staff=True)
                    html = template.template.render(SekizaiContext({"user": user}))
                    self.assertEqual(f'href="{reverse("health")}"' in html, superuser)
                    if superuser:
                        self.assertLess(html.index(reverse("admin:index")), html.index(reverse("health")))

    def test_dashboard_shows_partial_disabled_and_failed_checks(self):
        html = render_to_string(
            "backend/health.html",
            {
                "overall": "critical",
                "overall_label": "Critical",
                "results": [
                    {
                        "label": "PostFinance",
                        "level": "critical",
                        "level_label": "Critical",
                        "detail": [{"label": "HTTP", "value": "401"}],
                    },
                    {
                        "label": "SSO",
                        "level": "warning",
                        "level_label": "Warning",
                        "detail": [{"label": "Note", "value": "Credentials not tested"}],
                    },
                    {"label": "Datatrans", "level": "disabled", "level_label": "Not enabled"},
                ],
            },
        )
        self.assertIn("PostFinance", html)
        self.assertIn("401", html)
        self.assertIn("Credentials not tested", html)
        self.assertIn("Not enabled", html)

    @patch("sportfac.views.run_checks", return_value={"database": {"level": "ok", "detail": {"error": "private"}}})
    @patch("backend.views.health_views.run_service_checks")
    def test_public_probe_does_not_run_external_checks(self, services, infrastructure):
        from sportfac.views import health_check

        response = health_check(self.factory.get("/_health-kc/"))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"private", response.content)
        services.assert_not_called()


class PublicHealthCheckTest(BackendTestBase):
    def test_reachable_without_login(self):
        response = Client().get("/_health-kc/")
        self.assertIn(response.status_code, (200, 503))

    def test_body_never_leaks_raw_numbers(self):
        response = Client().get("/_health-kc/")
        data = response.json()
        self.assertEqual(set(data.keys()), {"status", "checks"})
        for level in data["checks"].values():
            self.assertIn(level, ("ok", "warning", "critical"))
