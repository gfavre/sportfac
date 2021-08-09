# -*- coding:utf-8 -*-
"""Production settings and globals."""
from production import *

TEMPLATES[0]['DIRS'] = [
    normpath(join(SITE_ROOT, 'themes', 'latourdepeilz', 'templates')),
    normpath(join(SITE_ROOT, 'templates')),
]

STATICFILES_DIRS = (
    normpath(join(SITE_ROOT, 'themes', 'latourdepeilz', 'static')),
    normpath(join(SITE_ROOT, 'static')),
)

# Absences
KEPCHUP_USE_ABSENCES = True
KEPCHUP_EXPLICIT_SESSION_DATES = True

# Activities
KEPCHUP_ENABLE_ALLOCATION_ACCOUNTS = True
KEPCHUP_ACTIVITIES_CAN_REGISTER_SAME_ACTIVITY_TWICE = True


# Accounts
KEPCHUP_REGISTER_ACCOUNTS_AT_ANY_TIME = True

# Children
KEPCHUP_EMERGENCY_NUMBER_MANDATORY = True

# Email
#########################################
KEPCHUP_SEND_PRESENCE_LIST = True
KEPCHUP_SEND_COPY_CONTACT_MAIL_TO_ADMIN = True

# Registration
KEPCHUP_CALENDAR_HIDDEN_DAYS = []
KEPCHUP_ACTIVITIES_CAN_REGISTER_SAME_ACTIVITY_TWICE = True
KEPCHUP_INSTRUCTORS_CAN_REMOVE_REGISTRATIONS = True
KEPCHUP_ALTERNATIVE_STEPS_NAMING = True
KEPCHUP_ALTERNATIVE_ABOUT_LABEL = None
KEPCHUP_ALTERNATIVE_CHILDREN_LABEL = None
KEPCHUP_ALTERNATIVE_ACTIVITIES_LABEL = u'Prestations'
KEPCHUP_ALTERNATIVE_CONFIRM_LABEL = u'Récapitulation'
KEPCHUP_ALTERNATIVE_BILLING_LABEL = None
KEPCHUP_LIMIT_BY_AGE = True
KEPCHUP_LIMIT_BY_SCHOOL_YEAR = not KEPCHUP_LIMIT_BY_AGE
KEPCHUP_SCHOOL_YEAR_MANDATORY = True

# Payment
#########################################
KEPCHUP_NO_PAYMENT = False
KEPCHUP_PAYMENT_METHOD = 'datatrans'
KEPCHUP_USE_DIFFERENTIATED_PRICES = True
KEPCHUP_LOCAL_ZIPCODES = ['1814']

# Misc
KEPCHUP_IMPORT_CHILDREN = False
KEPCHUP_ENABLE_TEACHER_MANAGEMENT = False

CELERYBEAT_SCHEDULE['notify-absences'] = {
        'task': 'absences.tasks.notify_absences',
        'schedule': crontab(hour=04, minute=0),
}
