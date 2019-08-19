# -*- coding:utf-8 -*-
"""Common settings and globals."""
from os.path import abspath, basename, dirname, join, normpath
from sys import path

# Normally you should not import ANYTHING from Django directly
# into your settings, but ImproperlyConfigured is an exception.
from django.core.exceptions import ImproperlyConfigured

from celery.schedules import crontab
import environ

env = environ.Env()

ugettext = lambda s: s

########## PATH CONFIGURATION
# Absolute filesystem path to the Django project directory:
DJANGO_ROOT = dirname(dirname(abspath(__file__)))

# Absolute filesystem path to the top-level project folder:
SITE_ROOT = dirname(DJANGO_ROOT)

# Site name:
SITE_NAME = basename(DJANGO_ROOT)

# Add our project to our pythonpath, this way we don't need to type our project
# name in our dotted import paths:
path.append(DJANGO_ROOT)
########## END PATH CONFIGURATION


########## DEBUG CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = False

########## END DEBUG CONFIGURATION


########## MANAGER CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = (
    ('Gregory Favre', 'gregory.favre@gmail.com'),
)


# See: https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS
########## END MANAGER CONFIGURATION


########## DATABASE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',
        'NAME': '',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

# Multitenancy configuration
DATABASE_ROUTERS = (
    'django_tenants.routers.TenantSyncRouter',
)
DEFAULT_TENANT_NAME = 'current'

VERSION_SESSION_NAME = 'period'
TENANT_MODEL = "backend.YearTenant" # app.Model
TENANT_DOMAIN_MODEL = "backend.Domain" # app.Model

########## END DATABASE CONFIGURATION


########## GENERAL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#time-zone
TIME_ZONE = 'Europe/Zurich'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = 'fr-CH'
LANGUAGES = (('fr', 'French'),)

# see https://docs.djangoproject.com/en/dev/ref/settings/#locale-paths
LOCALE_PATHS = (
    normpath(join(SITE_ROOT, 'locale')),
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-l10n
USE_L10N = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True
########## END GENERAL CONFIGURATION


########## MEDIA CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = normpath(join(SITE_ROOT, 'media'))

# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = '/media/'
########## END MEDIA CONFIGURATION


########## STATIC FILE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = normpath(join(SITE_ROOT, 'assets'))

# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = '/static/'

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = (
    normpath(join(SITE_ROOT, 'static')),
)

STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'django.contrib.staticfiles.finders.FileSystemFinder',
)


########## END STATIC FILE CONFIGURATION


########## END SECRET CONFIGURATION


########## FIXTURE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-FIXTURE_DIRS
FIXTURE_DIRS = (
    #normpath(join(SITE_ROOT, 'fixtures')),
)
########## END FIXTURE CONFIGURATION


########## TEMPLATE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            normpath(join(SITE_ROOT, 'templates')),
        ],
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.request',

                'sportfac.context_processors.wizard_context',
                'sportfac.context_processors.registration_opened_context',
                'sportfac.context_processors.activities_context',
                'sportfac.context_processors.tenants_context',
                'sportfac.context_processors.kepchup_context',
                'sportfac.context_processors.dynamic_preferences_context',

                'sekizai.context_processors.sekizai',
            ],
            'loaders': [
                'dbtemplates.loader.Loader',
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ]
        },
    },
]

########## END TEMPLATE CONFIGURATION


########## MIDDLEWARE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#middleware-classes
MIDDLEWARE_CLASSES = [
    # Default Django middleware.
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.contrib.sites.middleware.CurrentSiteMiddleware',
    'django.middleware.security.SecurityMiddleware',

    'sportfac.middleware.VersionMiddleware',
    'sportfac.middleware.RegistrationOpenedMiddleware',
    # asynchronous messages
    'async_messages.middleware.AsyncMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
]
########## END MIDDLEWARE CONFIGURATION


########## URL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = '%s.urls' % SITE_NAME
########## END URL CONFIGURATION


########## APP CONFIGURATION

SHARED_APPS = (
    'django_tenants',
    'backend',  # you must list the app where your tenant model resides in

    # Default Django apps:
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    'django.contrib.sites',
    'django.contrib.flatpages',
    'django.contrib.sitemaps',

    # third party apps

    'ckeditor',  # wysiwyg editor
    'ckeditor_uploader',
    'dbtemplates',  # store templates in db (used by mailer module)
    'django_select2',  # select2 form input
    'dynamic_preferences',
    'floppyforms',  # better forms
    'import_export',
    'mathfilters',
    'phonenumber_field',
    'registration',  # user registration
    'rest_framework',  # REST API
    'sekizai',  # add_to_block template tag

    # local apps
    'api',
    'contact',
    'mailer',
    'profiles',

    # last apps
    'django.contrib.admin',
)


