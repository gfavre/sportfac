"""Production settings and globals."""


from os import environ

from base import *

# Normally you should not import ANYTHING from Django directly
# into your settings, but ImproperlyConfigured is an exception.
from django.core.exceptions import ImproperlyConfigured


def get_env_setting(setting):
    """ Get the environment setting or return exception """
    try:
        return environ[setting]
    except KeyError:
        error_msg = "Set the %s env variable" % setting
        raise ImproperlyConfigured(error_msg)

INSTALLED_APPS += ('gunicorn', # web server
                   'raven.contrib.django.raven_compat', # sentry
                   )

########## EMAIL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-host
EMAIL_HOST = environ.get('EMAIL_HOST', '')

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-host-password
EMAIL_HOST_PASSWORD = environ.get('EMAIL_HOST_PASSWORD', '')

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-host-user
EMAIL_HOST_USER = environ.get('EMAIL_HOST_USER', '')

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-subject-prefix
EMAIL_SUBJECT_PREFIX = '[%s] ' % SITE_NAME

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-use-tls
EMAIL_USE_TLS = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#server-email
SERVER_EMAIL = get_env_setting('SERVER_EMAIL')

DEFAULT_FROM_EMAIL = get_env_setting('DEFAULT_FROM_EMAIL')


MANAGERS = (
    ('Gregory Favre', 'gregory.favre@gmail.com'),
    ('Remo Aeschbach', 'remo.aeschbach@vd.educanet2.ch'),
)
########## END EMAIL CONFIGURATION


########## MEDIA CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = get_env_setting('MEDIA_ROOT')
CKEDITOR_UPLOAD_PATH = MEDIA_ROOT


########## STATIC FILE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = get_env_setting('STATIC_ROOT')

########## END STATIC FILE CONFIGURATION



########## DATABASE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': environ.get('DB_NAME'),
        'USER': environ.get('DB_USER'),
        'PASSWORD': environ.get('DB_PASSWORD'),
        'HOST': '',
        'PORT': '',
        'OPTIONS': {'autocommit': True,}
    }
}
########## END DATABASE CONFIGURATION



########## CACHE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#caches
{
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
########## END CACHE CONFIGURATION


########## SECRET CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = get_env_setting('SECRET_KEY')
########## END SECRET CONFIGURATION

ALLOWED_HOSTS = get_env_setting('ALLOWED_HOSTS').split(';')

############ Celery
# Asynchrnous tasks. 
# See http://celery.readthedocs.org/en/latest/configuration.html
BROKER_URL = get_env_setting('BROKER_URL')


########### Sentry
# Définissez la valeur du DSN : 
RAVEN_CONFIG = {
    'dsn': 'https://7490d3622e2140c6beb983ede7fd6c88:ebffe9eb0ff249da95e412296e1dad4d@beyond-sentry.herokuapp.com/2',
}

# Ajoutez raven à la liste des applications installées
INSTALLED_APPS = INSTALLED_APPS + (
    # ...
    'raven.contrib.django.raven_compat',
)