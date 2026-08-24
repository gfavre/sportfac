from django.test import Client
from django.urls import reverse

from profiles.tests.factories import DEFAULT_PASS
from profiles.tests.factories import FamilyUserFactory

from .base import BackendTestBase


class ServerHealthViewTest(BackendTestBase):
    def setUp(self):
        super().setUp()
        self.url = reverse("backend:health")

    def test_anonymous_denied(self):
        response = self.tenant_client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_manager_denied(self):
        # is_manager passes BackendMixin/KepchupStaffMixin elsewhere, but this view is
        # deliberately superuser-only.
        self.tenant_client.login(username=self.manager.email, password=DEFAULT_PASS)
        response = self.tenant_client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_superuser_sees_the_dashboard(self):
        superuser = FamilyUserFactory(is_superuser=True)
        self.tenant_client.login(username=superuser.email, password=DEFAULT_PASS)
        response = self.tenant_client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.context)
        self.assertIn("overall", response.context)


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
