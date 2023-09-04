"""Production settings and globals."""

from .production import *  # noqa: F403


TEMPLATES[0]["DIRS"] = [  # noqa: F405
    normpath(join(SITE_ROOT, "themes", "nyon", "templates")),  # noqa: F405
    normpath(join(SITE_ROOT, "templates")),  # noqa: F405
]

STATICFILES_DIRS = (
    normpath(join(SITE_ROOT, "themes", "nyon", "static")),  # noqa: F405
    normpath(join(SITE_ROOT, "static")),  # noqa: F405
)

INSTALLED_APPS += ["nyonmarens"]  # noqa: F405

KEPCHUP_ACTIVATE_NYON_MARENS = True
KEPCHUP_NYON_MARENS_EMAIL_RECIPIENTS = [
    "Anne-Marie Garcia <Anne-marie.garcia@vd.ch>",
    "Gérard Produit <Gerard.produit@vd.ch>",
    "Nicole Ortelli <Nicole.ortelli@vd.ch>",
    "Michaël Ferrari <Michael.ferrari@vd.ch>",
    "Sandrine Breitenmoser <Sandrine.breitenmoser@vd.ch>",
    "vlad.andrievici@vd.ch",
    "timothee.tramaux@vd.ch",
    "2911_direction@edu-vd.ch",
]
KEPCHUP_USE_ABSENCES = True
KEPCHUP_ABSENCE_PDF_LANDSCAPE = True
KEPCHUP_IMPORT_CHILDREN = False
KEPCHUP_PREFILL_YEARS_WITH_TEACHERS = False
KEPCHUP_SEND_PRESENCE_LIST = True
KEPCHUP_SEND_COPY_CONTACT_MAIL_TO_ADMIN = True
KEPCHUP_NO_PAYMENT = True
KEPCHUP_NO_TERMS = False
KEPCHUP_NO_SSF = True
KEPCHUP_REGISTER_ACCOUNTS_AT_ANY_TIME = True
KEPCHUP_INSTRUCTORS_CAN_REMOVE_REGISTRATIONS = True

CELERYBEAT_SCHEDULE["notify-absences"] = {  # noqa: F405
    "task": "absences.tasks.notify_absences",
    "schedule": crontab(hour=6, minute=0),  # noqa: F405
}
