"""Common settings and globals."""
import warnings
from os.path import abspath, basename, dirname, join, normpath
from sys import path

from django.contrib.messages import constants as messages
from django.utils.translation import gettext_lazy as _

import environ
from celery.schedules import crontab


env = environ.Env()

gettext = lambda s: s  # noqa

# PATH CONFIGURATION
# Absolute filesystem path to the Django project directory:
DJANGO_ROOT = dirname(dirname(abspath(__file__)))

# Absolute filesystem path to the top-level project folder:
SITE_ROOT = dirname(DJANGO_ROOT)

# Site name:
SITE_NAME = basename(DJANGO_ROOT)

# Add our project to our pythonpath, this way we don't need to type our project
# name in our dotted import paths:
path.append(DJANGO_ROOT)
# END PATH CONFIGURATION


# DEBUG CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = env.bool("DEBUG", default=False)

# END DEBUG CONFIGURATION


# MANAGER CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = (("Gregory Favre", "gregory.favre@gmail.com"),)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS
# END MANAGER CONFIGURATION


# DATABASE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    "default": {
        "ENGINE": "django_tenants.postgresql_backend",
        "NAME": "",
        "USER": "",
        "PASSWORD": "",
        "HOST": "",
        "PORT": "",
    }
}

# Multitenancy configuration
DATABASE_ROUTERS = ("django_tenants.routers.TenantSyncRouter",)
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

DEFAULT_TENANT_NAME = "current"
TENANT_MODEL = "backend.YearTenant"  # app.Model
TENANT_DOMAIN_MODEL = "backend.Domain"  # app.Model
TENANT_CREATION_FAKES_MIGRATIONS = False
VERSION_SESSION_NAME = "period"

# END DATABASE CONFIGURATION


# GENERAL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#time-zone
TIME_ZONE = "Europe/Zurich"

# See: https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = "fr-CH"
LANGUAGES = (("fr", "French"),)

# see https://docs.djangoproject.com/en/dev/ref/settings/#locale-paths
LOCALE_PATHS = (normpath(join(SITE_ROOT, "locale")),)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-l10n

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True
# END GENERAL CONFIGURATION


# MEDIA CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = normpath(join(SITE_ROOT, "media"))

# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = "/media/"
# END MEDIA CONFIGURATION


# STATIC FILE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = normpath(join(SITE_ROOT, "assets"))

# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = "/static/"

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = (normpath(join(SITE_ROOT, "static")),)

STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "django.contrib.staticfiles.finders.FileSystemFinder",
)

# END STATIC FILE CONFIGURATION


# END SECRET CONFIGURATION


# FIXTURE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-FIXTURE_DIRS
FIXTURE_DIRS = (
    # normpath(join(SITE_ROOT, 'fixtures')),
)
# END FIXTURE CONFIGURATION


# TEMPLATE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            normpath(join(SITE_ROOT, "templates")),
        ],
        "OPTIONS": {
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.debug",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.request",
                "sportfac.context_processors.registration_opened_context",
                "sportfac.context_processors.activities_context",
                "sportfac.context_processors.tenants_context",
                "sportfac.context_processors.kepchup_context",
                "sportfac.context_processors.dynamic_preferences_context",
                "sekizai.context_processors.sekizai",
            ],
            "loaders": [
                "dbtemplates.loader.Loader",
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
            ],
        },
    },
]

# END TEMPLATE CONFIGURATION


# MIDDLEWARE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#middleware-classes
MIDDLEWARE = [
    # Default Django middleware.
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.contrib.sites.middleware.CurrentSiteMiddleware",
    "sportfac.middleware.VersionMiddleware",
    "sportfac.middleware.RegistrationOpenedMiddleware",
    "django.contrib.flatpages.middleware.FlatpageFallbackMiddleware",
    "impersonate.middleware.ImpersonateMiddleware",
]
# END MIDDLEWARE CONFIGURATION


# URL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = "%s.urls" % SITE_NAME
# END URL CONFIGURATION


