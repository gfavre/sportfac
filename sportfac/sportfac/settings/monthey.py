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

# General
KEPCHUP_USE_ABSENCES = True
KEPCHUP_NO_PAYMENT = False

# User accounts
KEPCHUP_ZIPCODE_RESTRICTION = [
    ["1870", "Monthey"],
    ["1871", "Choëx"],
]

# Children
KEPCHUP_CHILD_SCHOOL = True
KEPCHUP_ENABLE_TEACHER_MANAGEMENT = True
KEPCHUP_EMERGENCY_NUMBER_MANDATORY = True

# LAGAPEO
KEPCHUP_IMPORT_CHILDREN = True
KEPCHUP_PREFILL_YEARS_WITH_TEACHERS = True

# Limitations
KEPCHUP_LIMIT_BY_AGE = False
KEPCHUP_LIMIT_BY_SCHOOL_YEAR = True

# Registrations
KEPCHUP_ACTIVITIES_CAN_REGISTER_SAME_ACTIVITY_TWICE = False

# Dates
KEPCHUP_EXPLICIT_SESSION_DATES = True

# Emails
KEPCHUP_SEND_PRESENCE_LIST = True
KEPCHUP_NO_SSF = False

# Payment
