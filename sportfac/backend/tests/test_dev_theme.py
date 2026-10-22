from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from sportfac.dev_theme import configure_development_theme


class DevelopmentThemeTests(SimpleTestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        for theme in ("montreux", "montreux_ski", "vevey"):
            (self.root / "sportfac" / "themes" / theme / "templates").mkdir(parents=True)
        self.config = {
            "SITE_ROOT": str(self.root / "sportfac"),
            "TEMPLATES": [{"DIRS": [], "OPTIONS": {"debug": True}}],
            "DATABASES": {"default": {"NAME": "local"}},
            "CACHES": {"default": {"BACKEND": "local-cache"}},
        }
        self.environment = patch.dict("os.environ", {}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_default_keeps_montreux_visuals_and_local_database(self):
        configure_development_theme(self.config)
        self.assertEqual(self.config["KEPCHUP_DEV_THEME"], "montreux")
        self.assertEqual(self.config["KEPCHUP_DIPLOMA_STYLE"], "montreux")
        self.assertEqual(self.config["DATABASES"], {"default": {"NAME": "local"}})
        self.assertEqual(self.config["TEMPLATES"][0]["OPTIONS"], {"debug": True})
        self.assertEqual(self.config["CACHES"]["default"], {"BACKEND": "local-cache"})
        self.assertEqual(self.config["CACHES"]["template_fragments"]["LOCATION"], "development-theme-montreux")

    def test_ignored_file_selects_templates_static_assets_and_branding(self):
        selection = self.root / ".dev-theme"
        for theme, style in (("montreux_ski", "montreux"), ("vevey", "classic")):
            with self.subTest(theme=theme):
                selection.write_text(theme + "\n")
                configure_development_theme(self.config)
                self.assertEqual(
                    self.config["TEMPLATES"][0]["DIRS"][0], str(self.root / "sportfac/themes" / theme / "templates")
                )
                self.assertEqual(
                    self.config["STATICFILES_DIRS"][0], str(self.root / "sportfac/themes" / theme / "static")
                )
                self.assertEqual(self.config["KEPCHUP_DIPLOMA_STYLE"], style)
        self.assertEqual(self.config["KEPCHUP_LOGO"], "img/logo.png")

    def test_environment_takes_precedence_over_file(self):
        (self.root / ".dev-theme").write_text("vevey")
        with patch.dict("os.environ", {"KEPCHUP_DEV_THEME": "montreux_ski"}):
            configure_development_theme(self.config)
        self.assertEqual(self.config["KEPCHUP_DEV_THEME"], "montreux_ski")

    def test_invalid_or_path_traversal_theme_fails_clearly(self):
        for theme in ("unknown", "../montreux", ""):
            with self.subTest(theme=theme), patch.dict("os.environ", {"KEPCHUP_DEV_THEME": theme}):
                with self.assertRaisesMessage(ImproperlyConfigured, "Unknown development theme"):
                    configure_development_theme(self.config)
