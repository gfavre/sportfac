from unittest import mock

from django.test import override_settings
from django.test.client import RequestFactory
from django.urls import reverse
from faker import Faker
from rest_framework.test import APIRequestFactory
from rest_framework.test import force_authenticate

from profiles.tests.factories import FamilyUserFactory
from registrations.tests.factories import BillFactory
from registrations.tests.factories import RegistrationFactory
from sportfac.utils import TenantTestCase
from wizard.tests.factories import WizardStepFactory

from ..models import PostfinanceTransaction
from ..postfinance import invoice_to_transaction
from ..views import NewPostfinanceTransactionView
from ..views import PostfinanceWebhookView
from ..views import WizardPaymentSuccessView


fake = Faker(locale="fr_CH")

# One of api.permissions.PostfinanceIPFilterPermission's hardcoded allowed IPs.
ALLOWED_POSTFINANCE_IP = "52.211.247.160"


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


def _mock_pf_response(state, payment_method_name="TWINT"):
    """Build a fake object mimicking what get_new_status() returns from the SDK."""
    pf_transaction = mock.Mock()
    pf_transaction.to_dict.return_value = {"state": state}
    pf_transaction.payment_connector_configuration.name = payment_method_name
    return state, pf_transaction


class PostfinanceWebhookViewTests(TenantTestCase):
    """
    Simulates PostFinance's webhook calling back with a positive or negative
    transaction state, and checks the app reacts in the right places: Bill/
    Registration status, the confirmation email trigger, and the two bugs that
    would otherwise blow up while reading back a successfully-paid registration
    (settings.KETCHUP_PAYMENT_METHOD typo, and PostfinanceTransaction.successful
    missing manager).
    """

    def setUp(self):
        super().setUp()
        self.api_factory = APIRequestFactory()
        self.registration = RegistrationFactory(course__price=50)
        self.invoice = BillFactory(registrations=[self.registration], payment_method="postfinance")
        self.pf_transaction = PostfinanceTransaction.objects.create(
            invoice=self.invoice,
            transaction_id=123456789,
            status=PostfinanceTransaction.STATUS.PENDING,
        )

    def _post_webhook(self, data, remote_addr=ALLOWED_POSTFINANCE_IP):
        request = self.api_factory.post("/postfinance/", data=data, format="json", REMOTE_ADDR=remote_addr)
        return PostfinanceWebhookView.as_view()(request)

    @override_settings(KEPCHUP_PAYMENT_METHOD="postfinance", POSTFINANCE_SPACE_ID=42)
    @mock.patch("registrations.models.Bill.send_confirmation")
    @mock.patch("payments.postfinance.get_new_status")
    def test_successful_payment_marks_bill_and_registrations_paid(self, mock_get_new_status, mock_send_confirmation):
        mock_get_new_status.return_value = _mock_pf_response(
            PostfinanceTransaction.STATUS.COMPLETED, payment_method_name="TWINT"
        )

        response = self._post_webhook({"entityId": self.pf_transaction.transaction_id, "spaceId": 42})

        self.assertEqual(response.status_code, 200)
        self.pf_transaction.refresh_from_db()
        self.assertEqual(self.pf_transaction.status, PostfinanceTransaction.STATUS.COMPLETED)
        self.invoice.refresh_from_db()
        self.assertTrue(self.invoice.is_paid)
        self.registration.refresh_from_db()
        self.assertTrue(self.registration.paid)
        mock_send_confirmation.assert_called_once()
        # Regression check for the two AttributeError bugs found while investigating
        # this flow: reading back a paid postfinance registration's payment method
        # must not blow up (settings typo + missing PostfinanceTransaction.successful).
        self.assertEqual(self.registration.payment_method, "TWINT")

    @override_settings(POSTFINANCE_SPACE_ID=42)
    @mock.patch("registrations.models.Bill.send_confirmation")
    @mock.patch("payments.postfinance.get_new_status")
    def test_failed_payment_leaves_bill_waiting_and_sends_no_confirmation(
        self, mock_get_new_status, mock_send_confirmation
    ):
        mock_get_new_status.return_value = _mock_pf_response(PostfinanceTransaction.STATUS.DECLINE)

        response = self._post_webhook({"entityId": self.pf_transaction.transaction_id, "spaceId": 42})

        self.assertEqual(response.status_code, 200)
        self.pf_transaction.refresh_from_db()
        self.assertEqual(self.pf_transaction.status, PostfinanceTransaction.STATUS.DECLINE)
        self.invoice.refresh_from_db()
        self.assertFalse(self.invoice.is_paid)
        self.registration.refresh_from_db()
        self.assertFalse(self.registration.paid)
        mock_send_confirmation.assert_not_called()

    @override_settings(POSTFINANCE_SPACE_ID=42)
    @mock.patch("registrations.models.Bill.send_confirmation")
    @mock.patch("payments.postfinance.get_new_status")
    def test_repeated_success_webhooks_send_confirmation_only_once(self, mock_get_new_status, mock_send_confirmation):
        """PostFinance redelivers the same webhook several times; only the first should email."""
        mock_get_new_status.return_value = _mock_pf_response(PostfinanceTransaction.STATUS.COMPLETED)

        for _ in range(3):
            response = self._post_webhook({"entityId": self.pf_transaction.transaction_id, "spaceId": 42})
            self.assertEqual(response.status_code, 200)

        mock_send_confirmation.assert_called_once()

    @override_settings(POSTFINANCE_SPACE_ID=42)
    def test_unknown_transaction_is_silently_accepted(self):
        """Montreux shares one webhook URL across two tenants - unmatched calls must not error."""
        response = self._post_webhook({"entityId": 999999999, "spaceId": 42})
        self.assertEqual(response.status_code, 200)

    def test_missing_entity_id_is_rejected(self):
        response = self._post_webhook({"spaceId": 42})
        self.assertEqual(response.status_code, 400)

    def test_missing_space_id_is_rejected(self):
        response = self._post_webhook({"entityId": self.pf_transaction.transaction_id})
        self.assertEqual(response.status_code, 400)

    @override_settings(POSTFINANCE_SPACE_ID=42)
    def test_wrong_space_id_is_rejected(self):
        response = self._post_webhook({"entityId": self.pf_transaction.transaction_id, "spaceId": 999})
        self.assertEqual(response.status_code, 400)

    def test_request_from_unallowed_ip_is_forbidden(self):
        response = self._post_webhook(
            {"entityId": self.pf_transaction.transaction_id, "spaceId": 42}, remote_addr="1.2.3.4"
        )
        self.assertEqual(response.status_code, 403)


class PostfinanceTransactionModelTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.invoice = BillFactory(payment_method="postfinance")
        self.pf_transaction = PostfinanceTransaction.objects.create(
            invoice=self.invoice,
            transaction_id=987654321,
            status=PostfinanceTransaction.STATUS.PENDING,
        )

    def test_successful_manager_returns_only_successful_statuses(self):
        for status in (
            PostfinanceTransaction.STATUS.AUTHORIZED,
            PostfinanceTransaction.STATUS.COMPLETED,
            PostfinanceTransaction.STATUS.FULFILL,
        ):
            self.pf_transaction.status = status
            self.pf_transaction.save(update_fields=["status"])
            self.assertIn(self.pf_transaction, PostfinanceTransaction.successful.all())

        for status in (
            PostfinanceTransaction.STATUS.PENDING,
            PostfinanceTransaction.STATUS.FAILED,
            PostfinanceTransaction.STATUS.DECLINE,
            PostfinanceTransaction.STATUS.VOIDED,
        ):
            self.pf_transaction.status = status
            self.pf_transaction.save(update_fields=["status"])
            self.assertNotIn(self.pf_transaction, PostfinanceTransaction.successful.all())

    @mock.patch("payments.postfinance.get_new_status")
    def test_update_status_stores_webhook_payload_and_payment_method(self, mock_get_new_status):
        mock_get_new_status.return_value = _mock_pf_response(
            PostfinanceTransaction.STATUS.COMPLETED, payment_method_name="VISA"
        )

        self.pf_transaction.update_status()

        self.assertEqual(self.pf_transaction.status, PostfinanceTransaction.STATUS.COMPLETED)
        self.assertEqual(self.pf_transaction.payment_method, "VISA")
        self.assertEqual(self.pf_transaction.webhook, {"state": PostfinanceTransaction.STATUS.COMPLETED})


class WizardPaymentSuccessViewTests(TenantTestCase):
    """
    The browser lands on this page as soon as PostFinance's own checkout widget
    decides the payment is done - before the async webhook has necessarily landed
    and actually flipped Bill.status. get_context_data must reflect that honestly
    via payment_confirmed rather than always asserting success.
    """

    def setUp(self):
        super().setUp()
        self.user = FamilyUserFactory()
        self.step = WizardStepFactory(slug="payment-success", display_in_navigation=True)

    def _get_context(self):
        request = RequestFactory().get("/")
        request.user = self.user
        view = WizardPaymentSuccessView()
        view.request = request
        view.kwargs = {"step_slug": "payment-success"}
        view.args = []
        with mock.patch.object(view, "get_step", return_value=self.step), mock.patch.object(
            view, "get_workflow"
        ) as mock_workflow:
            mock_workflow.return_value.get_visible_steps.return_value = [self.step]
            mock_workflow.return_value.get_next_step.return_value = None
            mock_workflow.return_value.get_previous_step.return_value = None
            return view.get_context_data()

    def test_payment_confirmed_true_once_bill_is_paid(self):
        BillFactory(family=self.user, status="paid")
        context = self._get_context()
        self.assertTrue(context["payment_confirmed"])

    def test_payment_confirmed_false_while_webhook_has_not_landed_yet(self):
        BillFactory(family=self.user, status="waiting")
        context = self._get_context()
        self.assertFalse(context["payment_confirmed"])

    def test_payment_confirmed_false_without_any_bill(self):
        context = self._get_context()
        self.assertFalse(context["payment_confirmed"])