# APP CONFIGURATION

SHARED_APPS = (
    "django_tenants",
    "backend",  # you must list the app where your tenant model resides in
    # Default Django apps:
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.contrib.sites",
    "django.contrib.flatpages",
    "django.contrib.sitemaps",
    # third party apps
    "adminsortable2",  # admin sortable
    "anymail",  # send mail
    "bootstrap_datepicker_plus",
    "captcha",  # recaptcha
    "ckeditor",  # wysiwyg editor
    "ckeditor_uploader",
    "crispy_forms",  # better forms => DRY
    "dbtemplates",  # store templates in db (used by mailer module)
    "django_countries",  # country field selector
    "dynamic_preferences",
    "floppyforms",  # better forms => bootstrap components
    "import_export",
    "impersonate",  # impersonate users
    "mathfilters",
    "phonenumber_field",
    "rest_framework",  # REST API
    "sekizai",  # add_to_block template tag
    # local apps
    "api",
    "contact",
    "mailer",
    "profiles",
    "wizard",
    # last apps
    "django.contrib.admin",
    "django_select2",  # select2 form input
)

TENANT_APPS = (
    "absences",
    "activities",
    "appointments",
    "registrations",
    "payments",
    "payroll",
    "schools",
    "waiting_slots",
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]
# END APP CONFIGURATION

ADMIN_URL = env.str("ADMIN_URL", default="admin/")

# LOGGING CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#logging
# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"require_debug_false": {"()": "django.utils.log.RequireDebugFalse"}},
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "celery": {
            "handlers": ["console"],
            "level": "INFO",
        },
    },
}
# END LOGGING CONFIGURATION

TEST_RUNNER = "django.test.runner.DiscoverRunner"

# WSGI CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = "wsgi.application"
# END WSGI CONFIGURATION


# MESSAGE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/contrib/messages/


MESSAGE_TAGS = {
    messages.DEBUG: "alert-info",
    messages.INFO: "alert-info",
    messages.SUCCESS: "alert-success",
    messages.WARNING: "alert-warning",
    messages.ERROR: "alert-danger",
}

# END WSGI CONFIGURATION


# REST FRAMEWORK CONFIGURATION

REST_FRAMEWORK = {
    # Use hyperlinked styles by default.
    # Only used if the `serializer_class` attribute is not set on a view.
    "DEFAULT_MODEL_SERIALIZER_CLASS": "rest_framework.serializers.HyperlinkedModelSerializer",
    "DEFAULT_PAGINATION_CLASS": None,  # "rest_framework.pagination.PageNumberPagination",
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly"],
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
        "rest_framework_datatables.renderers.DatatablesRenderer",
    ),
    "DEFAULT_FILTER_BACKENDS": ("rest_framework_datatables.filters.DatatablesFilterBackend",),
    "PAGE_SIZE": 50,
}

# END REST FRAMEWORK CONFIGURATION

# DYNAMIC PREFERENCES CONFIGURATION
# see http://django-dynamic-preferences.readthedocs.io

DYNAMIC_PREFERENCES = {
    # a python attribute that will be added to model instances with preferences
    # override this if the default collide with one of your models attributes/fields
    "MANAGER_ATTRIBUTE": "preferences",
    "MANAGER_ATTRIBUTE": "preferences",
    # The python module in which registered preferences will be searched within each app
    "REGISTRY_MODULE": "dynamic_preferences_registry",
    # Allow quick editing of preferences directly in admin list view
    # WARNING: enabling this feature can cause data corruption if multiple users
    # use the same list view at the same time, see https://code.djangoproject.com/ticket/11313
    "ADMIN_ENABLE_CHANGELIST_FORM": False,
    # Should we enable the admin module for user preferences ?
    "ENABLE_USER_PREFERENCES": False,
    # Customize how you can access preferences from managers. The default is to
    # separate sections and keys with two underscores. This is probably not a settings you'll
    # want to change, but it's here just in case
    "SECTION_KEY_SEPARATOR": "__",
    # Use this to disable caching of preference. This can be useful to debug things
    "ENABLE_CACHE": True,
    # Use this to disable checking preferences names. This can be useful to debug things
    "VALIDATE_NAMES": True,
}

