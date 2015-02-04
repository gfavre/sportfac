"""Development settings and globals."""

import os
from os.path import join, normpath

from base import *


########## DEBUG CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-debug
TEMPLATE_DEBUG = DEBUG

TEMPLATE_CONTEXT_PROCESSORS += (
  'django.core.context_processors.debug',
)

########## END DEBUG CONFIGURATION


########## EMAIL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
########## END EMAIL CONFIGURATION


########## DATABASE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.environ['DB_NAME'],
        'USER': os.environ['DB_USER'],
        'PASSWORD': os.environ['DB_PASSWORD'],
        'HOST': '',
        'PORT': '',
        'OPTIONS': {'autocommit': True,}
    }
}
########## END DATABASE CONFIGURATION


########## CACHE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
########## END CACHE CONFIGURATION


########## TOOLBAR CONFIGURATION
# See: https://github.com/django-debug-toolbar/django-debug-toolbar#installation
INSTALLED_APPS += (
    'django_extensions', # more commands
    'debug_toolbar', # debugging
    'kombu.transport.django', # celery broker using django db
)

# See: https://github.com/django-debug-toolbar/django-debug-toolbar#installation
INTERNAL_IPS = ('127.0.0.1',)

# See: https://github.com/django-debug-toolbar/django-debug-toolbar#installation
MIDDLEWARE_CLASSES += (
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)

DEBUG_TOOLBAR_CONFIG ={'INTERCEPT_REDIRECTS': False,
                       'SHOW_TEMPLATE_CONTEXT': True,
}

ALLOWED_HOSTS = ('127.0.0.1', 'localhost',)

########## END TOOLBAR CONFIGURATION

########### EMAIL:
DEFAULT_FROM_EMAIL = 'sportfac@localhost'
EMAIL_SUBJECT_PREFIX = '[%s] ' % SITE_NAME

########### MEDIA:
MEDIA_ROOT = normpath(join(dirname(SITE_ROOT), 'media'))

########### CKEDITOR
CKEDITOR_UPLOAD_PATH = MEDIA_ROOT

############ Celery
# Asynchrnous tasks. 
# See http://celery.readthedocs.org/en/latest/configuration.html
BROKER_URL = 'django://'