TENANT_APPS = (
    'absences',
    'activities',
    'registrations',
    'schools',
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]
########## END APP CONFIGURATION


########## LOGGING CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#logging
# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}
########## END LOGGING CONFIGURATION

TEST_RUNNER = 'django.test.runner.DiscoverRunner'

########## WSGI CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = 'wsgi.application'
########## END WSGI CONFIGURATION


##########  MESSAGE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/contrib/messages/

from django.contrib.messages import constants as messages
MESSAGE_TAGS = {
    messages.DEBUG: 'alert-info',
    messages.INFO: 'alert-info',
    messages.SUCCESS: 'alert-success',
    messages.WARNING: 'alert-warning',
    messages.ERROR: 'alert-danger'
}


########## END WSGI CONFIGURATION



########## REST FRAMEWORK CONFIGURATION

REST_FRAMEWORK = {
    # Use hyperlinked styles by default.
    # Only used if the `serializer_class` attribute is not set on a view.
    'DEFAULT_MODEL_SERIALIZER_CLASS':
        'rest_framework.serializers.HyperlinkedModelSerializer',

    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly'
    ]
}

########## END REST FRAMEWORK CONFIGURATION

########## DYNAMIC PREFERENCES CONFIGURATION
# see http://django-dynamic-preferences.readthedocs.io

DYNAMIC_PREFERENCES = {

    # a python attribute that will be added to model instances with preferences
    # override this if the default collide with one of your models attributes/fields
    'MANAGER_ATTRIBUTE': 'preferences',

    # The python module in which registered preferences will be searched within each app
    'REGISTRY_MODULE': 'dynamic_preferences_registry',

    # Allow quick editing of preferences directly in admin list view
    # WARNING: enabling this feature can cause data corruption if multiple users
    # use the same list view at the same time, see https://code.djangoproject.com/ticket/11313
    'ADMIN_ENABLE_CHANGELIST_FORM': False,

    # Should we enable the admin module for user preferences ?
    'ENABLE_USER_PREFERENCES': False,

    # Customize how you can access preferences from managers. The default is to
    # separate sections and keys with two underscores. This is probably not a settings you'll
    # want to change, but it's here just in case
    'SECTION_KEY_SEPARATOR': '__',

    # Use this to disable caching of preference. This can be useful to debug things
    'ENABLE_CACHE': True,

    # Use this to disable checking preferences names. This can be useful to debug things
    'VALIDATE_NAMES': True,
}

########## END DYNAMIC PREFERENCES CONFIGURATION


DATE_INPUT_FORMATS = [
    '%d.%m.%Y',
    '%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', # '2006-10-25', '10/25/2006', '10/25/06'
    '%b %d %Y', '%b %d, %Y',            # 'Oct 25 2006', 'Oct 25, 2006'
    '%d %b %Y', '%d %b, %Y',            # '25 Oct 2006', '25 Oct, 2006'
    '%B %d %Y', '%B %d, %Y',            # 'October 25 2006', 'October 25, 2006'
    '%d %B %Y', '%d %B, %Y',            # '25 October 2006', '25 October, 2006'
]


########## USER and REGISTRATION
AUTH_USER_MODEL = 'profiles.FamilyUser'
REGISTRATION_OPEN = True
LOGIN_URL = '/account/login/'
LOGOUT_URL = '/account/logout/'

########## END USER and REGISTRAION


########### GRAPPELLI CONFIG
GRAPPELLI_ADMIN_TITLE = "Administration du sport scolaire facultatif"
########## END GRAPPELLI CONFIG


########### PIPELINE CONFIG
#STATICFILES_STORAGE = 'pipeline.storage.PipelineCachedStorage'

########## END PIPELINE CONFIG


########### CKEDITOR
CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'Custom',
        'toolbar_Custom': [
            ['Source', '-', 'Print'],  ['Undo', 'Redo'], ['Bold', 'Italic', 'Subscript', 'Superscript'],
            ['Format', 'TextColor'], ['NumberedList', 'BulletedList'],
            ['Link', 'Unlink', 'Anchor'],
            '/',
            ['Image', 'Table', 'HorizontalRule'],
            [#'Emojione',
             'SpecialChar']

        ],
        'extraPlugins': ','.join(['emojione']),
    }
}