# END DYNAMIC PREFERENCES CONFIGURATION

SWISS_DATE_SHORT = "%d.%m.%Y"
SHORT_DATE_FORMAT = "d.m.Y"
SHORT_DATETIME_FORMAT = "d.m.Y H:i"
DATE_INPUT_FORMATS = [
    SWISS_DATE_SHORT,
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%m/%d/%y",  # '2006-10-25', '10/25/2006', '10/25/06'
    "%b %d %Y",
    "%b %d, %Y",  # 'Oct 25 2006', 'Oct 25, 2006'
    "%d %b %Y",
    "%d %b, %Y",  # '25 Oct 2006', '25 Oct, 2006'
    "%B %d %Y",
    "%B %d, %Y",  # 'October 25 2006', 'October 25, 2006'
    "%d %B %Y",
    "%d %B, %Y",  # '25 October 2006', '25 October, 2006'
]

# USER and REGISTRATION
AUTH_USER_MODEL = "profiles.FamilyUser"
REGISTRATION_OPEN = True
LOGIN_URL = "profiles:auth_login"
LOGOUT_URL = "profiles:logout"
LOGIN_REDIRECT_URL = "profiles:authenticated-home"

# END USER and REGISTRAION


# GRAPPELLI CONFIG
GRAPPELLI_ADMIN_TITLE = "Administration du sport scolaire facultatif"
# END GRAPPELLI CONFIG


# PIPELINE CONFIG
# STATICFILES_STORAGE = 'pipeline.storage.PipelineCachedStorage'

# END PIPELINE CONFIG


# CKEDITOR
CKEDITOR_CONFIGS = {
    "default": {
        "alignment": {"options": ["left", "right"]},
        "contentCss": "/static/css/style.css",
        "extraPlugins": ",".join(["emojione"]),
        "stylesSet": [
            {"name": "sans", "element": "p", "attributes": {"class": "empty-kepchup"}},
            {
                "name": "Cadre orange",
                "element": "p",
                "attributes": {"class": "alert-warning alert"},
            },
            {
                "name": "Cadre bleu clair",
                "element": "p",
                "attributes": {"class": "alert-info alert"},
            },
            {"name": "Cadre vert", "element": "p", "attributes": {"class": "alert alert-success"}},
            {"name": "Cadre rouge", "element": "p", "attributes": {"class": "alert alert-danger"}},
            {"name": "Cadre gris", "element": "p", "attributes": {"class": "well"}},
            {"name": "Bouton", "element": "a", "attributes": {"class": "btn btn-primary"}},
            {"name": "Bouton vert", "element": "a", "attributes": {"class": "btn btn-success"}},
            {"name": "Bouton bleu clair", "element": "a", "attributes": {"class": "btn btn-info"}},
            {"name": "Bouton orange", "element": "a", "attributes": {"class": "btn btn-warning"}},
            {"name": "Bouton rouge", "element": "a", "attributes": {"class": "btn btn-danger"}},
        ],
        "toolbar": "Custom",
        "toolbar_Custom": [
            ["Source", "-", "Print"],
            ["Undo", "Redo"],
            ["Bold", "Italic", "Subscript", "Superscript"],
            ["Format", "TextColor"],
            ["JustifyLeft", "JustifyCenter", "JustifyRight", "JustifyBlock"],
            ["NumberedList", "BulletedList"],
            ["Link", "Unlink", "Anchor"],
            "/",
            ["Image", "Table", "HorizontalRule"],
            ["Styles", "SpecialChar"],
        ],
    }
}

CKEDITOR_UPLOAD_PATH = "uploads/"
CKEDITOR_BROWSE_SHOW_DIRS = True
CKEDITOR_IMAGE_BACKEND = "pillow"
X_FRAME_OPTIONS = "SAMEORIGIN"

