"""Development settings and globals."""
from .base import *  # noqa: F403


# DEBUG CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = True


# SECRET CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
# Note: This key only used for development and testing.
SECRET_KEY = env("DJANGO_SECRET_KEY", default="CHANGEME!!!")  # noqa: F405


SHARED_APPS += (  # noqa: F405
    "djcelery",
    "kombu.transport.django",
)

INSTALLED_APPS += (  # noqa: F405
    "django_extensions",  # more commands
    "debug_toolbar",  # debugging
    "corsheaders",
)
MIDDLEWARE = ["corsheaders.middleware.CorsMiddleware"] + MIDDLEWARE  # noqa: F405
CORS_ALLOW_ALL_ORIGINS = DEBUG


# See: https://github.com/django-debug-toolbar/django-debug-toolbar#installation
INTERNAL_IPS = ("127.0.0.1",)

# See: https://github.com/django-debug-toolbar/django-debug-toolbar#installation
MIDDLEWARE += [  # noqa: F405
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]


ALLOWED_HOSTS = ("127.0.0.1", "localhost", "test.com", "tenant.test.com", "testserver")

# END DEBUG CONFIGURATION


# DATABA:qSE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    # 'other': env.db('DATABASE_URL', default='postgres:///sportfac'),
    #"master_users": env.db("MASTER_DATABASE_URL", default="postgres:///kepchup_users"),  # noqa: F405
    "default": env.db("OTHER_DB", "postgres:///sportfac_montreux"),  # noqa: F405
}
DATABASES["default"]["ENGINE"] = "django_tenants.postgresql_backend"

DATABASE_ROUTERS = [
    "django_tenants.routers.TenantSyncRouter",
    #"sportfac.database_router.MasterRouter",
]
AUTHENTICATION_BACKENDS = (
    #"sportfac.authentication_backends.MasterUserBackend",
    "django.contrib.auth.backends.ModelBackend",
)
SESSION_COOKIE_NAME = "sportfac"
# END DATABASE CONFIGURATION


# TOOLBAR CONFIGURATION
# See: https://github.com/django-debug-toolbar/django-debug-toolbar#installation


DEBUG_TOOLBAR_CONFIG = {
    "INTERCEPT_REDIRECTS": False,
    "SHOW_TEMPLATE_CONTEXT": True,
    "SKIP_TEMPLATE_PREFIXES": ("django/forms/widgets/", "admin/widgets/", "floppyforms/"),
}
DEBUG_TOOLBAR_PANELS = [
    "debug_toolbar.panels.versions.VersionsPanel",
    "debug_toolbar.panels.timer.TimerPanel",
    "debug_toolbar.panels.settings.SettingsPanel",
    "debug_toolbar.panels.headers.HeadersPanel",
    "debug_toolbar.panels.request.RequestPanel",
    "debug_toolbar.panels.sql.SQLPanel",
    "debug_toolbar.panels.staticfiles.StaticFilesPanel",
    "debug_toolbar.panels.templates.TemplatesPanel",
    "debug_toolbar.panels.cache.CachePanel",
    "debug_toolbar.panels.signals.SignalsPanel",
    "debug_toolbar.panels.logging.LoggingPanel",
    "debug_toolbar.panels.redirects.RedirectsPanel",
]
# END TOOLBAR CONFIGURATION


# EMAIL:
DEFAULT_FROM_EMAIL = "sportfac@localhost"
EMAIL_SUBJECT_PREFIX = "[%s] " % SITE_NAME  # noqa: F405

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
# EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
# EMAIL_FILE_PATH = env('EMAIL_FILE_PATH', default='/tmp/app-messages')
# END EMAIL CONFIGURATION

TEMPLATES[0]["DIRS"] = [  # noqa: F405
    normpath(join(SITE_ROOT, "themes", "jorat", "templates")),  # noqa: F405
    normpath(join(SITE_ROOT, "templates")),  # noqa: F405
]

STATICFILES_DIRS = (
    normpath(join(SITE_ROOT, "themes", "jorat", "static")),  # noqa: F405
    normpath(join(SITE_ROOT, "static")),  # noqa: F405
)
COMPRESS_ENABLED = True


INSTALLED_APPS += ["nyonmarens"]  # noqa: F405
KEPCHUP_ACTIVATE_NYON_MARENS = True

