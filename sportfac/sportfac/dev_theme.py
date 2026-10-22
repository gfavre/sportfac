"""Local visual previews without importing another deployment's infrastructure settings."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured


def configure_development_theme(config):
    root = Path(config["SITE_ROOT"])
    selection = root.parent / ".dev-theme"
    theme = os.environ.get("KEPCHUP_DEV_THEME")
    if theme is None:
        theme = selection.read_text().strip() if selection.exists() else "montreux"
    themes = root / "themes"
    available = {path.name for path in themes.iterdir() if (path / "templates").is_dir()}
    if theme not in available:
        raise ImproperlyConfigured(
            f"Unknown development theme {theme!r}. Choose one of: {', '.join(sorted(available))}"
        )
    config["TEMPLATES"][0]["DIRS"] = [str(themes / theme / "templates"), str(root / "templates")]
    config["STATICFILES_DIRS"] = (str(themes / theme / "static"), str(root / "static"))
    ssf = theme in ("montreux", "montreux_ski")
    config["KEPCHUP_LOGO"] = "img/montreux-ssf-logo-dark-2026.png" if ssf else "img/logo.png"
    config["KEPCHUP_DIPLOMA_LOGO"] = config["KEPCHUP_LOGO"]
    config["KEPCHUP_DIPLOMA_STYLE"] = "montreux" if ssf else "classic"
    config["KEPCHUP_DEV_THEME"] = theme
    # Footer fragments must not carry the previous theme's markup across restarts.
    config.setdefault("CACHES", {})["template_fragments"] = {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": f"development-theme-{theme}",
    }
