from unittest import mock

from django.core import mail
from django.core.mail import EmailMessage

from backend.dynamic_preferences_registry import global_preferences_registry
from faker import Faker

from sportfac.utils import TenantTestCase

from ..models import Bill
from ..tasks import send_invoice_pdf
from .factories import BillFactory


fake = Faker(locale="fr_CH")


class SendInvoicePDFTests(TenantTestCase):
    def setUp(self):
        self.bill = BillFactory()
        self.accountant_email = fake.email()
        global_preferences = global_preferences_registry.manager()
        global_preferences["email__ACCOUNTANT_MAIL"] = self.accountant_email

    def test_email_is_sent(self):
        send_invoice_pdf(self.bill.id, self.tenant.id)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, [self.accountant_email])
        self.assertEqual(len(email.attachments), 1)
        self.assertTrue(len(email.subject) > 0)
        self.assertTrue(len(email.body) > 0)

    @mock.patch.object(EmailMessage, "attach_file")
    def test_generate_pdf(self, _attach_file):
        self.bill.pdf = None
        self.bill.save()
        with mock.patch.object(Bill, "generate_pdf") as generate_pdf:
            send_invoice_pdf(self.bill.id, self.tenant.id)
            generate_pdf.assert_called_once()