CKEDITOR_UPLOAD_PATH = 'uploads/'
CKEDITOR_BROWSE_SHOW_DIRS = True
CKEDITOR_IMAGE_BACKEND = "pillow"
X_FRAME_OPTIONS = 'SAMEORIGIN'

############# Select2
AUTO_RENDER_SELECT2_STATICS = False


############ Celery
# Asynchrnous tasks.
# See http://celery.readthedocs.org/en/latest/configuration.html
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

CELERYBEAT_SCHEDULE = {
    'update-periods': {
        'task': 'backend.tasks.update_current_tenant',
        'schedule': crontab(hour=0, minute=0),
    },
}

PHANTOMJS = env('PHANTOMJS', default='/usr/local/bin/phantomjs')
PHANTOMJS_RASTERIZE_PORTRAIT = join(dirname(SITE_ROOT), 'bin', 'rasterize-portrait.js')
PHANTOMJS_RASTERIZE_LANDSCAPE = join(dirname(SITE_ROOT), 'bin', 'rasterize-landscape.js')

DBTEMPLATES_USE_CODEMIRROR = True


############# Phonenumbers
PHONENUMBER_DEFAULT_REGION = 'CH'

################################################################################
# Kepchup Options
################################################################################

# general
#########################################

# Use a splash page rather than home. Use by Montreux who has 2 kepchup instances
KEPCHUP_SPLASH_PAGE = False

# no terms and conditions
KEPCHUP_NO_TERMS = False
# not used for the moment. TODO: do something with that for Coppet-primaire
KEPCHUP_DISPLAY_PARENT_CITY = False
# Use other step names during registration.  # TODO: have a dict of names here...
KEPCHUP_ALTERNATIVE_STEPS_NAMING = False
# Activate absence module
KEPCHUP_USE_ABSENCES = False
# By default, absences are connected to courses.
KEPCHUP_ABSENCES_RELATE_TO_ACTIVITIES = False
# Activate montreux specific feature to handle instructors pay slips
KEPCHUP_FICHE_SALAIRE_MONTREUX = False

KEPCHUP_REGISTRATION_LEVELS = False
KEPCHUP_DISPLAY_CAR_NUMBER = False
KEPCHUP_DISPLAY_REGISTRATION_NOTE = False
KEPCHUP_LEVELS_PREFIXER = {}

# Payment
#########################################
# if true, disable invoicing system
KEPCHUP_NO_PAYMENT = False
KEPCHUP_DISPLAY_FREE_WHEN_PRICE_IS_0 = False


# Registration steps
#########################################
KEPCHUP_ALTERNATIVE_ABOUT_LABEL = None
KEPCHUP_ALTERNATIVE_CHILDREN_LABEL = None
KEPCHUP_ALTERNATIVE_ACTIVITIES_LABEL = None
KEPCHUP_ALTERNATIVE_CONFIRM_LABEL = None
KEPCHUP_ALTERNATIVE_BILLING_LABEL = None



# Children
#########################################

# Children have a bib number (n° dossard)
KEPCHUP_BIB_NUMBERS = False
# Ask for school of the child
KEPCHUP_CHILD_SCHOOL = False
# these fields are not editable by parent. Makes sense with KEPCHUP_IMPORT_CHILDREN
KEPCHUP_CHILDREN_UNEDITABLE_FIELDS = []
# display nb of sessions on public pages. Disabled for Nyon-Prangins
KEPCHUP_DISPLAY_NUMBER_OF_SESSIONS = True
# make emergency number mandatory on children
KEPCHUP_EMERGENCY_NUMBER_MANDATORY = True
# Import children lists from lagapeo
KEPCHUP_IMPORT_CHILDREN = False
# School years are related to main teacher of the child
KEPCHUP_PREFILL_YEARS_WITH_TEACHERS = False
# Ask for school building. Manage imports by building
KEPCHUP_USE_BUILDINGS = False


# Activities
#########################################

# In Coppet-Rojalets children can register Poterie at different periods of the year.
KEPCHUP_ACTIVITIES_CAN_REGISTER_SAME_ACTIVITY_TWICE = False
KEPCHUP_CALENDAR_DISPLAY_DATES = True
KEPCHUP_CALENDAR_DISPLAY_COURSE_NAMES = False

# Email
#########################################

# Send presence list to instructors
KEPCHUP_SEND_PRESENCE_LIST = True
KEPCHUP_SEND_COPY_CONTACT_MAIL_TO_ADMIN = True
KEPCHUP_ADDITIONAL_INSTRUCTOR_EMAIL_DOCUMENTS = []
# If true: do not send E_SSF_decompte_heures_%s_%s.pdf to instructors
KEPCHUP_NO_SSF = False
