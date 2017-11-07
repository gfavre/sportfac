# coding: utf-8
"""Development settings and globals."""

import os
from os.path import join, normpath

from base import *


########## DEBUG CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = True

SHARED_APPS += (
    'djcelery',
    'kombu.transport.django',
)

INSTALLED_APPS += (
    'django_extensions', # more commands
    'debug_toolbar', # debugging
    'djcelery',
    'kombu.transport.django',
)

# See: https://github.com/django-debug-toolbar/django-debug-toolbar#installation
INTERNAL_IPS = ('127.0.0.1',)

# See: https://github.com/django-debug-toolbar/django-debug-toolbar#installation
MIDDLEWARE_CLASSES = [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
] + MIDDLEWARE_CLASSES


ALLOWED_HOSTS = ('127.0.0.1', 'localhost', 'test.com', 'tenant.test.com', 'testserver')

########## END DEBUG CONFIGURATION


########## EMAIL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
EMAIL_FILE_PATH = '/tmp/app-messages' #  change this to a proper location

########## END EMAIL CONFIGURATION


########## DATABASE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES['default']['NAME'] = os.environ['DB_NAME']
DATABASES['default']['USER'] = os.environ['DB_USER']
DATABASES['default']['PASSWORD'] = os.environ['DB_PASSWORD']

########## END DATABASE CONFIGURATION


########## TOOLBAR CONFIGURATION
# See: https://github.com/django-debug-toolbar/django-debug-toolbar#installation


DEBUG_TOOLBAR_CONFIG ={
    'INTERCEPT_REDIRECTS': False,
    'SHOW_TEMPLATE_CONTEXT': True,
}
DEBUG_TOOLBAR_PANELS = [
    'debug_toolbar.panels.versions.VersionsPanel',
    'debug_toolbar.panels.timer.TimerPanel',
    'debug_toolbar.panels.settings.SettingsPanel',
    'debug_toolbar.panels.headers.HeadersPanel',
    'debug_toolbar.panels.request.RequestPanel',
    'debug_toolbar.panels.sql.SQLPanel',
    'debug_toolbar.panels.staticfiles.StaticFilesPanel',
    'debug_toolbar.panels.templates.TemplatesPanel',
    'debug_toolbar.panels.cache.CachePanel',
    'debug_toolbar.panels.signals.SignalsPanel',
    'debug_toolbar.panels.logging.LoggingPanel',
    'debug_toolbar.panels.redirects.RedirectsPanel',
]
########## END TOOLBAR CONFIGURATION




########### EMAIL:
DEFAULT_FROM_EMAIL = 'sportfac@localhost'
EMAIL_SUBJECT_PREFIX = '[%s] ' % SITE_NAME


############ Celery
# Asynchrnous tasks.
# See http://celery.readthedocs.org/en/latest/configuration.html
BROKER_URL = 'django://'
CELERY_RESULT_BACKEND = 'djcelery.backends.database:DatabaseBackend'



TEMPLATES[0]['DIRS'] = [
    normpath(join(SITE_ROOT, 'themes', 'vevey', 'templates')),
    normpath(join(SITE_ROOT, 'templates')),
]

STATICFILES_DIRS = (
    normpath(join(SITE_ROOT, 'themes', 'vevey', 'static')),
    normpath(join(SITE_ROOT, 'static')),
)

KEPCHUP_USE_ABSENCES = True
KEPCHUP_IMPORT_CHILDREN = True
KEPCHUP_PREFILL_YEARS_WITH_TEACHERS = True
KEPCHUP_SEND_PRESENCE_LIST = True
KEPCHUP_SEND_COPY_CONTACT_MAIL_TO_ADMIN = True
KEPCHUP_NO_PAYMENT = False
KEPCHUP_NO_TERMS = False
KEPCHUP_CHILD_SCHOOL = True
KEPCHUP_ADDITIONAL_INSTRUCTOR_EMAIL_DOCUMENTS = ['pdf/Lettre-Moniteurs-cours-automne-2017.pdf', 'pdf/GMS_2017-2018.pdf']
KEPCHUP_CALENDAR_DISPLAY_DATES = True
KEPCHUP_CALENDAR_DISPLAY_COURSE_NAMES = True
KEPCHUP_BIB_NUMBERS = True
KEPCHUP_FICHE_SALAIRE_MONTREUX = True
KEPCHUP_REGISTRATION_LEVELS = True
KEPCHUP_DISPLAY_CAR_NUMBER = True
KEPCHUP_DISPLAY_REGISTRATION_NOTE = True
KEPCHUP_REGISTRATION_LEVELS = True

CELERYBEAT_SCHEDULE['notify-absences'] = {
        'task': 'absences.tasks.notify_absences',
        'schedule': crontab(hour=19, minute=0),
}
