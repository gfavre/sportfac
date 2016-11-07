"""Production settings and globals."""

from production import *

TEMPLATES[0]['DIRS'] = [
    normpath(join(SITE_ROOT, 'themes', 'montreux_ski', 'templates')),
    normpath(join(SITE_ROOT, 'templates')),
]

STATICFILES_DIRS = (
    normpath(join(SITE_ROOT, 'themes', 'montreux_ski', 'static')),
    normpath(join(SITE_ROOT, 'static')),
)
RAVEN_CONFIG = {
    'dsn': 'https://226a25de763049f1aa6b2405815ad74f:f3ec6c3228264c5289854488cb3bd928@sentry.evoe.wine/4',
}

KEPCHUP_USE_ABSENCES = True
KEPCHUP_IMPORT_CHILDREN = True
KEPCHUP_PREFILL_YEARS_WITH_TEACHERS = False
KEPCHUP_SEND_PRESENCE_LIST = True 
KEPCHUP_SEND_COPY_CONTACT_MAIL_TO_ADMIN = True
KEPCHUP_NO_PAYMENT = False
KEPCHUP_NO_TERMS = False
KEPCHUP_CHILD_SCHOOL = True


STATIC_URL = '/hiver/static/'
