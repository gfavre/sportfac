"""Settings for Docker-based development (Django 5 migration branch)."""
from .base import CELERYBEAT_SCHEDULE  # noqa: F401
from .base import *  # noqa: F403
from .base import env


DEBUG = True

SECRET_KEY = env("DJANGO_SECRET_KEY", default="docker-dev-secret-key-change-in-prod")

ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": env.db("OTHER_DB", default="postgres://sportfac:sportfac@db:5432/sportfac_dev"),  # noqa: F405
}
DATABASES["default"]["ENGINE"] = "django_tenants.postgresql_backend"

DATABASE_ROUTERS = ["django_tenants.routers.TenantSyncRouter"]

INSTALLED_APPS += [  # noqa: F405
    "django_extensions",
    "debug_toolbar",
    "corsheaders",
]

MIDDLEWARE = ["corsheaders.middleware.CorsMiddleware"] + MIDDLEWARE  # noqa: F405
MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]

CORS_ALLOW_ALL_ORIGINS = True
INTERNAL_IPS = ["127.0.0.1"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "sportfac@localhost"

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://redis:6379/0")
CELERY_ALWAYS_EAGER = False

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "sportfac-docker",
        "KEY_FUNCTION": "django_tenants.cache.make_key",
        "REVERSE_KEY_FUNCTION": "django_tenants.cache.reverse_key",
    },
}

SILENCED_SYSTEM_CHECKS = ["django_recaptcha.recaptcha_test_key_error"]
RECAPTCHA_PUBLIC_KEY = env("RECAPTCHA_PUBLIC_KEY", default="")
RECAPTCHA_PRIVATE_KEY = env("RECAPTCHA_PRIVATE_KEY", default="")

SESSION_COOKIE_NAME = "sportfac"
