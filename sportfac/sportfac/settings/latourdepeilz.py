"""Production settings and globals."""

from .production import *  # noqa: F403


TEMPLATES[0]["DIRS"] = [  # noqa: F405
    normpath(join(SITE_ROOT, "themes", "latourdepeilz", "templates")),  # noqa: F405
    normpath(join(SITE_ROOT, "templates")),  # noqa: F405
]

STATICFILES_DIRS = (
    normpath(join(SITE_ROOT, "themes", "latourdepeilz", "static")),  # noqa: F405
    normpath(join(SITE_ROOT, "static")),  # noqa: F405
)

# Absences
KEPCHUP_USE_ABSENCES = True
KEPCHUP_EXPLICIT_SESSION_DATES = True
KEPCHUP_ABSENCES_ORDER_ASC = True

# Activities
KEPCHUP_ENABLE_ALLOCATION_ACCOUNTS = True
KEPCHUP_ACTIVITIES_CAN_REGISTER_SAME_ACTIVITY_TWICE = True
KEPCHUP_ACTIVITY_TYPES = [
    ("activity", "Prestations"),
    ("sportfac", "Sports scolaires facultatifs"),
]


# Accounts
KEPCHUP_REGISTER_ACCOUNTS_AT_ANY_TIME = True

# Children
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
# Email
#########################################
KEPCHUP_SEND_PRESENCE_LIST = True
KEPCHUP_SEND_COPY_CONTACT_MAIL_TO_ADMIN = True

# Registration
KEPCHUP_CALENDAR_HIDDEN_DAYS = []
KEPCHUP_ACTIVITIES_CAN_REGISTER_SAME_ACTIVITY_TWICE = True
KEPCHUP_INSTRUCTORS_CAN_REMOVE_REGISTRATIONS = False
KEPCHUP_ALTERNATIVE_STEPS_NAMING = True
KEPCHUP_ALTERNATIVE_ABOUT_LABEL = None
KEPCHUP_ALTERNATIVE_CHILDREN_LABEL = None
KEPCHUP_ALTERNATIVE_ACTIVITIES_LABEL = "Prestations"
KEPCHUP_ALTERNATIVE_CONFIRM_LABEL = "Récapitulation"
KEPCHUP_ALTERNATIVE_BILLING_LABEL = None
KEPCHUP_AGES = list(range(4, 26))
KEPCHUP_LIMIT_BY_AGE = True
KEPCHUP_LIMIT_BY_SCHOOL_YEAR = not KEPCHUP_LIMIT_BY_AGE
KEPCHUP_SCHOOL_YEAR_MANDATORY = True
KEPCHUP_REGISTRATION_EXPIRE_MINUTES = 60 * 24 * 7
KEPCHUP_REGISTRATION_EXPIRE_REMINDER_MINUTES = 60 * 48


# Payment
#########################################
KEPCHUP_NO_PAYMENT = False
KEPCHUP_PAYMENT_METHOD = "datatrans"
KEPCHUP_USE_DIFFERENTIATED_PRICES = True
KEPCHUP_LOCAL_ZIPCODES = ["1814"]

# Misc
KEPCHUP_IMPORT_CHILDREN = False
KEPCHUP_ENABLE_TEACHER_MANAGEMENT = False

CELERYBEAT_SCHEDULE["notify-absences"] = {  # noqa: F405
    "task": "absences.tasks.notify_absences",
    "schedule": crontab(hour=0o4, minute=0),  # noqa: F405
}
CELERYBEAT_SCHEDULE["cancel-expired-registrations"] = {  # noqa: F405
    "task": "registrations.tasks.cancel_expired_registrations",
    "schedule": crontab(minute="*/15"),  # noqa: F405
}
CELERYBEAT_SCHEDULE["send-reminders"] = {  # noqa: F405
    "task": "registrations.tasks.send_reminders",
    "schedule": crontab(minute="*/15"),  # noqa: F405
}
