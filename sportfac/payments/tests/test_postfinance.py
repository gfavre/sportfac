from unittest import mock

from django.test.client import RequestFactory
from django.urls import reverse

from faker import Faker
from registrations.tests.factories import BillFactory, RegistrationFactory

from sportfac.utils import TenantTestCase

from ..postfinance import invoice_to_transaction


fake = Faker(locale="fr_CH")


class InvoiceToTransactionTests(TenantTestCase):
    def setUp(self) -> None:
        self.request = RequestFactory().get(reverse("wizard_billing"))
        self.amount = fake.pyint(1, 200)
        self.registration = RegistrationFactory(course__price=self.amount)
        self.invoice = BillFactory(registrations=[self.registration])

    @mock.patch("payments.postfinance.TransactionCreate", autospec=True)
    def test_invoice_to_transaction(self, mock_transaction_create):
        invoice_to_transaction(self.request, self.invoice)
        mock_transaction_create.assert_called_once()
        call_args = mock_transaction_create.call_args[1]
        self.assertIn("successUrl", call_args)
        self.assertTrue(call_args["successUrl"].startswith("http"))
        self.assertTrue(call_args["successUrl"].endswith(reverse("wizard_payment_success")))
        self.assertIn("failedUrl", call_args)
        self.assertTrue(call_args["failedUrl"].startswith("http"))
        self.assertTrue(call_args["failedUrl"].endswith(reverse("wizard_billing")))
        self.assertIn("invoiceMerchantReference", call_args)
        self.assertEqual(call_args["invoiceMerchantReference"], self.invoice.billing_identifier)
        self.assertIn("line_items", call_args)
        self.assertEqual(len(call_args["line_items"]), 1)
        self.assertEqual(call_args["line_items"][0].amount_including_tax, self.amount)
