"""Production settings and globals."""
import logging

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from .base import *  # noqa: F403


INSTALLED_APPS += ("gunicorn",)  # noqa: F405
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [  # noqa: F405
    "rest_framework.renderers.JSONRenderer",
    "rest_framework_datatables.renderers.DatatablesRenderer",
]


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


# CACHE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.memcached.PyMemcacheCache",
        "LOCATION": ["127.0.0.1:11211"],
        "KEY_PREFIX": env("CACHE_KEY_PREFIX"),  # noqa: F405
    }
}


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
REST_FRAMEWORK = {
    "DATA_UPLOAD_MAX_MEMORY_SIZE": 50 * 1024 * 1024,  # 50 MB
}
