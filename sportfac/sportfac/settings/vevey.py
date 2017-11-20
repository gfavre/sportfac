"""Production settings and globals."""

from production import *

TEMPLATES[0]['DIRS'] = [
    normpath(join(SITE_ROOT, 'themes', 'vevey', 'templates')),
    normpath(join(SITE_ROOT, 'templates')),
]

STATICFILES_DIRS = (
    normpath(join(SITE_ROOT, 'themes', 'vevey', 'static')),
    normpath(join(SITE_ROOT, 'static')),
)
RAVEN_CONFIG = {
    'dsn': 'https://226a25de763049f1aa6b2405815ad74f:f3ec6c3228264c5289854488cb3bd928@sentry.evoe.wine/4',
}


LOGIN_URL = '/account/login/'
LOGOUT_URL = '/account/logout/'

KEPCHUP_USE_ABSENCES = True
KEPCHUP_IMPORT_CHILDREN = False
KEPCHUP_PREFILL_YEARS_WITH_TEACHERS = False
KEPCHUP_SEND_PRESENCE_LIST = True
KEPCHUP_SEND_COPY_CONTACT_MAIL_TO_ADMIN = True
KEPCHUP_NO_PAYMENT = True
KEPCHUP_NO_TERMS = False
KEPCHUP_NO_SSF = True
KEPCHUP_CHILD_SCHOOL = True
KEPCHUP_ACTIVITIES_CAN_REGISTER_SAME_ACTIVITY_TWICE = True
