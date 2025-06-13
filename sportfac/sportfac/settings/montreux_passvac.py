"""Production settings and globals."""
from .production import *  # noqa: F403, F401


TEMPLATES[0]["DIRS"] = [  # noqa: F405
    normpath(join(SITE_ROOT, "themes", "montreux_passvac", "templates")),  # noqa: F405
    normpath(join(SITE_ROOT, "templates")),  # noqa: F405
]

STATICFILES_DIRS = (
    normpath(join(SITE_ROOT, "themes", "montreux_passvac", "static")),  # noqa: F405
    normpath(join(SITE_ROOT, "static")),  # noqa: F405
)

MASTER_DB = "master_users"
DATABASES[MASTER_DB] = env.db("MASTER_DATABASE_URL", default="postgres:///sportfac_montreux_users")  # noqa: F405
OTHER_DB = "other"
DATABASES[OTHER_DB] = env.db("OTHER_DATABASE_URL", default="postgres:///kepchup_montreux_passvac")  # noqa: F405

DATABASES["default"]["ENGINE"] = "django_tenants.postgresql_backend"  # noqa: F405
DATABASE_ROUTERS = [
    "django_tenants.routers.TenantSyncRouter",
    "sportfac.database_router.MasterRouter",
]
AUTHENTICATION_BACKENDS = (
    "sportfac.authentication_backends.MasterUserBackend",
    "django.contrib.auth.backends.ModelBackend",
)
SESSION_COOKIE_NAME = "montreux_epa"

CELERY_TASK_DEFAULT_QUEUE = "montreux_passvac_queue"  # noqa: F405

CELERYBEAT_SCHEDULE["notify-absences"] = {  # noqa: F405
    "task": "absences.tasks.notify_absences",
    "schedule": crontab(hour=19, minute=0),  # noqa: F405
}
CELERYBEAT_SCHEDULE["sync_from_master"] = {  # noqa: F405
    "task": "profiles.tasks.sync_from_master",
    "schedule": crontab(minute="*/10"),  # noqa: F405
}
CELERYBEAT_SCHEDULE["cancel-expired-registrations"] = {  # noqa: F405
    "task": "registrations.tasks.cancel_expired_registrations",
    "schedule": crontab(minute="*/5"),  # noqa: F405
}


KEPCHUP_USE_ABSENCES = True
KEPCHUP_USE_APPOINTMENTS = False
KEPCHUP_IMPORT_CHILDREN = True
KEPCHUP_PREFILL_YEARS_WITH_TEACHERS = False
KEPCHUP_SEND_PRESENCE_LIST = True
KEPCHUP_SEND_COPY_CONTACT_MAIL_TO_ADMIN = True
KEPCHUP_NO_PAYMENT = False
KEPCHUP_USE_DIFFERENTIATED_PRICES = True
KEPCHUP_PAYMENT_METHOD = "postfinance"
KEPCHUP_ALTERNATIVE_PAYMENT_METHODS_FROM_BACKEND = ["external"]
KEPCHUP_EMERGENCY_NUMBER_ON_PARENT = True

KEPCHUP_NO_TERMS = False
KEPCHUP_CHILD_SCHOOL = True
KEPCHUP_FICHE_SALAIRE_MONTREUX = True
KEPCHUP_NO_SSF = True
KEPCHUP_ADDITIONAL_INSTRUCTOR_EMAIL_DOCUMENTS = [
    "pdf/infos-moniteurs-2024.pdf",
    "pdf/GMS_2024_2025.pdf",
]
KEPCHUP_SPLASH_PAGE = True
KEPCHUP_CHILDREN_UNEDITABLE_FIELDS = [
    "first_name",
    "last_name",
    "birth_date",
    "school_year",
    "school",
    "other_school",
    "nationality",
    "language",
    "avs",
]
KEPCHUP_CHILDREN_MANDATORY_FIELDS = [
    "sex",
]
# KEPCHUP_CHILDREN_HIDDEN_FIELDS = ["language", "nationality"]
# FIXME: no way to fill in school, rest returns a primary key, not a name
KEPCHUP_CHILDREN_HIDDEN_FIELDS = ["language", "nationality", "school", "other_school", "emergency_number"]

KEPCHUP_EXPLICIT_SESSION_DATES = True
SCHOOL_YEAR_EDITABLE = False
KEPCHUP_DISPLAY_LAGAPEO = False
KEPCHUP_LOOKUP_LAGAPEO = False
KEPCHUP_LOOKUP_AVS = True
KEPCHUP_CAN_DELETE_CHILD = False
KEPCHUP_USE_BLACKLISTS = True
KEPCHUP_INSTRUCTORS_DISPLAY_EXTERNAL_ID = True
KEPCHUP_INSTRUCTORS_CAN_EDIT_EXTERNAL_ID = True
KEPCHUP_ENABLE_PAYROLLS = True
KEPCHUP_ENABLE_WAITING_LISTS = False
KEPCHUP_REGISTRATION_HIDE_COUNTRY = True
KEPCHUP_REGISTRATION_HIDE_OTHER_PHONES = True
KEPCHUP_REGISTER_ACCOUNTS_AT_ANY_TIME = True


# Registration steps
#########################################
KEPCHUP_ALTERNATIVE_ACTIVITIES_LABEL = "Inscription"
KEPCHUP_ALTERNATIVE_CONFIRM_LABEL = "Résumé"
KEPCHUP_ALTERNATIVE_BILLING_LABEL = "Paiement"


# Single Sign On
#########################################
KEPCHUP_USE_SSO = True
LOGIN_URL = "/client/"


# Dashboard
############################################
KEPCHUP_DASHBOARD_SHOW_CHILDREN_STATS = True
KEPCHUP_DASHBOARD_SHOW_FAMILY_STATS = False
KEPCHUP_REGISTRATION_EXPIRE_MINUTES = 60
