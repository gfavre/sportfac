"""Production settings and globals."""

from .production import *  # noqa: F403, F401


TEMPLATES[0]["DIRS"] = [  # noqa: F405
    normpath(join(SITE_ROOT, "themes", "montreux_ski", "templates")),  # noqa: F405
    normpath(join(SITE_ROOT, "templates")),  # noqa: F405
]

STATICFILES_DIRS = (
    normpath(join(SITE_ROOT, "themes", "montreux_ski", "static")),  # noqa: F405
    normpath(join(SITE_ROOT, "static")),  # noqa: F405
)

# We switch to postmark. Here are the old settings which ended up in mailgun
# EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
# EMAIL_HOST = env('EMAIL_HOST', default='')
# EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
# EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')

MASTER_DB = "master_users"
DATABASES[MASTER_DB] = env.db("MASTER_DATABASE_URL", default="postgres:///kepchup_users")  # noqa: F405
DATABASES["default"]["ENGINE"] = "django_tenants.postgresql_backend"  # noqa: F405
DATABASE_ROUTERS = [
    "django_tenants.routers.TenantSyncRouter",
    "sportfac.database_router.MasterRouter",
]
AUTHENTICATION_BACKENDS = (
    "sportfac.authentication_backends.MasterUserBackend",
    "django.contrib.auth.backends.ModelBackend",
)
SESSION_COOKIE_NAME = "ssfmontreux_hiver"

KEPCHUP_USE_ABSENCES = True
KEPCHUP_USE_APPOINTMENTS = True
KEPCHUP_APPOINTMENTS_WITHOUT_WIZARD = False
KEPCHUP_IMPORT_CHILDREN = True
KEPCHUP_PREFILL_YEARS_WITH_TEACHERS = False
KEPCHUP_SEND_PRESENCE_LIST = True
KEPCHUP_SEND_COPY_CONTACT_MAIL_TO_ADMIN = True
KEPCHUP_NO_PAYMENT = False
KEPCHUP_PAYMENT_METHOD = "postfinance"
KEPCHUP_ALTERNATIVE_PAYMENT_METHODS_FROM_BACKEND = ["external"]

KEPCHUP_NO_TERMS = False
KEPCHUP_NO_SSF = True
KEPCHUP_CHILD_SCHOOL = True
KEPCHUP_CHILD_SCHOOL_DISPLAY_OTHER = False
KEPCHUP_CHILDREN_EDITABLE = False
KEPCHUP_CHILDREN_POPUP = True
KEPCHUP_CHILDREN_UNEDITABLE_FIELDS = [
    "first_name",
    "last_name",
    "birth_date",
    "school_year",
    "school",
    "avs",
]
KEPCHUP_CHILDREN_MANDATORY_FIELDS = [
    "sex",
]
KEPCHUP_CHILDREN_HIDDEN_FIELDS = ["language", "nationality", "school"]
KEPCHUP_ACTIVITIES_POPUP = True
KEPCHUP_CALENDAR_DISPLAY_DATES = False
KEPCHUP_CALENDAR_DISPLAY_COURSE_NAMES = True
KEPCHUP_CALENDAR_HIDDEN_DAYS = [0, 1, 2, 3, 4, 5]
KEPCHUP_BIB_NUMBERS = True
KEPCHUP_FICHE_SALAIRE_MONTREUX = True
KEPCHUP_REGISTRATION_LEVELS = True
KEPCHUP_LEVELS_PREFIXER = {"200": "A"}
KEPCHUP_ADDITIONAL_INSTRUCTOR_EMAIL_DOCUMENTS = [
    "pdf/infos-moniteurs-2024.pdf",
    "pdf/GMS_2024_2025.pdf",
]

KEPCHUP_EMERGENCY_NUMBER_ON_PARENT = True


KEPCHUP_DISPLAY_CAR_NUMBER = True
KEPCHUP_DISPLAY_REGISTRATION_NOTE = True
KEPCHUP_DISPLAY_LAGAPEO = True
KEPCHUP_ALTERNATIVE_STEPS_NAMING = True
KEPCHUP_ABSENCES_RELATE_TO_ACTIVITIES = True
KEPCHUP_EXPLICIT_SESSION_DATES = True
KEPCHUP_DISPLAY_OVERLAP_HELP = False
KEPCHUP_CAN_DELETE_CHILD = True
KEPCHUP_USE_BLACKLISTS = True
KEPCHUP_INSTRUCTORS_DISPLAY_EXTERNAL_ID = True
KEPCHUP_INSTRUCTORS_CAN_EDIT_EXTERNAL_ID = True
KEPCHUP_ENABLE_PAYROLLS = True
KEPCHUP_ENABLE_WAITING_LISTS = False
KEPCHUP_REGISTRATION_HIDE_COUNTRY = True
KEPCHUP_REGISTRATION_HIDE_OTHER_PHONES = True

# Registration steps
#########################################
KEPCHUP_ALTERNATIVE_ACTIVITIES_LABEL = "Cours"
KEPCHUP_ALTERNATIVE_CONFIRM_LABEL = "Transport"
KEPCHUP_ALTERNATIVE_APPOINTMENTS_LABEL = "Matériel"
KEPCHUP_ALTERNATIVE_BILLING_LABEL = "Paiement"


KEPCHUP_REGISTRATION_EXPIRE_MINUTES = None


STATIC_URL = "/hiver/static/"
MEDIA_URL = "/hiver/media/"
FORCE_SCRIPT_NAME = "/hiver"
SESSION_COOKIE_PATH = FORCE_SCRIPT_NAME

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
# Single Sign On
#########################################
KEPCHUP_USE_SSO = True

LOGIN_URL = "/hiver/client/"
LOGOUT_URL = "/hiver/account/logout/"
