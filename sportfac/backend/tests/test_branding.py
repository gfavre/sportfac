import base64
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from diplomas.services import diploma_logo
from django.conf import settings
from django.contrib.staticfiles import finders
from django.template.loader import get_template
from django.template.loader import render_to_string
from django.test import override_settings
from PIL import Image
from sekizai.context import SekizaiContext

from sportfac.context_processors import kepchup_context
from sportfac.utils import TenantTestCase


LOGO = "img/montreux-ssf-logo-dark-2026.png"
WHITE_LOGO = "img/montreux-ssf-logo-white-2026.png"


class BrandingTests(TenantTestCase):
    def test_shared_templates_use_deployment_logo_and_keep_legacy_default(self):
        for logo in (LOGO, "img/logo.png"):
            with self.subTest(logo=logo), override_settings(KEPCHUP_LOGO=logo):
                context = {
                    **kepchup_context(None),
                    **SekizaiContext().dicts[1],
                    "STATIC_URL": "/hiver/static/",
                }
                for template in ("backend/base-pdf.html", "registrations/invoice-part-heading.html"):
                    html = render_to_string(template, context)
                    self.assertIn(f"/hiver/static/{logo}", html)

    def test_both_seasonal_pdf_themes_use_current_deployment_static_url(self):
        for theme in ("montreux", "montreux_ski"):
            templates = deepcopy(settings.TEMPLATES)
            templates[0]["DIRS"].insert(0, str(Path(settings.SITE_ROOT) / "themes" / theme / "templates"))
            with self.subTest(theme=theme), override_settings(TEMPLATES=templates):
                html = render_to_string("mailer/base_pdf.html", {"STATIC_URL": "https://example.org/hiver/static/"})
                self.assertIn(f"https://example.org/hiver/static/{LOGO}", html)
                self.assertNotIn("https://ssfmontreux.ch/static/img/logo.png", html)
                footer = render_to_string("footer.html")
                self.assertIn(LOGO, footer)
                self.assertIn('width="240"', footer)
                self.assertNotIn("img/logo.png", footer)
                self.assertIn('{% include "ssf-favicons.html" %}', get_template("base.html").template.source)
                source = get_template("base.html").template.source
                self.assertIn("css/ssf-montreux-2026.css", source)
                self.assertNotIn("css/mvpready-admin-pom.css", source)
                self.assertNotIn("css/mvpready-admin-royal.css", source)
                self.assertIsNotNone(finders.find("css/ssf-montreux-2026.css"))

    def test_browser_icons_support_dark_backgrounds_and_resolve_manifest_assets(self):
        html = render_to_string("ssf-favicons.html")
        self.assertIn("(prefers-color-scheme: dark)", html)
        for name in ("icon-16.png", "icon-32.png", "icon-dark-32.png", "icon-180.png", "icon-192.png", "icon-512.png"):
            self.assertIsNotNone(finders.find("img/montreux-ssf-2026/" + name))

    def test_logo_assets_are_bounded_transparent_and_available_to_all_themes(self):
        for logo in (LOGO, WHITE_LOGO):
            with self.subTest(logo=logo), Image.open(finders.find(logo)) as image:
                self.assertEqual(image.width, 1200)
                self.assertLess(image.height, 400)
                self.assertIn("A", image.getbands())

    @override_settings(KEPCHUP_DIPLOMA_LOGO=LOGO)
    def test_new_diplomas_use_theme_logo_and_preserve_explicit_preference(self):
        with patch("diplomas.services.global_preferences_registry.manager") as manager:
            for preference, expected in (("", LOGO), (WHITE_LOGO, WHITE_LOGO)):
                with self.subTest(preference=preference):
                    manager.return_value.__getitem__.return_value = preference
                    encoded = diploma_logo().split(",", 1)[1]
                    self.assertEqual(base64.b64decode(encoded), Path(finders.find(expected)).read_bytes())
