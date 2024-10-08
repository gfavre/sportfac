"""Production settings and globals."""
from .production import *  # noqa: F403


TEMPLATES[0]["DIRS"] = [  # noqa: F405
    normpath(join(SITE_ROOT, "themes", "coppet", "templates")),  # noqa: F405
    normpath(join(SITE_ROOT, "templates")),  # noqa: F405
]

STATICFILES_DIRS = (
    normpath(join(SITE_ROOT, "themes", "coppet", "static")),  # noqa: F405
    normpath(join(SITE_ROOT, "static")),  # noqa: F405
)

KEPCHUP_USE_ABSENCES = False
KEPCHUP_IMPORT_CHILDREN = False
KEPCHUP_PREFILL_YEARS_WITH_TEACHERS = True

KEPCHUP_SEND_PRESENCE_LIST = True
KEPCHUP_SEND_COPY_CONTACT_MAIL_TO_ADMIN = True
KEPCHUP_NO_PAYMENT = False
KEPCHUP_DISPLAY_FREE_WHEN_PRICE_IS_0 = True
KEPCHUP_NO_TERMS = False
KEPCHUP_CHILD_SCHOOL = False
KEPCHUP_DISPLAY_PARENT_CITY = False
KEPCHUP_DISPLAY_PARENT_EMAIL = True
KEPCHUP_DISPLAY_PARENT_PHONE = False
KEPCHUP_DISPLAY_PUBLICLY_SUPERVISOR_EMAIL = True
KEPCHUP_REGISTER_ACCOUNTS_AT_ANY_TIME = True
KEPCHUP_INSTRUCTORS_CAN_REMOVE_REGISTRATIONS = True
KEPCHUP_SEND_BILL_TO_ACCOUNTANT = True
KEPCHUP_CHILDREN_MANDATORY_FIELDS = [
    "first_name",
    "last_name",
    "sex",
    "birth_date",
    "nationality",
    "language",
    "emergency_number",
]
