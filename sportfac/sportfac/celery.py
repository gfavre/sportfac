from django.conf import settings

from kombu import Queue
from tenant_schemas_celery.app import CeleryApp


# set the default Django settings module for the 'celery' program.
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sportfac.settings.local')

app = CeleryApp("sportfac")
# Set the key prefix for Redis
key_prefix = settings.CELERY_PREFIX


# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object("django.conf:settings")
app.conf.broker_transport_options = {
    "queue_options": {
        "bindings": [Queue(key_prefix + "default")],
    },
    "key_prefix": key_prefix,
}
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
