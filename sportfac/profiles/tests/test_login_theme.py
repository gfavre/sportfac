from copy import deepcopy
from pathlib import Path

from django.conf import settings
from django.test import override_settings
from django.urls import reverse

from sportfac.utils import TenantTestCase


class WinterLoginTests(TenantTestCase):
    def test_anonymous_login_renders_with_winter_navigation(self):
        templates = deepcopy(settings.TEMPLATES)
        templates[0]["DIRS"].insert(0, str(Path(settings.SITE_ROOT) / "themes" / "montreux_ski" / "templates"))
        with override_settings(TEMPLATES=templates, KEPCHUP_USE_SSO=False):
            response = self.tenant_client.get(reverse("profiles:auth_login"), {"next": "/"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("profiles:authenticated-home"))
        self.assertContains(response, 'name="username"')
