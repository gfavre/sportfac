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

KEPCHUP_USE_ABSENCES = True
KEPCHUP_SEND_PRESENCE_LIST = True
KEPCHUP_PREFILL_YEARS_WITH_TEACHERS = False
