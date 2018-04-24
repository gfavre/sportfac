"""Production settings and globals."""

from production import *

TEMPLATES[0]['DIRS'] = [
    normpath(join(SITE_ROOT, 'themes', 'coppet', 'templates')),
    normpath(join(SITE_ROOT, 'templates')),
]

STATICFILES_DIRS = (
    normpath(join(SITE_ROOT, 'themes', 'coppet', 'static')),
    normpath(join(SITE_ROOT, 'static')),
)
import os
import raven

RAVEN_CONFIG = {
    'dsn': 'https://3f862f015a1044e1962fd7a4e77ec5a2:5404be0237894b8fbfbf0122fd280280@sentry.io/1194911',
    # If you are using git, you can also automatically configure the
    # release based on the git info.
    'release': raven.fetch_git_sha(os.path.abspath(os.pardir)),
}

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env('EMAIL_HOST', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')

KEPCHUP_USE_ABSENCES = False
KEPCHUP_IMPORT_CHILDREN = False
KEPCHUP_PREFILL_YEARS_WITH_TEACHERS = True
KEPCHUP_SEND_PRESENCE_LIST = True
KEPCHUP_SEND_COPY_CONTACT_MAIL_TO_ADMIN = True
KEPCHUP_NO_PAYMENT = False
KEPCHUP_NO_TERMS = False
KEPCHUP_CHILD_SCHOOL = False
KEPCHUP_EMERGENCY_NUMBER_MANDATORY = True
KEPCHUP_DISPLAY_PARENT_CITY = True
