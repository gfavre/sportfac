from django.conf import settings
from tenant_schemas_celery.app import CeleryApp


# set the default Django settings module for the 'celery' program.
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sportfac.settings.local')

app = CeleryApp("sportfac")
# Set the key prefix for Redis
key_prefix = settings.CELERY_PREFIX

app.conf.task_default_queue = key_prefix + "_default"
app.conf.task_default_exchange = key_prefix + "_default"
app.conf.task_default_routing_key = key_prefix + "_default"

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object("django.conf:settings")
app.conf.broker_transport_options = {
    # This used to also carry "queue_options": {"bindings": [Queue(...)]} - not an
    # option kombu's Redis transport actually reads (that's AMQP/RabbitMQ-transport
    # doc territory), so it never did anything functional. What it *did* do: leave a
    # raw kombu.Queue instance sitting in app.conf, which every single control-command
    # reply (mingle, inspect active/reserved/stats, revoke, ...) tries to JSON-encode
    # on the way back to the caller - and always failed with EncodeError("Object of
    # type Queue is not JSON serializable"), silently, from the worker's side. Callers
    # just saw "No nodes replied within time constraint" with no indication why, since
    # the worker had already fully processed the request - it choked only on sending
    # the reply. key_prefix below is the actual (real, documented) tenant-isolation
    # mechanism and is unaffected by removing the dead "queue_options" key.
    "key_prefix": key_prefix,
}
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.on_after_configure.connect
def disable_dbtemplates_cache(sender, **kwargs):
    from dbtemplates.conf import settings as dbt_settings

    dbt_settings.DBTEMPLATES_USE_CACHE = False


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
