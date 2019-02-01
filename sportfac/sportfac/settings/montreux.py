# -*- coding: utf-8 -*-
"""Production settings and globals."""

from production import *

TEMPLATES[0]['DIRS'] = [
    normpath(join(SITE_ROOT, 'themes', 'montreux', 'templates')),
    normpath(join(SITE_ROOT, 'templates')),
]

STATICFILES_DIRS = (
    normpath(join(SITE_ROOT, 'themes', 'montreux', 'static')),
    normpath(join(SITE_ROOT, 'static')),
)


EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env('EMAIL_HOST', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')

KEPCHUP_USE_ABSENCES = True
KEPCHUP_IMPORT_CHILDREN = True
KEPCHUP_PREFILL_YEARS_WITH_TEACHERS = False
KEPCHUP_SEND_PRESENCE_LIST = True
KEPCHUP_SEND_COPY_CONTACT_MAIL_TO_ADMIN = True
KEPCHUP_NO_PAYMENT = False
KEPCHUP_NO_TERMS = False
KEPCHUP_CHILD_SCHOOL = True
KEPCHUP_FICHE_SALAIRE_MONTREUX = True
KEPCHUP_NO_SSF = True
KEPCHUP_ADDITIONAL_INSTRUCTOR_EMAIL_DOCUMENTS = ['pdf/infos-moniteurs-2018.pdf', 'pdf/GMS_2018-2019.pdf']
KEPCHUP_SPLASH_PAGE = True
KEPCHUP_ABSENCES_RELATE_TO_ACTIVITIES = True
KEPCHUP_CHILDREN_UNEDITABLE_FIELDS = ['first_name', 'last_name', 'birth_date']


# Registration steps
#########################################
KEPCHUP_ALTERNATIVE_ACTIVITIES_LABEL = u'Inscription'
KEPCHUP_ALTERNATIVE_CONFIRM_LABEL = u'Résumé'
KEPCHUP_ALTERNATIVE_BILLING_LABEL = u'Confirmation'


CELERYBEAT_SCHEDULE['notify-absences'] = {
        'task': 'absences.tasks.notify_absences',
        'schedule': crontab(hour=19, minute=0),
}
