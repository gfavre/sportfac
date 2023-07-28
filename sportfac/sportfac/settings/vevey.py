"""Production settings and globals."""
from .production import *  # noqa: F403


TEMPLATES[0]["DIRS"] = [  # noqa: F405
    normpath(join(SITE_ROOT, "themes", "vevey", "templates")),  # noqa: F405
    normpath(join(SITE_ROOT, "templates")),  # noqa: F405
]

STATICFILES_DIRS = (
    normpath(join(SITE_ROOT, "themes", "vevey", "static")),  # noqa: F405
    normpath(join(SITE_ROOT, "static")),  # noqa: F405
)


KEPCHUP_USE_ABSENCES = True
KEPCHUP_PREFILL_YEARS_WITH_TEACHERS = False
KEPCHUP_SEND_PRESENCE_LIST = True
KEPCHUP_SEND_COPY_CONTACT_MAIL_TO_ADMIN = True
KEPCHUP_NO_PAYMENT = True
KEPCHUP_NO_TERMS = False

KEPCHUP_NO_SSF = True
KEPCHUP_CAN_DELETE_CHILD = False
KEPCHUP_CHILDREN_UNEDITABLE_FIELDS = [
    "first_name",
    "last_name",
    "birth_date",
    "school_year",
    "school",
    "other_school",
    "nationality",
    "language",
]
KEPCHUP_DISPLAY_LAGAPEO = True
KEPCHUP_IMPORT_CHILDREN = True

KEPCHUP_CHILD_SCHOOL = True
KEPCHUP_CHILDREN_HIDDEN_FIELDS = []
KEPCHUP_ACTIVITIES_CAN_REGISTER_SAME_ACTIVITY_TWICE = True
KEPCHUP_CHILD_SCHOOL_DISPLAY_OTHER = True
KEPCHUP_REGISTER_ACCOUNTS_AT_ANY_TIME = True
KEPCHUP_EXPLICIT_SESSION_DATES = True


CELERYBEAT_SCHEDULE["notify-absences"] = {  # noqa: F405
    "task": "absences.tasks.notify_absences",
    "schedule": crontab(hour=6, minute=0),  # noqa: F405
}
