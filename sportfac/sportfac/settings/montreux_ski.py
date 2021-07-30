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

# We switch to postmark. Here are the old settings which ended up in mailgun
# EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
# EMAIL_HOST = env('EMAIL_HOST', default='')
# EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
# EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')

MASTER_DB = 'master_users'
DATABASES[MASTER_DB] = env.db('MASTER_DATABASE_URL', default='postgres:///kepchup_users')
DATABASES['default']['ENGINE'] = 'django_tenants.postgresql_backend'
DATABASE_ROUTERS = ['django_tenants.routers.TenantSyncRouter', 'sportfac.database_router.MasterRouter']
AUTHENTICATION_BACKENDS = ('sportfac.authentication_backends.MasterUserBackend',
                           'django.contrib.auth.backends.ModelBackend')
SESSION_COOKIE_NAME = 'ssfmontreux_hiver'



KEPCHUP_USE_ABSENCES = True
KEPCHUP_USE_APPOINTMENTS = True
KEPCHUP_IMPORT_CHILDREN = True
KEPCHUP_PREFILL_YEARS_WITH_TEACHERS = False
KEPCHUP_SEND_PRESENCE_LIST = True
KEPCHUP_SEND_COPY_CONTACT_MAIL_TO_ADMIN = True
KEPCHUP_NO_PAYMENT = False
KEPCHUP_NO_TERMS = False
KEPCHUP_NO_SSF = True
KEPCHUP_CHILD_SCHOOL = True
KEPCHUP_CHILD_SCHOOL_DISPLAY_OTHER = False
KEPCHUP_CHILDREN_UNEDITABLE_FIELDS = ['first_name', 'last_name', 'birth_date', 'school_year', 'school']
KEPCHUP_CALENDAR_DISPLAY_DATES = False
KEPCHUP_CALENDAR_DISPLAY_COURSE_NAMES = True
KEPCHUP_CALENDAR_HIDDEN_DAYS = [0, 1, 2, 3, 4, 5]
KEPCHUP_BIB_NUMBERS = True
KEPCHUP_FICHE_SALAIRE_MONTREUX = True
KEPCHUP_REGISTRATION_LEVELS = True
KEPCHUP_LEVELS_PREFIXER = {'200': 'A'}

KEPCHUP_DISPLAY_CAR_NUMBER = True
KEPCHUP_DISPLAY_REGISTRATION_NOTE = True
KEPCHUP_DISPLAY_LAGAPEO = True
KEPCHUP_ALTERNATIVE_STEPS_NAMING = True
KEPCHUP_ABSENCES_RELATE_TO_ACTIVITIES = True
KEPCHUP_EXPLICIT_SESSION_DATES = True
KEPCHUP_DISPLAY_OVERLAP_HELP = False
KEPCHUP_CAN_DELETE_CHILD = False
KEPCHUP_USE_BLACKLISTS = True


# Registration steps
#########################################
KEPCHUP_ALTERNATIVE_ACTIVITIES_LABEL = u'Inscription'
KEPCHUP_ALTERNATIVE_CONFIRM_LABEL = u'Validation'
KEPCHUP_ALTERNATIVE_BILLING_LABEL = u'Confirmation'


STATIC_URL = '/hiver/static/'
FORCE_SCRIPT_NAME = '/hiver'
SESSION_COOKIE_PATH = FORCE_SCRIPT_NAME

CELERYBEAT_SCHEDULE['notify-absences'] = {
        'task': 'absences.tasks.notify_absences',
        'schedule': crontab(hour=19, minute=0),
}
CELERYBEAT_SCHEDULE['sync_from_master'] = {
        'task': 'profiles.tasks.sync_from_master',
        'schedule': crontab(minute='*/10'),
}

# Single Sign On
#########################################
KEPCHUP_USE_SSO = True

LOGIN_URL = '/hiver/client/'
LOGOUT_URL = '/hiver/account/logout/'