CACHES = {
    # … default cache config and others
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "sportfac-local",
    }
}

# Tell select2 which cache configuration to use:
SELECT2_CACHE_BACKEND = "default"

# Select2
AUTO_RENDER_SELECT2_STATICS = False

# Celery
# Asynchrnous tasks.
# See http://celery.readthedocs.org/en/latest/configuration.html
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_PREFIX = ""
CELERY_TASK_TRACK_STARTED = True
CELERYBEAT_SCHEDULE = {
    "update-periods": {
        "task": "backend.tasks.update_current_tenant",
        "schedule": crontab(hour=0, minute=0),
    },
}

PHANTOMJSCLOUD_APIKEY = env("PHANTOMJSCLOUD_APIKEY")

DBTEMPLATES_USE_CODEMIRROR = True

# Phonenumbers
PHONENUMBER_DEFAULT_REGION = "CH"

# Crispy
CRISPY_TEMPLATE_PACK = "bootstrap3"

# Date picker
# The link above contains all settings
BOOTSTRAP_DATEPICKER_PLUS = {
    # Options for all input widgets
    # More options: https://getdatepicker.com/4/Options/
    "options": {
        "locale": "fr",
        "allowInputToggle": True,
    },
    "addon_icon_classes": {
        "month": "bi-calendar-month",
        "date": "icon-calendar",
        "time": "icon-clock ",
    },
    "variant_options": {
        "date": {
            "format": "DD.MM.YYYY",
        },
        "datetime": {
            "format": "DD.MM.YYYY HH:mm",
        },
        "time": {
            "format": "HH:mm",
        },
    },
}

#
# Kepchup Options
#

# general
#

# Use a splash page rather than home. Use by Montreux who has 2 kepchup instances
KEPCHUP_SPLASH_PAGE = False

# no terms and conditions
KEPCHUP_NO_TERMS = False
# not used for the moment.
KEPCHUP_DISPLAY_PARENT_CITY = False
KEPCHUP_DISPLAY_PARENT_EMAIL = False
KEPCHUP_DISPLAY_PARENT_PHONE = False
KEPCHUP_DISPLAY_PUBLICLY_SUPERVISOR_PHONE = False
KEPCHUP_DISPLAY_PUBLICLY_SUPERVISOR_EMAIL = False
# Use other step names during registration.  # TODO: have a dict of names here...
KEPCHUP_ALTERNATIVE_STEPS_NAMING = False
# Activate absence module
KEPCHUP_USE_ABSENCES = False
# By default, absences are connected to courses.
KEPCHUP_ABSENCES_RELATE_TO_ACTIVITIES = False
KEPCHUP_ABSENCES_ORDER_ASC = False
KEPCHUP_ABSENCE_PDF_LANDSCAPE = False
# Activate montreux specific feature to handle instructors pay slips
KEPCHUP_FICHE_SALAIRE_MONTREUX = False

KEPCHUP_REGISTRATION_LEVELS = False
KEPCHUP_REGISTRATION_EXPIRE_MINUTES = 0
KEPCHUP_REGISTRATION_EXPIRE_REMINDER_MINUTES = 0
KEPCHUP_DISPLAY_CAR_NUMBER = False
KEPCHUP_DISPLAY_REGISTRATION_NOTE = False
KEPCHUP_LEVELS_PREFIXER = {}
KEPCHUP_INSTRUCTORS_CAN_REMOVE_REGISTRATIONS = False
KEPCHUP_LIMIT_BY_AGE = False
KEPCHUP_LIMIT_BY_SCHOOL_YEAR = not KEPCHUP_LIMIT_BY_AGE
KEPCHUP_SCHOOL_YEAR_MANDATORY = True
KEPCHUP_AGES = list(range(4, 19))

