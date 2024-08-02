"""Production settings and globals."""

from .production import *  # noqa: F403


TEMPLATES[0]["DIRS"] = [  # noqa: F405
    normpath(join(SITE_ROOT, "themes", "jorat", "templates")),  # noqa: F405
    normpath(join(SITE_ROOT, "templates")),  # noqa: F405
]

STATICFILES_DIRS = (
    normpath(join(SITE_ROOT, "themes", "jorat", "static")),  # noqa: F405
    normpath(join(SITE_ROOT, "static")),  # noqa: F405
)


KEPCHUP_USE_ABSENCES = True
KEPCHUP_NO_PAYMENT = True
KEPCHUP_USE_BLACKLISTS = False

KEPCHUP_REGISTER_ACCOUNTS_AT_ANY_TIME = True
KEPCHUP_INSTRUCTORS_DISPLAY_EXTERNAL_ID = False
KEPCHUP_INSTRUCTORS_CAN_EDIT_EXTERNAL_ID = False
KEPCHUP_ZIPCODE_RESTRICTION = []

KEPCHUP_BIB_NUMBERS = False
KEPCHUP_CHILD_SCHOOL = True
KEPCHUP_PREFILL_YEARS_WITH_TEACHERS = True
KEPCHUP_EMERGENCY_NUMBER_MANDATORY = False

KEPCHUP_IMPORT_CHILDREN = True

KEPCHUP_LIMIT_BY_SCHOOL_YEAR = True
KEPCHUP_LIMIT_BY_AGE = False

KEPCHUP_INSTRUCTORS_CAN_REMOVE_REGISTRATIONS = False
KEPCHUP_ACTIVITIES_CAN_REGISTER_SAME_ACTIVITY_TWICE = True

KEPCHUP_EXPLICIT_SESSION_DATES = True

KEPCHUP_SEND_PRESENCE_LIST = True
KEPCHUP_NO_SSF = False


CELERYBEAT_SCHEDULE["notify-absences"] = {  # noqa: F405
    "task": "absences.tasks.notify_absences",
    "schedule": crontab(hour=6, minute=30),  # noqa: F405
}
