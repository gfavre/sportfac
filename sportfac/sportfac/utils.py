import csv, codecs, cStringIO

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
    def setUp(self, *args, **kwargs):
        super(TenantTestCase, self).__init__(*args, **kwargs)
        self.tenant = get_tenant_model()(schema_name='test')
        self.client = TenantClient(self.tenant)