KEPCHUP_USE_ABSENCES = True
KEPCHUP_ABSENCES_RELATE_TO_ACTIVITIES = False
KEPCHUP_ABSENCES_ORDER_ASC = True

KEPCHUP_USE_APPOINTMENTS = False
KEPCHUP_USE_BUILDINGS = False
KEPCHUP_SEND_PRESENCE_LIST = True
KEPCHUP_SEND_COPY_CONTACT_MAIL_TO_ADMIN = True
KEPCHUP_NO_TERMS = False
KEPCHUP_CHILD_SCHOOL = True
KEPCHUP_ADDITIONAL_INSTRUCTOR_EMAIL_DOCUMENTS = [
    "pdf/Lettre-Moniteurs-cours-automne-2017.pdf",
    "pdf/GMS_2017-2018.pdf",
]
KEPCHUP_CALENDAR_DISPLAY_DATES = True
KEPCHUP_CALENDAR_DISPLAY_COURSE_NAMES = True
KEPCHUP_CALENDAR_HIDDEN_DAYS = [
    0,
]
KEPCHUP_BIB_NUMBERS = True
KEPCHUP_CHILDREN_HIDDEN_FIELDS = []
KEPCHUP_FICHE_SALAIRE_MONTREUX = True
KEPCHUP_DISPLAY_CAR_NUMBER = True
KEPCHUP_DISPLAY_REGISTRATION_NOTE = True
KEPCHUP_DISPLAY_PARENT_CITY = True
KEPCHUP_DISPLAY_PUBLICLY_SUPERVISOR_PHONE = True
KEPCHUP_DISPLAY_PUBLICLY_SUPERVISOR_EMAIL = True
KEPCHUP_REGISTRATION_LEVELS = True
KEPCHUP_ACTIVITIES_CAN_REGISTER_SAME_ACTIVITY_TWICE = True
KEPCHUP_DISPLAY_COURSE_NUMBER_INSTEAD_OF_ACTIVITY = True
KEPCHUP_NO_SSF = True
KEPCHUP_IMPORT_CHILDREN = True
KEPCHUP_DISPLAY_NUMBER_OF_SESSIONS = False
KEPCHUP_SPLASH_PAGE = False
KEPCHUP_CHILDREN_UNEDITABLE_FIELDS = ["first_name", "last_name", "school"]
KEPCHUP_CHILDREN_MANDATORY_FIELDS = [
    "first_name",
    "last_name",
    "sex",
    "birth_date",
    "nationality",
    "language",
    "school_year",
    "emergency_number",
]
KEPCHUP_ID_LAGAPEO_ALTERNATIVE_LABEL = "Identifiant pour cours facultatif"

KEPCHUP_REGISTER_ACCOUNTS_AT_ANY_TIME = True
KEPCHUP_EXPLICIT_SESSION_DATES = False

KEPCHUP_ZIPCODE_RESTRICTION = [
    ["1277", "Arnex-sur-Nyon"],
    ["1273", "Arzier-Le Muids"],
    ["1269", "Bassins"],
    ["1268", "Begnins"],
    ["1279", "Bogis-Bossey"],
    ["1277", "Borex"],
    ["1195", "Bursinel"],
    ["1183", "Bursins"],
    ["1268", "Burtigny"],
    ["1279", "Chavannes-de-Bogis"],
    ["1290", "Chavannes-des-Bois"],
    ["1275", "Chéserex"],
    ["1267", "Coinsins"],
    ["1291", "Commugny"],
    ["1296", "Coppet"],
    ["1299", "Crans-près-Céligny"],
    ["1263", "Crassier"],
    ["1266", "Duillier"],
    ["1195", "Dully"],
    ["1186", "Essertines-sur-Rolle"],
    ["1260", "Eysins"],
    ["1297", "Founex"],
    ["1272", "Genolier"],
    ["1182", "Gilly"],
    ["1276", "Gingins"],
    ["1271", "Givrins"],
    ["1196", "Gland"],
    ["1276", "Grens"],
    ["1278", "La Rippe"],
    ["1261", "Le Vaud"],
    ["1261", "Longirod"],
    ["1184", "Luins"],
    ["1261", "Marchissy"],
    ["1295", "Mies"],
    ["1185", "Mont-sur-Rolle"],
    ["1260", "Nyon"],
    ["116", "Perroy"],
    ["1197", "Prangins"],
    ["1180", "Rolle"],
    ["1264", "Saint-Cergue"],
    ["1265", "Saint-George"],
    ["1188", "Signy-Avenex"],
    ["1274", "Tannay"],
    ["1180", "Tartegnin"],
    ["1270", "Trélex"],
    ["1267", "Vich"],
    ["1184", "Vinzel"],
]
KEPCHUP_REGISTRATION_HIDE_COUNTRY = True
KEPCHUP_REGISTRATION_HIDE_OTHER_PHONES = True

