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
    def __init__(self, file_path, headers=None):
        self.file_path = file_path
        self.headers = headers
        self.file = open(self.file_path, 'w', newline='', encoding='utf-8')
        self.writer = csv.writer(self.file, dialect='excel')

    def write_header(self):
        if self.headers:
            self.writer.writerow(self.headers)

    def close(self):
        self.file.close()


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


def process_request_for_middleware(request, middleware_class):
    middleware = middleware_class("response")
    middleware.process_request(request)
    # return request


def add_middleware_to_response(request, middleware_class):
    middleware = middleware_class()
    middleware.process_response(request)
    return request
