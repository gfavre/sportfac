"""Production settings and globals."""

from .production import *


TEMPLATES[0]["DIRS"] = [
    normpath(join(SITE_ROOT, "themes", "rojalets", "templates")),
    normpath(join(SITE_ROOT, "templates")),
]

STATICFILES_DIRS = (
    normpath(join(SITE_ROOT, "themes", "rojalets", "static")),
    normpath(join(SITE_ROOT, "static")),
)

# We switch to postmark. Here are the old settings which ended up in mailgun
# EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
# EMAIL_HOST = env('EMAIL_HOST', default='')
# EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
# EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')

KEPCHUP_USE_ABSENCES = True
KEPCHUP_IMPORT_CHILDREN = False
KEPCHUP_PREFILL_YEARS_WITH_TEACHERS = False
KEPCHUP_SEND_PRESENCE_LIST = True
KEPCHUP_SEND_COPY_CONTACT_MAIL_TO_ADMIN = True
KEPCHUP_NO_PAYMENT = False
KEPCHUP_NO_TERMS = False
KEPCHUP_CHILD_SCHOOL = False
KEPCHUP_EMERGENCY_NUMBER_MANDATORY = True
KEPCHUP_DISPLAY_PARENT_CITY = True
KEPCHUP_ADDITIONAL_INSTRUCTOR_EMAIL_DOCUMENTS = []
KEPCHUP_CALENDAR_DISPLAY_DATES = True
KEPCHUP_CALENDAR_DISPLAY_COURSE_NAMES = False
KEPCHUP_ACTIVITIES_CAN_REGISTER_SAME_ACTIVITY_TWICE = False
KEPCHUP_BIB_NUMBERS = False
KEPCHUP_FICHE_SALAIRE_MONTREUX = False
KEPCHUP_REGISTRATION_LEVELS = False
KEPCHUP_DISPLAY_CAR_NUMBER = False
KEPCHUP_DISPLAY_REGISTRATION_NOTE = False


CELERYBEAT_SCHEDULE["notify-absences"] = {
    "task": "absences.tasks.notify_absences",
    "schedule": crontab(hour=19, minute=0),
}
