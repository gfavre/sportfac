"""Production settings and globals."""
import logging

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from .base import *  # noqa: F403


INSTALLED_APPS += ("gunicorn",)  # noqa: F405


# EMAIL CONFIGURATION

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-subject-prefix
# EMAIL_SUBJECT_PREFIX = '[%s] ' % SITE_NAME

# See: https://docs.djangoproject.com/en/dev/ref/settings/#server-email
SERVER_EMAIL = env("SERVER_EMAIL")  # noqa: F405
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL")  # noqa: F405
EMAIL_BACKEND = "anymail.backends.postmark.EmailBackend"
ANYMAIL = {
    "POSTMARK_SERVER_TOKEN": env("POSTMARK_TOKEN"),  # noqa: F405
}
MANAGERS = (("Gregory Favre", "greg@beyondthewall.ch"),)
# EMAIL CONFIGURATION


# MEDIA CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = env("MEDIA_ROOT")  # noqa: F405

# STATIC FILE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = env("STATIC_ROOT")  # noqa: F405


# DATABASE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES["default"]["NAME"] = env("DB_NAME")  # noqa: F405
DATABASES["default"]["USER"] = env("DB_USER")  # noqa: F405
DATABASES["default"]["HOST"] = env("DB_HOST")  # noqa: F405
DATABASES["default"]["PASSWORD"] = env("DB_PASSWORD")  # noqa: F405
# Without this, Django opens/closes a fresh Postgres connection on every request (the
# default, CONN_MAX_AGE=0) - each gunicorn thread pays full TCP+auth handshake cost per
# request, and a burst of concurrent requests means a burst of concurrent new connections
# on the Postgres side too. django_tenants is safe to reuse connections across requests:
# its middleware runs `SET search_path` at the start of every request regardless of
# whether the underlying connection is new or reused, so tenant isolation isn't affected.
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)  # noqa: F405


# CACHE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("BROKER_URL"),  # noqa: F405
        "KEY_PREFIX": env("CACHE_KEY_PREFIX"),  # noqa: F405
        "KEY_FUNCTION": "django_tenants.cache.make_key",
        "REVERSE_KEY_FUNCTION": "django_tenants.cache.reverse_key",
    },
    "sessions": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("BROKER_URL"),  # noqa: F405
        "KEY_PREFIX": env("CACHE_KEY_PREFIX") + "_sessions",  # noqa: F405
    },
    # dynamic_preferences reads/writes to whichever alias DYNAMIC_PREFERENCES["CACHE_NAME"]
    # names (set below) - its own preference model already connects a global post_save
    # signal (dynamic_preferences/models.py: invalidate_cache) that re-primes this cache
    # with the fresh value on every write, tenant- or globally-scoped, so a TTL here is not
    # a correctness backstop, just wasted DB round trips every time it expires under load.
    # 24h rather than never-expire: a sane guard rail against anything that changed a
    # preference outside that signal (a raw .update() on the model, a direct DB edit) -
    # this bounds the worst case at "stale for up to a day" instead of "stale forever"
    # without reintroducing the every-5-minutes cost the default TTL had. It would NOT be
    # safe to apply the same TIMEOUT to "default" above, which also holds cache entries
    # (e.g. api/views/activities_views.py's CourseViewSet.retrieve) that haven't been
    # audited the same way and still rely on the 5-minute expiry to self-heal.
    "preferences": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("BROKER_URL"),  # noqa: F405
        "KEY_PREFIX": env("CACHE_KEY_PREFIX") + "_preferences",  # noqa: F405
        "KEY_FUNCTION": "django_tenants.cache.make_key",
        "REVERSE_KEY_FUNCTION": "django_tenants.cache.reverse_key",
        "TIMEOUT": 60 * 60 * 24,
    },
}

DYNAMIC_PREFERENCES["CACHE_NAME"] = "preferences"  # noqa: F405


# SECRET CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env("SECRET_KEY")  # noqa: F405


# SECURITY
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_SECONDS = 3600
# SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "sessions"

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")  # noqa: F405

# Celery
# Asynchrnous tasks.
# See http://celery.readthedocs.org/en/latest/configuration.html
BROKER_URL = env("BROKER_URL")  # noqa: F405
CELERY_RESULT_BACKEND = env("RESULT_URL", default=env("BROKER_URL"))  # noqa: F405
CELERY_RESULT_EXPIRES = 60 * 15  # 15 minutes
CELERY_PREFIX = env("CELERY_PREFIX", default="sportfac")  # noqa: F405
CELERY_TASK_DEFAULT_QUEUE = CELERY_PREFIX + "_default"  # noqa: F405


# Sentry
def before_send(event, hint):
    event["extra"] = event.get("extra", {})

    # Add only the settings that are safe to expose
    event["extra"]["django_settings"] = env("DJANGO_SETTINGS_MODULE")  # noqa: F405
    event["extra"]["db_name"] = env("DB_NAME")  # noqa: F405
    return event


SENTRY_DSN = env(  # noqa: F405
    "SENTRY_DSN", default="https://3f862f015a1044e1962fd7a4e77ec5a2:5404be0237894b8fbfbf0122fd280280@sentry.io/1194911"
)
SENTRY_LOG_LEVEL = env.int("DJANGO_SENTRY_LOG_LEVEL", logging.INFO)  # noqa: F405

sentry_logging = LoggingIntegration(
    level=SENTRY_LOG_LEVEL,  # Capture info and above as breadcrumbs
    event_level=logging.ERROR,  # Send errors as events
)
integrations = [sentry_logging, DjangoIntegration(), CeleryIntegration()]

sentry_sdk.init(
    dsn=SENTRY_DSN,
    integrations=integrations,
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production,
    traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.0),  # noqa: F405
    send_default_pii=True,
    before_send=before_send,
)


RECAPTCHA_PUBLIC_KEY = env("RECAPTCHA_PUBLIC_KEY")  # noqa: F405
RECAPTCHA_PRIVATE_KEY = env("RECAPTCHA_PRIVATE_KEY")  # noqa: F405
RECAPTCHA_REQUIRED_SCORE = env("RECAPTCHA_REQUIRED_SCORE", default=0.85)  # noqa: F405


DATATRANS_API_URL = env.url("DATATRANS_API_URL", default="https://api.datatrans.com/")  # noqa: F405
DATATRANS_PAY_URL = env.url("DATATRANS_PAY_URL", default="https://pay.datatrans.com/")  # noqa: F405


DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  # 50 MB
# `DATA_UPLOAD_MAX_MEMORY_SIZE` is a top-level Django setting (above), not a DRF
# REST_FRAMEWORK key - a `REST_FRAMEWORK = {...}` reassignment used to sit here too,
# silently replacing (not merging with) base.py's dict and dropping the ORJSON renderer,
# pagination, filter backends and permission classes in every production deployment.


LOGGING["root"] = {  # noqa: F405
    "handlers": ["console"],
    "level": "DEBUG",
}
