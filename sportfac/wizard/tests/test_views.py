from django.test import RequestFactory

from profiles.tests.factories import FamilyUserFactory
from registrations.models import Bill
from registrations.models import Registration
from registrations.tests.factories import ChildFactory
from registrations.tests.factories import RegistrationFactory
from registrations.tests.factories import WaitingBillFactory
from registrations.tests.factories import WaitingRegistrationFactory
from sportfac.utils import TenantTestCase

from ..views import ActivitiesStepView


class GetRegistrationsTests(TenantTestCase):
    """Tests for BaseWizardStepView.get_registrations."""

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.user = FamilyUserFactory()
        self.child = ChildFactory(family=self.user)
        request = self.factory.get("/")
        request.user = self.user
        request.REGISTRATION_OPENED = True
        self.view = ActivitiesStepView()
        self.view.request = request
        self.view.kwargs = {"step_slug": "activities"}
        self.view.args = []

    def test_returns_waiting_registrations(self):
        reg = WaitingRegistrationFactory(child=self.child)
        registrations, invoice = self.view.get_registrations(self.user)
        self.assertIn(reg, registrations)
        self.assertIsNone(invoice)

    def test_returns_empty_when_no_registrations_no_invoice(self):
        registrations, invoice = self.view.get_registrations(self.user)
        self.assertFalse(registrations.exists())
        self.assertIsNone(invoice)

    def test_payment_timeout_returns_invoice_registrations(self):
        """After a payment timeout, registrations are in 'valid' status and a waiting invoice
        exists. get_registrations must find them so the wizard can redirect to payment."""
        reg = RegistrationFactory(child=self.child, status=Registration.STATUS.valid)
        invoice = WaitingBillFactory(family=self.user)
        reg.bill = invoice
        reg.save()

        registrations, returned_invoice = self.view.get_registrations(self.user)

        self.assertEqual(returned_invoice, invoice)
        self.assertIn(reg, registrations)

    def test_payment_timeout_ignores_paid_invoice(self):
        """A paid invoice must not be picked up — only waiting ones."""
        reg = RegistrationFactory(child=self.child, status=Registration.STATUS.valid)
        invoice = WaitingBillFactory(family=self.user, status=Bill.STATUS.paid)
        reg.bill = invoice
        reg.save()

        registrations, returned_invoice = self.view.get_registrations(self.user)

        self.assertIsNone(returned_invoice)
        self.assertFalse(registrations.exists())

    def test_waiting_registrations_take_precedence_over_invoice(self):
        """If waiting registrations exist alongside a waiting invoice (edge case),
        the waiting registrations must be returned, not the invoice's."""
        waiting_reg = WaitingRegistrationFactory(child=self.child)
        valid_reg = RegistrationFactory(child=self.child, status=Registration.STATUS.valid)
        invoice = WaitingBillFactory(family=self.user)
        valid_reg.bill = invoice
        valid_reg.save()

        registrations, returned_invoice = self.view.get_registrations(self.user)

        self.assertIn(waiting_reg, registrations)
        self.assertNotIn(valid_reg, registrations)
        self.assertIsNone(returned_invoice)
