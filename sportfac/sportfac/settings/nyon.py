"""Production settings and globals."""

from production import *

TEMPLATES[0]['DIRS'] = [
    normpath(join(SITE_ROOT, 'themes', 'nyon', 'templates')),
    normpath(join(SITE_ROOT, 'templates')),
]

STATICFILES_DIRS = (
    normpath(join(SITE_ROOT, 'themes', 'nyon', 'static')),
    normpath(join(SITE_ROOT, 'static')),
)

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
