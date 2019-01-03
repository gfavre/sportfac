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

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env('EMAIL_HOST', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')

LOGIN_URL = '/hiver/account/login/'
LOGOUT_URL = '/hiver/account/logout/'

KEPCHUP_USE_ABSENCES = True
KEPCHUP_IMPORT_CHILDREN = True
KEPCHUP_PREFILL_YEARS_WITH_TEACHERS = False
KEPCHUP_SEND_PRESENCE_LIST = True
KEPCHUP_SEND_COPY_CONTACT_MAIL_TO_ADMIN = True
KEPCHUP_NO_PAYMENT = False
KEPCHUP_NO_TERMS = False
KEPCHUP_NO_SSF = True
KEPCHUP_CHILD_SCHOOL = True
KEPCHUP_CALENDAR_DISPLAY_DATES = False
KEPCHUP_CALENDAR_DISPLAY_COURSE_NAMES = True
KEPCHUP_BIB_NUMBERS = True
KEPCHUP_FICHE_SALAIRE_MONTREUX = True
KEPCHUP_REGISTRATION_LEVELS = True
KEPCHUP_LEVELS_PREFIXER = {'200': 'A',}

KEPCHUP_DISPLAY_CAR_NUMBER = True
KEPCHUP_DISPLAY_REGISTRATION_NOTE = True
KEPCHUP_ALTERNATIVE_STEPS_NAMING = True
KEPCHUP_ABSENCES_RELATE_TO_ACTIVITIES = True



STATIC_URL = '/hiver/static/'
FORCE_SCRIPT_NAME = '/hiver'
SESSION_COOKIE_NAME = 'ssf_hiver_sessionid'
SESSION_COOKIE_PATH = FORCE_SCRIPT_NAME

CELERYBEAT_SCHEDULE['notify-absences'] = {
        'task': 'absences.tasks.notify_absences',
        'schedule': crontab(hour=19, minute=0),
}
