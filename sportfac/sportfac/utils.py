import csv, codecs, cStringIO
from datetime import date

from django.core.management import call_command
from django.db import connection
from django_tenants.test.cases import TenantTestCase as BaseTenantTestCase
from django_tenants.test.client import TenantClient
from django_tenants.utils import get_tenant_model, get_tenant_domain_model
from django.contrib.auth.models import Group

from backend import INSTRUCTORS_GROUP, MANAGERS_GROUP


class ExcelSemicolon(csv.excel):
    delimiter = ';'


class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """
    def __init__(self, f, dialect=ExcelSemicolon, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


class ExcelWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=ExcelSemicolon, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()
        self.encoding = encoding

    def writerow(self, row):
        self.writer.writerow([s.encode(self.encoding, 'ignore') for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode(self.encoding, 'ignore')
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


class TenantTestCase(BaseTenantTestCase):

    def setUp(self):
        self.sync_shared()
        grp, created = Group.objects.get_or_create(name=INSTRUCTORS_GROUP)
        grp, created = Group.objects.get_or_create(name=MANAGERS_GROUP)
        self.tenant, created = get_tenant_model().objects.get_or_create(
            schema_name='test',
            start_date=date(2015, 1, 1),
            end_date=date(2015, 12, 31),
            status='ready')
        self.tenant.create_schema(check_if_exists=True, verbosity=0)

        tenant_domain = 'testserver'
        self.domain, created = get_tenant_domain_model().objects.get_or_create(
            tenant=self.tenant,
            domain=tenant_domain,
            is_current=True)

        connection.set_tenant(self.tenant)
        self.tenant_client = TenantClient(self.tenant)

    def _fixture_teardown(self):
        # Allow TRUNCATE ... CASCADE and don't emit the post_migrate signal
        # when flushing only a subset of the apps
        for db_name in self._databases_names(include_mirrors=False):
            # Flush the database
            inhibit_post_migrate = (
                self.available_apps is not None or
                (   # Inhibit the post_migrate signal when using serialized
                    # rollback to avoid trying to recreate the serialized data.
                    self.serialized_rollback and
                    hasattr(connections[db_name], '_test_serialized_contents')
                )
            )
            call_command('flush', verbosity=0, interactive=False,
                         database=db_name, reset_sequences=False,
                         allow_cascade=True,
                         inhibit_post_migrate=inhibit_post_migrate)


def add_middleware_to_request(request, middleware_class):
    middleware = middleware_class()
    middleware.process_request(request)
    return request


def add_middleware_to_response(request, middleware_class):
    middleware = middleware_class()
    middleware.process_response(request)
    return request