KEPCHUP_ENABLE_PAYROLLS = False
KEPCHUP_ENABLE_WAITING_LISTS = True
KEPCHUP_WAITING_LIST_REMINDER_HOURS = 24
# User accounts
#
KEPCHUP_REGISTER_ACCOUNTS_AT_ANY_TIME = False
KEPCHUP_ZIPCODE_RESTRICTION = []
KEPCHUP_INSTRUCTORS_DISPLAY_EXTERNAL_ID = False
KEPCHUP_INSTRUCTORS_CAN_EDIT_EXTERNAL_ID = False
KEPCHUP_REGISTRATION_HIDE_COUNTRY = False
KEPCHUP_REGISTRATION_HIDE_OTHER_PHONES = False

# Payment
#
# if true, disable invoicing system
KEPCHUP_NO_PAYMENT = False
KEPCHUP_DISPLAY_FREE_WHEN_PRICE_IS_0 = False
# external, iban, datatrans or none
KEPCHUP_PAYMENT_METHOD = "iban"
KEPCHUP_USE_DIFFERENTIATED_PRICES = False
KEPCHUP_RELY_ON_CHILD_MARKED_UP_PRICE = False
KEPCHUP_LOCAL_ZIPCODES = []
KEPCHUP_SEND_BILL_TO_ACCOUNTANT = False
KEPCHUP_ALTERNATIVE_PAYMENT_METHODS_FROM_BACKEND = ["on-site"]

# Registration steps
#
KEPCHUP_ALTERNATIVE_ABOUT_LABEL = None
KEPCHUP_ALTERNATIVE_CHILDREN_LABEL = None
KEPCHUP_ALTERNATIVE_ACTIVITIES_LABEL = None
KEPCHUP_ALTERNATIVE_CONFIRM_LABEL = None
KEPCHUP_ALTERNATIVE_BILLING_LABEL = None
KEPCHUP_ALTERNATIVE_APPOINTMENTS_LABEL = None

# Children
#
KEPCHUP_CHILDREN_EDITABLE = True
KEPCHUP_ID_LAGAPEO_ALTERNATIVE_LABEL = None
KEPCHUP_CHILDREN_POPUP = False
# Children have a bib number (n° dossard)
KEPCHUP_BIB_NUMBERS = False
# Ask for school of the child
KEPCHUP_CHILD_SCHOOL = False
# Teachers submenu in backend
KEPCHUP_ENABLE_TEACHER_MANAGEMENT = True
# Is other a valid choice?
KEPCHUP_CHILD_SCHOOL_DISPLAY_OTHER = False
# these fields are not editable by parent. Makes sense with KEPCHUP_IMPORT_CHILDREN
KEPCHUP_CHILDREN_UNEDITABLE_FIELDS = []
KEPCHUP_CHILDREN_HIDDEN_FIELDS = []
KEPCHUP_CHILDREN_MANDATORY_FIELDS = [
    "first_name",
    "last_name",
    "sex",
    "birth_date",
    "avs",
    "nationality",
    "language",
    "school_year",
]
# display nb of sessions on public pages. Disabled for Nyon-Prangins
KEPCHUP_DISPLAY_NUMBER_OF_SESSIONS = True
# make emergency number mandatory on children
KEPCHUP_EMERGENCY_NUMBER_MANDATORY = True
KEPCHUP_EMERGENCY_NUMBER_ON_PARENT = False
# Import children lists from lagapeo
KEPCHUP_IMPORT_CHILDREN = False
# School years are related to main teacher of the child
KEPCHUP_PREFILL_YEARS_WITH_TEACHERS = False
# Ask for school building. Manage imports by building
KEPCHUP_USE_BUILDINGS = False
# Display ID Lagapeo
KEPCHUP_DISPLAY_LAGAPEO = False
# Possibility to prefill by lagapeo id
KEPCHUP_LOOKUP_LAGAPEO = False
# Possibility to prefill by avs
KEPCHUP_LOOKUP_AVS = False
# Ability to remove child
KEPCHUP_CAN_DELETE_CHILD = True
# Blacklist to block children from registering
KEPCHUP_USE_BLACKLISTS = False
# Years
KEPCHUP_YEAR_NAMES = {
    1: "1P",
    2: "2P",
    3: "3P",
    4: "4P",
    5: "5P",
    6: "6P",
    7: "7P",
    8: "8P",
    9: "9S",
    10: "10S",
    11: "11S",
    12: "12R",
}

