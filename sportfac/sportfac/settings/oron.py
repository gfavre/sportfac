"""Production settings and globals."""
from .production import *  # noqa: F403


TEMPLATES[0]["DIRS"] = [  # noqa: F405
    normpath(join(SITE_ROOT, "themes", "oron", "templates")),  # noqa: F405
    normpath(join(SITE_ROOT, "templates")),  # noqa: F405
]

STATICFILES_DIRS = (
    normpath(join(SITE_ROOT, "themes", "oron", "static")),  # noqa: F405
    normpath(join(SITE_ROOT, "static")),  # noqa: F405
)
CELERY_PREFIX = "oron:"


# General
KEPCHUP_USE_ABSENCES = True
KEPCHUP_NO_PAYMENT = True
KEPCHUP_USE_BLACKLISTS = False

# User accounts
KEPCHUP_REGISTER_ACCOUNTS_AT_ANY_TIME = True
KEPCHUP_ZIPCODE_RESTRICTION = []
KEPCHUP_INSTRUCTORS_DISPLAY_EXTERNAL_ID = False
KEPCHUP_INSTRUCTORS_CAN_EDIT_EXTERNAL_ID = False

# Children
KEPCHUP_BIB_NUMBERS = False
KEPCHUP_CHILD_SCHOOL = False
KEPCHUP_ENABLE_TEACHER_MANAGEMENT = False
KEPCHUP_CHILDREN_MANDATORY_FIELDS = [
    "first_name",
    "last_name",
    "sex",
    "birth_date",
    "avs",
    "nationality",
    "language",
    "school_year",
    "emergency_number",
]
# LAGAPEO
KEPCHUP_IMPORT_CHILDREN = False
KEPCHUP_PREFILL_YEARS_WITH_TEACHERS = False

# Limitations
KEPCHUP_LIMIT_BY_AGE = False
KEPCHUP_LIMIT_BY_SCHOOL_YEAR = True

# Registrations
KEPCHUP_ACTIVITIES_CAN_REGISTER_SAME_ACTIVITY_TWICE = True
KEPCHUP_INSTRUCTORS_CAN_REMOVE_REGISTRATIONS = True
KEPCHUP_ENABLE_WAITING_LISTS = True

# Dates
KEPCHUP_EXPLICIT_SESSION_DATES = False

# Emails
KEPCHUP_SEND_PRESENCE_LIST = True
KEPCHUP_NO_SSF = False

# Payment


CELERYBEAT_SCHEDULE["notify-absences"] = {  # noqa: F405
    "task": "absences.tasks.notify_absences",
    "schedule": crontab(hour=6, minute=0),  # noqa: F405
}
