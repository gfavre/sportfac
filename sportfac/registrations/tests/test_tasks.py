from datetime import timedelta
from unittest import mock

from django.conf import settings
from django.core import mail
from django.core.mail import EmailMessage
from django.utils.timezone import now

from backend.dynamic_preferences_registry import global_preferences_registry
from faker import Faker

from sportfac.utils import TenantTestCase

from ..models import Bill, Registration
from ..tasks import cancel_expired_registrations, send_invoice_pdf
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


class CancelExpiredRegistrationsTest(TenantTestCase):
    def setUp(self):
        # Create mocks for tenant switching
        self.tenant_mock = mock.MagicMock()

    @mock.patch("registrations.tasks.Registration.objects.filter")
    @mock.patch("registrations.tasks.Bill.objects.filter")
    @mock.patch("registrations.tasks.connection.set_tenant")
    @mock.patch("registrations.tasks.Domain.objects.filter")
    def test_cancel_expired_registrations_success(
        self, mock_domain_filter, mock_set_tenant, mock_bill_filter, mock_registration_filter
    ):
        """Test that expired registrations and invoices are correctly canceled."""
        # Set up settings to allow registration expiration
        settings.KEPCHUP_REGISTRATION_EXPIRE_MINUTES = 60
        settings.KEPCHUP_ENABLE_WAITING_LISTS = True

        # Mock current domain to get the tenant
        mock_domain_filter.return_value.first.return_value.tenant = self.tenant_mock

        # Mock expired invoices and registrations
        mock_invoice = mock.MagicMock()
        mock_registration = mock.MagicMock()
        mock_course = mock.MagicMock()
        mock_invoice.registrations.all.return_value = [mock_registration]
        mock_registration.course = mock_course

        # Mock queryset returns
        mock_bill_filter.return_value = [mock_invoice]
        mock_registration_filter.return_value = [mock_registration]

        # Call the task
        cancel_expired_registrations()

        # Assertions
        mock_set_tenant.assert_called_once_with(self.tenant_mock)
        mock_invoice.cancel.assert_called_once()  # Invoice should be canceled
        mock_registration.cancel.assert_called_once_with(reason=Registration.REASON.expired)
        mock_course.send_places_available_reminder.assert_called_once()

    @mock.patch("registrations.tasks.settings")
    def test_cancel_expired_registrations_no_expire_minutes(self, mock_settings):
        """Test early exit when KEPCHUP_REGISTRATION_EXPIRE_MINUTES is not set."""
        # Set the setting to None (early exit condition)
        mock_settings.KEPCHUP_REGISTRATION_EXPIRE_MINUTES = None

        # Call the task
        result = cancel_expired_registrations()

        # Assert that nothing was processed
        self.assertIsNone(result)

    @mock.patch("registrations.tasks.Registration.objects.filter")
    @mock.patch("registrations.tasks.Bill.objects.filter")
    @mock.patch("registrations.tasks.connection.set_tenant")
    @mock.patch("registrations.tasks.Domain.objects.filter")
    def test_cancel_expired_registrations_no_waiting_list(
        self, mock_domain_filter, mock_set_tenant, mock_bill_filter, mock_registration_filter
    ):
        """Test that expired registrations are canceled but no reminders are sent when KEPCHUP_WAITING_LIST is False."""
        # Set up settings to allow registration expiration but no waiting list
        settings.KEPCHUP_REGISTRATION_EXPIRE_MINUTES = 60
        settings.KEPCHUP_ENABLE_WAITING_LISTS = False

        # Mock current domain to get the tenant
        mock_domain_filter.return_value.first.return_value.tenant = self.tenant_mock

        # Mock expired invoices and registrations
        mock_invoice = mock.MagicMock()
        mock_registration = mock.MagicMock()
        mock_course = mock.MagicMock()
        mock_invoice.registrations.all.return_value = [mock_registration]
        mock_registration.course = mock_course

        # Mock queryset returns
        mock_bill_filter.return_value = [mock_invoice]
        mock_registration_filter.return_value = [mock_registration]

        # Call the task
        cancel_expired_registrations()

        # Assertions
        mock_set_tenant.assert_called_once_with(self.tenant_mock)
        mock_invoice.cancel.assert_called_once()  # Invoice should be canceled
        mock_registration.cancel.assert_called_once_with(reason=Registration.REASON.expired)
        mock_course.send_places_available_reminder.assert_not_called()

    @mock.patch("registrations.tasks.now")
    @mock.patch("registrations.tasks.Registration.objects.filter")
    @mock.patch("registrations.tasks.Bill.objects.filter")
    @mock.patch("registrations.tasks.connection.set_tenant")
    @mock.patch("registrations.tasks.Domain.objects.filter")
    def test_cancel_expired_registrations_time_filtering(
        self, mock_domain_filter, mock_set_tenant, mock_bill_filter, mock_registration_filter, mock_now
    ):
        """Test that only registrations and invoices older than the expiration time are canceled."""
        # Set up settings to allow registration expiration
        settings.KEPCHUP_REGISTRATION_EXPIRE_MINUTES = 60
        mock_current_time = now()
        mock_expiration_time = mock_current_time - timedelta(minutes=60)

        # Set up mock for `now`
        mock_now.return_value = mock_current_time

        # Mock current domain to get the tenant
        mock_domain_filter.return_value.first.return_value.tenant = self.tenant_mock

        # Call the task
        cancel_expired_registrations()

        # Ensure the time filter is correct
        mock_bill_filter.assert_called_once_with(
            status=Bill.STATUS.waiting,
            modified__lte=mock_expiration_time,
        )
        mock_registration_filter.assert_called_once_with(
            status=Registration.STATUS.waiting,
            modified__lte=mock_expiration_time,
        )
