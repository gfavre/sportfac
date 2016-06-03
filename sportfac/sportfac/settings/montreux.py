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
RAVEN_CONFIG = {
    'dsn': 'https://fbd4129c4d7f49d9b1ae50f662cd2261:a3205969b1b9409cbcef3a6bcf06ff63@sentry.evoe.wine/3',
}

KEPCHUP_USE_ABSENCES = True
