"""Production settings and globals."""
from base import *


INSTALLED_APPS += (
    'gunicorn',  # web server
    'raven.contrib.django.raven_compat',  # sentry
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-subject-prefix
# EMAIL_SUBJECT_PREFIX = '[%s] ' % SITE_NAME


# See: https://docs.djangoproject.com/en/dev/ref/settings/#server-email
SERVER_EMAIL = env('SERVER_EMAIL')

DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL')

EMAIL_BACKEND = "anymail.backends.postmark.EmailBackend"
ANYMAIL = {
    # (exact settings here depend on your ESP...)
    "POSTMARK_SERVER_TOKEN": env('POSTMARK_TOKEN'),
}

MANAGERS = (
    ('Gregory Favre', 'greg@beyondthewall.ch'),
    ('Remo Aeschbach', 'remo.aeschbach@vd.educanet2.ch'),
)

########## END EMAIL CONFIGURATION


########## MEDIA CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = env('MEDIA_ROOT')

########## STATIC FILE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = env('STATIC_ROOT')

########## END STATIC FILE CONFIGURATION


########## DATABASE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES['default']['NAME'] = env('DB_NAME')
DATABASES['default']['USER'] = env('DB_USER')
DATABASES['default']['HOST'] = env('DB_HOST')
DATABASES['default']['PASSWORD'] = env('DB_PASSWORD')

########## END DATABASE CONFIGURATION



########## CACHE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': ['127.0.0.1:11211'],
        'KEY_PREFIX': env('CACHE_KEY_PREFIX'),
    }
}


########## END CACHE CONFIGURATION



# SECRET CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
# Note: This key only used for development and testing.
SECRET_KEY = env('SECRET_KEY')


########## END SECRET CONFIGURATION

########## SECURITY

SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_SECONDS = 3600
#SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

ALLOWED_HOSTS = env('ALLOWED_HOSTS').split(';')

############ Celery
# Asynchrnous tasks.
# See http://celery.readthedocs.org/en/latest/configuration.html
BROKER_URL = env('BROKER_URL')


########### Sentry
from os.path import dirname
import raven

RAVEN_CONFIG = {
    'dsn': 'https://3f862f015a1044e1962fd7a4e77ec5a2:5404be0237894b8fbfbf0122fd280280@sentry.io/1194911',
    # If you are using git, you can also automatically configure the
    # release based on the git info.
    'release': raven.fetch_git_sha(dirname(SITE_ROOT)),
}


RECAPTCHA_PUBLIC_KEY = env('RECAPTCHA_PUBLIC_KEY')
RECAPTCHA_PRIVATE_KEY = env('RECAPTCHA_PRIVATE_KEY')
RECAPTCHA_REQUIRED_SCORE = env('RECAPTCHA_REQUIRED_SCORE', default=0.85)


DATATRANS_API_URL = env.url('DATATRANS_API_URL', default='https://api.datatrans.com/')
DATATRANS_PAY_URL = env.url('DATATRANS_PAY_URL', default='https://pay.datatrans.com/')
