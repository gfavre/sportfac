from unittest import mock

from django.test.client import RequestFactory
from django.urls import reverse
from faker import Faker
from rest_framework.test import APIRequestFactory
from rest_framework.test import force_authenticate

from profiles.tests.factories import FamilyUserFactory
from registrations.tests.factories import BillFactory
from registrations.tests.factories import RegistrationFactory
from sportfac.utils import TenantTestCase

from ..postfinance import invoice_to_transaction
from ..views import NewPostfinanceTransactionView


fake = Faker(locale="fr_CH")


class InvoiceToTransactionTests(TenantTestCase):
    def setUp(self) -> None:
        self.request = RequestFactory().get(reverse("wizard:step", kwargs={"step_slug": "payment"}))
        self.amount = fake.pyint(1, 200)
        self.registration = RegistrationFactory(course__price=self.amount)
        self.invoice = BillFactory(registrations=[self.registration])

    @mock.patch("payments.postfinance.TransactionCreate", autospec=True)
    def test_invoice_to_transaction(self, mock_transaction_create):
        invoice_to_transaction(self.request, self.invoice)
        mock_transaction_create.assert_called_once()
        call_args = mock_transaction_create.call_args[1]
        self.assertIn("success_url", call_args)
        self.assertTrue(call_args["success_url"].startswith("http"))
        self.assertTrue(
            call_args["success_url"].endswith(reverse("wizard:step", kwargs={"step_slug": "payment-success"}))
        )
        self.assertIn("failed_url", call_args)
        self.assertTrue(call_args["failed_url"].startswith("http"))
        self.assertTrue(
            call_args["failed_url"].endswith(reverse("wizard:step", kwargs={"step_slug": "payment-failure"}))
        )
        self.assertIn("invoice_merchant_reference", call_args)
        self.assertEqual(call_args["invoice_merchant_reference"], self.invoice.billing_identifier)
        self.assertIn("line_items", call_args)
        self.assertEqual(len(call_args["line_items"]), 1)
        self.assertEqual(call_args["line_items"][0].amount_including_tax, self.amount)


class InvoiceToTransactionFailUrlTests(TenantTestCase):
    """Tests for the fail_url parameter of invoice_to_transaction (else branch)."""

    def setUp(self):
        # Use a generic path that falls into the else branch (not wizard/backend)
        self.request = RequestFactory().get("/registrations/billing/")
        self.registration = RegistrationFactory()
        self.invoice = BillFactory(registrations=[self.registration])

    @mock.patch("payments.postfinance.TransactionCreate", autospec=True)
    def test_explicit_fail_url_is_used(self, mock_transaction_create):
        """When fail_url is provided it must be used as failed_url, not the request path."""
        explicit_fail_url = "https://example.com/pay/123/"
        invoice_to_transaction(self.request, self.invoice, fail_url=explicit_fail_url)
        call_args = mock_transaction_create.call_args[1]
        self.assertEqual(call_args["failed_url"], explicit_fail_url)

    @mock.patch("payments.postfinance.TransactionCreate", autospec=True)
    def test_fail_url_falls_back_to_request_path(self, mock_transaction_create):
        """Without fail_url, failed_url must end with the request's own path."""
        invoice_to_transaction(self.request, self.invoice)
        call_args = mock_transaction_create.call_args[1]
        self.assertTrue(call_args["failed_url"].endswith(self.request.get_full_path()))


class NewPostfinanceTransactionViewTests(TenantTestCase):
    """Tests for NewPostfinanceTransactionView — verifies fail_url is forwarded."""

    def setUp(self):
        super().setUp()
        self.api_factory = APIRequestFactory()
        self.user = FamilyUserFactory()
        self.invoice = BillFactory(family=self.user)

    @mock.patch("payments.views.get_postfinance_transaction")
    def test_fail_url_from_post_data_is_passed_to_get_transaction(self, mock_get_transaction):
        """fail_url sent in the POST body must be forwarded to get_postfinance_transaction."""
        mock_get_transaction.return_value.payment_page_url = "https://checkout.postfinance.ch/script.js"
        fail_url = "https://example.com/current-page/"

        request = self.api_factory.post(
            f"/postfinance/new-transaction/{self.invoice.id}/",
            data={"fail_url": fail_url},
            format="json",
        )
        force_authenticate(request, user=self.user)

        response = NewPostfinanceTransactionView.as_view()(request, invoice_id=self.invoice.id)

        self.assertEqual(response.status_code, 200)
        mock_get_transaction.assert_called_once_with(mock.ANY, self.invoice, fail_url=fail_url)

    @mock.patch("payments.views.get_postfinance_transaction")
    def test_missing_fail_url_passes_none(self, mock_get_transaction):
        """If no fail_url in POST body, get_postfinance_transaction receives fail_url=None."""
        mock_get_transaction.return_value.payment_page_url = "https://checkout.postfinance.ch/script.js"

        request = self.api_factory.post(
            f"/postfinance/new-transaction/{self.invoice.id}/",
            data={},
            format="json",
        )
        force_authenticate(request, user=self.user)

        NewPostfinanceTransactionView.as_view()(request, invoice_id=self.invoice.id)

        mock_get_transaction.assert_called_once_with(mock.ANY, self.invoice, fail_url=None)
