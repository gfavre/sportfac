"""Common settings and globals."""

import os
from os.path import abspath, basename, dirname, join, normpath
from sys import path
from datetime import datetime
from pytz import timezone

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
VERSION_COOKIE_NAME = 'KepchupYear'
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

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'django.contrib.staticfiles.finders.FileSystemFinder',
)


########## END STATIC FILE CONFIGURATION


########## SECRET CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
# Note: This key only used for development and testing.
SECRET_KEY = os.environ['SECRET_KEY']
########## END SECRET CONFIGURATION


########## FIXTURE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-FIXTURE_DIRS
FIXTURE_DIRS = (
    normpath(join(SITE_ROOT, 'fixtures')),
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
                
                'constance.context_processors.config',
                
                'sportfac.context_processors.wizard_context',
                'sportfac.context_processors.registration_opened_context',
                'sportfac.context_processors.activities_context',
                'sportfac.context_processors.tenants_context',
                'sekizai.context_processors.sekizai',
            ],
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'dbtemplates.loader.Loader',
                'django.template.loaders.app_directories.Loader',
            ]
        },
    },
]

########## END TEMPLATE CONFIGURATION


########## MIDDLEWARE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#middleware-classes
MIDDLEWARE_CLASSES = (
    'sportfac.middleware.VersionMiddleware',

    # Default Django middleware.
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.contrib.sites.middleware.CurrentSiteMiddleware',
    'django.middleware.security.SecurityMiddleware',
    
    'sportfac.middleware.RegistrationOpenedMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
)
########## END MIDDLEWARE CONFIGURATION


########## URL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = '%s.urls' % SITE_NAME
########## END URL CONFIGURATION


########## APP CONFIGURATION

SHARED_APPS = (
    'django_tenants',
    'backend', # you must list the app where your tenant model resides in
    
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
    #'django.contrib.humanize', # Useful template tags:

    # third party apps
    'rest_framework', # REST API
    'registration', #user registration
    'floppyforms', # better forms
    'grappelli', # admin interface
    'ckeditor', # wysiwyg editor
    'sekizai', #add_to_block template tag
    #'django_select2', # select2 widget (enhanced select box)
    'dbtemplates', # store templates in db (used by mailer module)

    # local apps
    'api',
    'contact',
    'mailer',
    'profiles',

    # last apps
    'django.contrib.admin',   
)


TENANT_APPS = (
    # third party apps
    'constance', # settings in admin
    'constance.backends.database', # settings in admin
    'activities',
    'registrations',
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

########## CONSTANCE CONFIGURATION (settings in admin)
# see http://django-constance.readthedocs.org
CONSTANCE_BACKEND = 'constance.backends.database.DatabaseBackend'
CONSTANCE_SUPERUSER_ONLY = False
CONSTANCE_CONFIG = {
    'START_REGISTRATION': (datetime(2013,9,1, tzinfo=timezone('Europe/Zurich')), 
                           ugettext("Registration opening date")),
    'END_REGISTRATION': (datetime(2013,10,1, tzinfo=timezone('Europe/Zurich')), 
                         ugettext("Registration ending date")),
    'CURRENT_PHASE': (1, 'PREPARATION'),
    'FROM_MAIL': ('Remo Aeschbach <remo.aeschbach@vd.educanet2.ch>', 
                  ugettext("Email used to send")),
    'SCHOOL_NAME': ('EP Coppet', ugettext("Name of school")),
    'SIGNATURE': ("""
Remo Aeschbach
Doyen - responsable du sport scolaire facultatif
EPCoppet
Chemin du Chaucey 7
1296 Coppet
remo.aeschbach@vd.educanet2.ch
+4122 | 557 58 58
+4179 | 417 69 93""", ugettext("Email Signature")),
   
}

########## END CONSTANCE CONFIGURATION


########## USER and REGISTRATION
AUTH_USER_MODEL = 'profiles.FamilyUser'
REGISTRATION_OPEN = True
LOGIN_URL = '/account/login'
LOGOUT_URL = '/account/logout'

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
        'toolbar': [
                    [ 'Source','-','Save','-', 'Cut','Copy','Paste','PasteText','PasteFromWord','-','Undo','Redo', '-', 'Find','Replace','-','SelectAll'],
                    [ 'Bold','Italic','Underline','Strike','Subscript','Superscript','-','RemoveFormat' ] ,'/',
                    [ 'NumberedList','BulletedList','-','Outdent','Indent','-','Blockquote','CreateDiv','-','JustifyLeft','JustifyCenter','JustifyRight','JustifyBlock','-','BidiLtr','BidiRtl' ],
                    [ 'Link','Unlink' ],
                    [ 'Image','Table','HorizontalRule','SpecialChar' ],
                    [ 'TextColor', '-','Format'],
                    [ 'Maximize', 'ShowBlocks','-'],
                ],
        'format_tags': 'p;h1;h2;h3;h4;h5;h6;pre;address',
    },
}

############# Select2
AUTO_RENDER_SELECT2_STATICS = False


############ Celery
# Asynchrnous tasks. 
# See http://celery.readthedocs.org/en/latest/configuration.html
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'


PHANTOMJS = os.environ['PHANTOMJS']
DBTEMPLATES_USE_CODEMIRROR = True