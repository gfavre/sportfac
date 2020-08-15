"""Production settings and globals."""

from production import *

TEMPLATES[0]['DIRS'] = [
    normpath(join(SITE_ROOT, 'themes', 'nyon_prangins', 'templates')),
    normpath(join(SITE_ROOT, 'templates')),
]

STATICFILES_DIRS = (
    normpath(join(SITE_ROOT, 'themes', 'nyon_prangins', 'static')),
    normpath(join(SITE_ROOT, 'static')),
)

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env('EMAIL_HOST', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')

KEPCHUP_USE_ABSENCES = True
KEPCHUP_IMPORT_CHILDREN = False
KEPCHUP_USE_BUILDINGS = False
KEPCHUP_PREFILL_YEARS_WITH_TEACHERS = False
KEPCHUP_SEND_PRESENCE_LIST = True
KEPCHUP_SEND_COPY_CONTACT_MAIL_TO_ADMIN = True
KEPCHUP_NO_PAYMENT = True
KEPCHUP_NO_TERMS = False
KEPCHUP_NO_SSF = True
KEPCHUP_DISPLAY_NUMBER_OF_SESSIONS = False
KEPCHUP_REGISTER_ACCOUNTS_AT_ANY_TIME = True
KEPCHUP_NO_EXTRAS = True
KEPCHUP_EXPLICIT_SESSION_DATES = True
KEPCHUP_FICHE_SALAIRE_MONTREUX = True
KEPCHUP_ZIPCODE_RESTRICTION = [
    ['1277', 'Arnex-sur-Nyon'], ['1273', 'Arzier-Le Muids'], ['1269', 'Bassins'], ['1268', 'Begnins'],
    ['1279', 'Bogis-Bossey'], ['1277', 'Borex'], ['1195', 'Bursinel'], ['1183', 'Bursins'],
    ['1268', 'Burtigny'], ['1279', 'Chavannes-de-Bogis'], ['1290', 'Chavannes-des-Bois'],
    ['1275', u'Chéserex'], ['1267', 'Coinsins'], ['1291', 'Commugny'], ['1296', 'Coppet'],
    ['1299', u'Crans-près-Céligny'], ['1263', 'Crassier'], ['1266', 'Duillier'], ['1195', 'Dully'],
    ['1186', 'Essertines-sur-Rolle'], ['1260', 'Eysins'], ['1297', 'Founex'], ['1272', 'Genolier'],
    ['1182', 'Gilly'], ['1276', 'Gingins'], ['1271', 'Givrins'], ['1196', 'Gland'], ['1276', 'Grens'],
    ['1278', 'La Rippe'], ['1261', 'Le Vaud'], ['1261', 'Longirod'], ['1184', 'Luins'], ['1261', 'Marchissy'],
    ['1295', 'Mies'], ['1185', 'Mont-sur-Rolle'], ['1260', 'Nyon'], ['116', 'Perroy'], ['1197', 'Prangins'],
    ['1180', 'Rolle'], ['1264', 'Saint-Cergue'], ['1265', 'Saint-George'], ['1188', 'Signy-Avenex'],
    ['1274', 'Tannay'], ['1180', 'Tartegnin'], ['1270', u'Trélex'], ['1267', 'Vich'], ['1184', 'Vinzel']
]