# Activities
#

# In Coppet-Rojalets children can register Poterie at different periods of the year.
KEPCHUP_ACTIVITIES_CAN_REGISTER_SAME_ACTIVITY_TWICE = False
KEPCHUP_ACTIVITIES_POPUP = False
KEPCHUP_CALENDAR_DISPLAY_DATES = True
KEPCHUP_CALENDAR_DISPLAY_COURSE_NAMES = False
KEPCHUP_CALENDAR_HIDDEN_DAYS = [0]
KEPCHUP_EXPLICIT_SESSION_DATES = False
KEPCHUP_NO_EXTRAS = False
KEPCHUP_DISPLAY_OVERLAP_HELP = True
KEPCHUP_ENABLE_ALLOCATION_ACCOUNTS = False

KEPCHUP_ACTIVITY_TYPES = [("activity", _("Activities"))]
KEPCHUP_DISPLAY_COURSE_NUMBER_INSTEAD_OF_ACTIVITY = False
# Email
#

# Send presence list to instructors
KEPCHUP_SEND_PRESENCE_LIST = True
KEPCHUP_SEND_COPY_CONTACT_MAIL_TO_ADMIN = True
KEPCHUP_ADDITIONAL_INSTRUCTOR_EMAIL_DOCUMENTS = []
# If true: do not send E_SSF_decompte_heures_%s_%s.pdf to instructors
KEPCHUP_NO_SSF = False

warnings.filterwarnings("ignore", module="floppyforms", message="Unable to import floppyforms.gis.*")

# Single Sign On
# git #
KEPCHUP_USE_SSO = False
SSO_PRIVATE_KEY = env.str("SSO_PRIVATE_KEY", default="")
SSO_PUBLIC_KEY = env.str("SSO_PUBLIC_KEY", default="")
SSO_SERVER = env.str("SSO_SERVER", default="")
SSO_DASHBOARD_REDIRECT = env.str("SSO_DASHBOARD_REDIRECT", default="/")

# Appointments
#
KEPCHUP_USE_APPOINTMENTS = False
KEPCHUP_APPOINTMENTS_WITHOUT_WIZARD = False

# Payments
#
DATATRANS_API_URL = env.url("DATATRANS_API_URL", default="https://api.sandbox.datatrans.com/")
DATATRANS_PAY_URL = env.url("DATATRANS_PAY_URL", default="https://pay.sandbox.datatrans.com/")
# See: https://api-reference.datatrans.ch/#operation/init
DATATRANS_PAYMENT_METHODS = env.list("DATATRANS_PAYMENT_METHODS", default=["TWI", "ECA", "VIS"])
DATATRANS_USER = env.str("DATATRANS_USER", default="")
DATATRANS_PASSWORD = env.str("DATATRANS_PASSWORD", default="")

POSTFINANCE_SPACE_ID = env.int("POSTFINANCE_SPACE_ID", default="")
POSTFINANCE_USER_ID = env.int("POSTFINANCE_USER_ID", default="")
POSTFINANCE_API_SECRET = env.str("POSTFINANCE_API_SECRET", default="")

# Dashboard
#
KEPCHUP_DASHBOARD_SHOW_CHILDREN_STATS = True
KEPCHUP_DASHBOARD_SHOW_FAMILY_STATS = True

KEPCHUP_ACTIVATE_NYON_MARENS = False
KEPCHUP_NYON_MARENS_EMAIL_RECIPIENTS = ADMINS

IMPERSONATE = {
    "USE_HTTP_REFERER": True,
    "CUSTOM_ALLOW": "profiles.utils.can_impersonate",
    "REDIRECT_FIELD_NAME": "next",
}
