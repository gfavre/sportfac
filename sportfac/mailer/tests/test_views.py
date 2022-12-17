from django.test import RequestFactory

from sportfac.utils import TenantTestCase


class MailCreateViewTests(TenantTestCase):
    def setUp(self):
        self.factory = RequestFactory()
