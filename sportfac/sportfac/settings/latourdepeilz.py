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
INSTALLED_APPS += [
    'anymail',  # integrates several transactional email service providers into Django
]

ANYMAIL = {
    "MAILGUN_API_KEY": env.str('MAILGUN_API_KEY'),
    "MAILGUN_SENDER_DOMAIN": env.str('MAILGUN_SENDER_DOMAIN')
}
#EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"



EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env('EMAIL_HOST', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')

# Absences
KEPCHUP_USE_ABSENCES = True

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


# Payment
KEPCHUP_NO_PAYMENT = False

# Misc
KEPCHUP_IMPORT_CHILDREN = False


CELERYBEAT_SCHEDULE['notify-absences'] = {
        'task': 'absences.tasks.notify_absences',
        'schedule': crontab(hour=04, minute=0),
}
