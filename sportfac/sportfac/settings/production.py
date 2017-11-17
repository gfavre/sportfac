"""Production settings and globals."""
from base import *


INSTALLED_APPS += ('gunicorn', # web server
                   'raven.contrib.django.raven_compat', # sentry
                   )

########## EMAIL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-host
EMAIL_HOST = env('EMAIL_HOST', default='')

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-host-password
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', '')

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-host-user
EMAIL_HOST_USER = env('EMAIL_HOST_USER', '')

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-subject-prefix
EMAIL_SUBJECT_PREFIX = '[%s] ' % SITE_NAME

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-use-tls
EMAIL_USE_TLS = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#server-email
SERVER_EMAIL = env('SERVER_EMAIL')

DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL')


MANAGERS = (
    ('Gregory Favre', 'gregory.favre@gmail.com'),
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
DATABASES['default']['PASSWORD'] = env('DB_PASSWORD')

########## END DATABASE CONFIGURATION



########## CACHE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': 'unix:' + env('MEMCACHED_SOCKET'),
    }
}


########## END CACHE CONFIGURATION



# SECRET CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
# Note: This key only used for development and testing.
SECRET_KEY = env('DJANGO_SECRET_KEY')


########## END SECRET CONFIGURATION

########## SECURITY

SECURE_SSL_REDIRECT = True
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
RAVEN_CONFIG = {
    'dsn': 'https://7490d3622e2140c6beb983ede7fd6c88:ebffe9eb0ff249da95e412296e1dad4d@beyond-sentry.herokuapp.com/2',
}
