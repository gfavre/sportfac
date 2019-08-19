"""Production settings and globals."""

from production import *

TEMPLATES[0]['DIRS'] = [
    normpath(join(SITE_ROOT, 'themes', 'nyon_prangins', 'templates')),
    normpath(join(SITE_ROOT, 'templates')),
]

STATICFILES_DIRS = (
    normpath(join(SITE_ROOT, 'themes', 'nyon_prangins', 'static')),
    normpath(join(SITE_ROOT, 'static')),
)

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env('EMAIL_HOST', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')

KEPCHUP_USE_ABSENCES = True
KEPCHUP_IMPORT_CHILDREN = False
KEPCHUP_USE_BUILDINGS = True
KEPCHUP_PREFILL_YEARS_WITH_TEACHERS = True
KEPCHUP_SEND_PRESENCE_LIST = True
KEPCHUP_SEND_COPY_CONTACT_MAIL_TO_ADMIN = True
KEPCHUP_NO_PAYMENT = True
KEPCHUP_NO_TERMS = False
KEPCHUP_NO_SSF = True
KEPCHUP_DISPLAY_NUMBER_OF_SESSIONS = False
KEPCHUP_REGISTER_ACCOUNTS_AT_ANY_TIME = True
