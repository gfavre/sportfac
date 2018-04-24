"""Production settings and globals."""

from production import *

TEMPLATES[0]['DIRS'] = [
    normpath(join(SITE_ROOT, 'themes', 'demo', 'templates')),
    normpath(join(SITE_ROOT, 'templates')),
]

STATICFILES_DIRS = (
    normpath(join(SITE_ROOT, 'themes', 'demo', 'static')),
    normpath(join(SITE_ROOT, 'static')),
)


KEPCHUP_USE_ABSENCES = True
KEPCHUP_IMPORT_CHILDREN = True
KEPCHUP_PREFILL_YEARS_WITH_TEACHERS = True
KEPCHUP_SEND_PRESENCE_LIST = True
KEPCHUP_SEND_COPY_CONTACT_MAIL_TO_ADMIN = True
KEPCHUP_NO_PAYMENT = False
KEPCHUP_NO_TERMS = False
KEPCHUP_NO_SSF = False
KEPCHUP_CHILD_SCHOOL = True
KEPCHUP_EMERGENCY_NUMBER_MANDATORY = True
KEPCHUP_DISPLAY_PARENT_CITY = False
KEPCHUP_ADDITIONAL_INSTRUCTOR_EMAIL_DOCUMENTS = []
