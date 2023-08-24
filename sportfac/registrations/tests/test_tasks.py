from datetime import timedelta
from unittest import mock

from django.core import mail
from django.core.mail import EmailMessage
from django.test import override_settings
from django.utils.timezone import now

from backend.dynamic_preferences_registry import global_preferences_registry
from faker import Faker
from payments.models import PostfinanceTransaction
from payments.tests.factories import PostfinanceTransactionFactory

from sportfac.utils import TenantTestCase

from ..models import Bill, Registration
from ..tasks import cancel_expired_registrations, send_invoice_pdf
from .factories import BillFactory, RegistrationFactory


fake = Faker(locale="fr_CH")


class SendInvoicePDFTests(TenantTestCase):
    # noinspection PyAttributeOutsideInit
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


@override_settings(KEPCHUP_REGISTRATION_EXPIRE_MINUTES=5)
class CancelExpiredRegistrationsTests(TenantTestCase):
    # noinspection PyAttributeOutsideInit
    def setUp(self):
        self.expired_invoice = BillFactory()
        self.expired_registration = RegistrationFactory(
            status=Registration.STATUS.waiting, created=now() - timedelta(minutes=15), bill=self.expired_invoice
        )
        self.valid_invoice = BillFactory()
        self.valid_registration = RegistrationFactory(status=Registration.STATUS.waiting, bill=self.valid_invoice)

    def test_cancel_expired_registrations(self):
        cancel_expired_registrations()
        self.expired_registration.refresh_from_db()
        self.assertEqual(self.expired_registration.status, Registration.STATUS.canceled)

    def test_does_not_cancel_valid_registrations(self):
        cancel_expired_registrations()
        self.valid_registration.refresh_from_db()
        self.assertEqual(self.valid_registration.status, Registration.STATUS.waiting)

    def test_void_all_pf_transactions(self):
        transactions = PostfinanceTransactionFactory.create_batch(2, invoice=self.expired_registration.bill)
        with mock.patch.object(PostfinanceTransaction, "void") as void_method:
            cancel_expired_registrations()
            void_method.assert_called()
        for transaction in transactions:
            transaction.refresh_from_db()
            self.assertEqual(transaction.status, PostfinanceTransaction.STATUS.VOIDED)

    def do_not_void_valid_pf_transactions(self):
        self.expired_registration.delete()