KEPCHUP_DISPLAY_LAGAPEO = True
KEPCHUP_INSTRUCTORS_CAN_REMOVE_REGISTRATIONS = True
KEPCHUP_ENABLE_ALLOCATION_ACCOUNTS = True
KEPCHUP_ENABLE_TEACHER_MANAGEMENT = True
KEPCHUP_ENABLE_PAYROLLS = True
KEPCHUP_DASHBOARD_SHOW_CHILDREN_STATS = True
KEPCHUP_DASHBOARD_SHOW_FAMILY_STATS = True
KEPCHUP_USE_BLACKLISTS = True
KEPCHUP_LIMIT_BY_AGE = False
KEPCHUP_LIMIT_BY_SCHOOL_YEAR = not KEPCHUP_LIMIT_BY_AGE
KEPCHUP_SCHOOL_YEAR_MANDATORY = False
KEPCHUP_REGISTRATION_EXPIRE_MINUTES = 60
KEPCHUP_REGISTRATION_EXPIRE_REMINDER_MINUTES = 30
KEPCHUP_INSTRUCTORS_DISPLAY_EXTERNAL_ID = True
KEPCHUP_INSTRUCTORS_CAN_EDIT_EXTERNAL_ID = True
KEPCHUP_ENABLE_WAITING_LISTS = True
KEPCHUP_EMERGENCY_NUMBER_ON_PARENT = True

# Registration steps
#
KEPCHUP_ALTERNATIVE_ACTIVITIES_LABEL = "Inscription"
KEPCHUP_ALTERNATIVE_CONFIRM_LABEL = "Résumé"
KEPCHUP_ALTERNATIVE_BILLING_LABEL = "Paiement"
KEPCHUP_ALTERNATIVE_APPOINTMENTS_LABEL = "Matériel"

# Single Sign On
#
KEPCHUP_USE_SSO = False
# LOGIN_URL = '/client/'
# LOGOUT_URL = 'https://users.ssfmontreux.ch/logout/'

# Payment
#
# if true, disable invoicing system
KEPCHUP_NO_PAYMENT = False
KEPCHUP_DISPLAY_FREE_WHEN_PRICE_IS_0 = False
# iban, datatrans, postfinance, ... or none => see in Bill.payment_method
KEPCHUP_PAYMENT_METHOD = "postfinance"
KEPCHUP_ALTERNATIVE_PAYMENT_METHODS_FROM_BACKEND = ["external"]
KEPCHUP_USE_DIFFERENTIATED_PRICES = True
KEPCHUP_LOCAL_ZIPCODES = ["1814", "1272"]
KEPCHUP_PREFILL_YEARS_WITH_TEACHERS = False
KEPCHUP_SEND_BILL_TO_ACCOUNTANT = True

KEPCHUP_YEAR_NAMES = {
    1: "1H",
    2: "2H",
    3: "3H",
    4: "4H",
    5: "5H",
    6: "6H",
    7: "7H",
    8: "8H",
    9: "9H",
    10: "10H",
    11: "11H",
    12: "12H",
}


CELERY_ALWAYS_EAGER = True

CELERYBEAT_SCHEDULE["notify-absences"] = {  # noqa F405
    "task": "absences.tasks.notify_absences",
    "schedule": crontab(hour=19, minute=0),  # noqa F405
}
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "sportfac-local",
    },
    "dbtemplates": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "sportfac-local-templates",
    },
}

SILENCED_SYSTEM_CHECKS = ["captcha.recaptcha_test_key_error"]

RECAPTCHA_PUBLIC_KEY = env("RECAPTCHA_PUBLIC_KEY", default="")  # noqa F405
RECAPTCHA_PRIVATE_KEY = env("RECAPTCHA_PRIVATE_KEY", default="")  # noqa F405
