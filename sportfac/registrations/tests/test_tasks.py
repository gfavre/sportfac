from datetime import timedelta
from unittest import mock

from django.conf import settings
from django.core import mail
from django.core.mail import EmailMessage
from django.test import override_settings
from django.utils.timezone import now
from faker import Faker

from absences.models import Absence
from absences.tests.factories import SessionFactory
from backend.dynamic_preferences_registry import global_preferences_registry
from sportfac.utils import TenantTestCase

from ..models import Bill
from ..models import Registration
from ..tasks import cancel_expired_registrations
from ..tasks import create_future_absences_for_registration
from ..tasks import send_bill_confirmation
from ..tasks import send_bill_pdf_email
from ..tasks import send_invoice_pdf
from .factories import BillFactory
from .factories import RegistrationFactory


fake = Faker(locale="fr_CH")


class SendBillConfirmationTests(TenantTestCase):
    def setUp(self):
        self.bill = BillFactory()
        global_preferences = global_preferences_registry.manager()
        # dynamic_preferences caches values outside the DB transaction rollback, so this would
        # otherwise leak into every later test in the same process - restore it.
        original_iban = global_preferences["payment__IBAN"]
        original_address = global_preferences["payment__ADDRESS"]
        self.addCleanup(lambda: global_preferences.__setitem__("payment__IBAN", original_iban))
        self.addCleanup(lambda: global_preferences.__setitem__("payment__ADDRESS", original_address))
        global_preferences["payment__IBAN"] = "CH9300762011623852957"
        global_preferences["payment__ADDRESS"] = "Commune de Coppet\nGrand-Rue 34\n1296 Coppet"

    @override_settings(KEPCHUP_PAYMENT_METHOD="iban")
    @mock.patch("registrations.tasks.send_bill_pdf_email.delay")
    def test_announces_a_separate_invoice_email_for_wire_transfer(self, _mock_delay):
        # The actual invoice (with IBAN/QR details and the PDF) is sent separately by
        # send_bill_pdf_email - this immediate confirmation just announces it, so it never
        # has to wait behind that rate-limited task. send_bill_pdf_email is mocked here so
        # this test stays about the announcement text, not a real PDF generation.
        send_bill_confirmation(user_pk=str(self.bill.family.pk), bill_pk=self.bill.pk, tenant_pk=self.tenant.id)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("email séparé", mail.outbox[0].body)
        self.assertNotIn("IBAN", mail.outbox[0].body)

    @override_settings(KEPCHUP_PAYMENT_METHOD="datatrans")
    @mock.patch("registrations.tasks.send_bill_pdf_email.delay")
    def test_no_separate_invoice_email_announced_for_other_payment_methods(self, _mock_delay):
        send_bill_confirmation(user_pk=str(self.bill.family.pk), bill_pk=self.bill.pk, tenant_pk=self.tenant.id)
        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn("email séparé", mail.outbox[0].body)

    @mock.patch("registrations.tasks.send_bill_pdf_email.delay")
    def test_dispatches_the_pdf_email_for_wire_transfer(self, mock_delay):
        self.bill.payment_method = self.bill.METHODS.iban
        self.bill.save()

        send_bill_confirmation(user_pk=str(self.bill.family.pk), bill_pk=self.bill.pk, tenant_pk=self.tenant.id)

        mock_delay.assert_called_once_with(bill_pk=self.bill.pk, tenant_pk=self.tenant.id, language=mock.ANY)

    @mock.patch("registrations.tasks.send_bill_pdf_email.delay")
    def test_does_not_dispatch_the_pdf_email_for_other_payment_methods(self, mock_delay):
        self.bill.payment_method = self.bill.METHODS.datatrans
        self.bill.save()

        send_bill_confirmation(user_pk=str(self.bill.family.pk), bill_pk=self.bill.pk, tenant_pk=self.tenant.id)

        mock_delay.assert_not_called()


class SendBillPdfEmailTests(TenantTestCase):
    def setUp(self):
        self.bill = BillFactory()
        global_preferences = global_preferences_registry.manager()
        original_iban = global_preferences["payment__IBAN"]
        original_address = global_preferences["payment__ADDRESS"]
        self.addCleanup(lambda: global_preferences.__setitem__("payment__IBAN", original_iban))
        self.addCleanup(lambda: global_preferences.__setitem__("payment__ADDRESS", original_address))
        global_preferences["payment__IBAN"] = "CH9300762011623852957"
        global_preferences["payment__ADDRESS"] = "Commune de Coppet\nGrand-Rue 34\n1296 Coppet"

    def test_pdf_attached_and_iban_details_included_for_wire_transfer(self):
        self.bill.payment_method = self.bill.METHODS.iban
        self.bill.save()

        send_bill_pdf_email(bill_pk=self.bill.pk, tenant_pk=self.tenant.id)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(len(mail.outbox[0].attachments), 1)
        self.assertIn("IBAN: CH9300762011623852957", mail.outbox[0].body)
        self.assertIn(self.bill.billing_identifier, mail.outbox[0].body)

    def test_noop_for_other_payment_methods(self):
        self.bill.payment_method = self.bill.METHODS.datatrans
        self.bill.save()

        send_bill_pdf_email(bill_pk=self.bill.pk, tenant_pk=self.tenant.id)

        self.assertEqual(len(mail.outbox), 0)

    def test_unknown_bill_is_a_noop(self):
        send_bill_pdf_email(bill_pk=self.bill.pk + 1000000, tenant_pk=self.tenant.id)
        self.assertEqual(len(mail.outbox), 0)


class CreateFutureAbsencesForRegistrationTaskTests(TenantTestCase):
    def setUp(self):
        self.registration = RegistrationFactory()
        self.future_session = SessionFactory(course=self.registration.course, date=now().date() + timedelta(days=7))

    def test_creates_absences_for_the_registration(self):
        create_future_absences_for_registration(self.registration.pk)
        self.assertTrue(Absence.objects.filter(child=self.registration.child, session=self.future_session).exists())

    def test_unknown_registration_is_a_noop(self):
        # The task can run after the registration was deleted in the meantime - shouldn't raise.
        create_future_absences_for_registration(self.registration.pk + 1000000)
        self.assertFalse(Absence.objects.exists())


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
        mock_bill_filter.return_value.exclude.return_value = [mock_invoice]
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
        mock_bill_filter.return_value.exclude.return_value = [mock_invoice]
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
            created__lte=mock_expiration_time,
        )
        mock_registration_filter.assert_called_once_with(
            status=Registration.STATUS.waiting,
            modified__lte=mock_expiration_time,
        )
