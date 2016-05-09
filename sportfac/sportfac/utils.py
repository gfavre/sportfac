import csv, codecs, cStringIO
from datetime import date

from django.db import connection

from django_tenants.test.cases import TenantTestCase as BaseTenantTestCase
from django_tenants.test.client import TenantClient
from django_tenants.utils import get_tenant_model, get_tenant_domain_model

class excel_semicolon(csv.excel):
    delimiter = ';'

class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=excel_semicolon, encoding="utf-8", **kwds):
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

    def __init__(self, f, dialect=excel_semicolon, encoding="utf-8", **kwds):
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
        self.tenant, created = get_tenant_model().objects.get_or_create(
            schema_name='test',
            start_date=date(2015, 1, 1),
            end_date=date(2015, 12, 31),
            status='ready')
        self.tenant.create_schema(check_if_exists=True, verbosity=0)
        
        tenant_domain = 'test'
        self.domain, created = get_tenant_domain_model().objects.get_or_create(
            tenant=self.tenant, 
            domain=tenant_domain, 
            is_current=True)
        
        connection.set_tenant(self.tenant)
        self.client = TenantClient(self.tenant)