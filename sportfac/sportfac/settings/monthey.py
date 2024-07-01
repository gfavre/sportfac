"""Production settings and globals."""
from .production import *  # noqa: F403


TEMPLATES[0]["DIRS"] = [  # noqa: F405
    normpath(join(SITE_ROOT, "themes", "monthey", "templates")),  # noqa: F405
    normpath(join(SITE_ROOT, "templates")),  # noqa: F405
]

STATICFILES_DIRS = (
    normpath(join(SITE_ROOT, "themes", "monthey", "static")),  # noqa: F405
    normpath(join(SITE_ROOT, "static")),  # noqa: F405
)
CELERY_PREFIX = "monthey:"

# General
KEPCHUP_USE_ABSENCES = True
KEPCHUP_NO_PAYMENT = False
KEPCHUP_DISPLAY_PUBLICLY_SUPERVISOR_PHONE = True
KEPCHUP_DISPLAY_PUBLICLY_SUPERVISOR_EMAIL = True

# User accounts
KEPCHUP_ZIPCODE_RESTRICTION = [
    ["1870", "Monthey"],
    ["1871", "Choëx"],
]

# Children
KEPCHUP_CHILD_SCHOOL = False
KEPCHUP_ENABLE_TEACHER_MANAGEMENT = True
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
# LAGAPEO
KEPCHUP_IMPORT_CHILDREN = False
KEPCHUP_DISPLAY_LAGAPEO = False
KEPCHUP_PREFILL_YEARS_WITH_TEACHERS = True

# Limitations
KEPCHUP_LIMIT_BY_AGE = False
KEPCHUP_LIMIT_BY_SCHOOL_YEAR = True

# Registrations
KEPCHUP_ACTIVITIES_CAN_REGISTER_SAME_ACTIVITY_TWICE = True
KEPCHUP_ENABLE_WAITING_LISTS = True

# Dates
KEPCHUP_EXPLICIT_SESSION_DATES = True

# Emails
KEPCHUP_SEND_PRESENCE_LIST = True
KEPCHUP_NO_SSF = False

# Payment
KEPCHUP_PAYMENT_METHOD = "wire_transfer"


CELERYBEAT_SCHEDULE["notify-absences"] = {  # noqa: F405
    "task": "absences.tasks.notify_absences",
    "schedule": crontab(hour=6, minute=0),  # noqa: F405
}
CELERYBEAT_SCHEDULE["cancel-expired-registrations"] = {  # noqa: F405
    "task": "registrations.tasks.cancel_expired_registrations",
    "schedule": crontab(minute="*/15"),  # noqa: F405
}
