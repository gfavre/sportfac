import codecs
import csv
from datetime import date
from io import StringIO

from django_tenants.test.cases import FastTenantTestCase as BaseTenantTestCase
from django_tenants.test.client import TenantClient


class ExcelSemicolon(csv.excel):
    delimiter = ";"


class ExcelWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=ExcelSemicolon, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()
        self.encoding = encoding

    def writerow(self, row):
        self.writer.writerow([s.encode(self.encoding, "ignore") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


class TenantTestCase(BaseTenantTestCase):
    @classmethod
    def setup_tenant(cls, tenant):
        tenant.start_date = date(2015, 1, 1)
        tenant.end_date = date(2015, 12, 31)
        tenant.status = "ready"
        tenant.create_schema()
        return tenant

    @classmethod
    def setup_domain(cls, domain):
        """
        Add any additional setting to the domain before it get saved. This is required if you have
        required fields.
        :param domain:
        :return:
        """
        domain.is_current = True
        return domain

    def setUp(self):
        super().setUp()
        self.tenant_client = TenantClient(self.tenant)


def add_middleware_to_request(request, middleware_class):
    middleware = middleware_class()
    middleware.process_request(request)
    return request


def add_middleware_to_response(request, middleware_class):
    middleware = middleware_class()
    middleware.process_response(request)
    return request
