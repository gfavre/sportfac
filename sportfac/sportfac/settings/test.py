from base import *

########## IN-MEMORY TEST DATABASE
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
     },
}
DEBUG = True
ALLOWED_HOSTS = list(ALLOWED_HOSTS) + ['test.com', 'tenant.test.com']