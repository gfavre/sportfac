from unittest import mock

from django.test import RequestFactory
from django.urls import reverse

from profiles.tests.factories import FamilyUserFactory
from registrations.models import Bill
from registrations.models import Registration
from registrations.tests.factories import ChildFactory
from registrations.tests.factories import RegistrationFactory
from registrations.tests.factories import WaitingBillFactory
from registrations.tests.factories import WaitingRegistrationFactory
from sportfac.utils import TenantTestCase

from ..tests.factories import WizardStepFactory
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


def _make_view(user, step_slug="activities"):
    factory = RequestFactory()
    request = factory.get("/")
    request.user = user
    request.REGISTRATION_OPENED = True
    view = ActivitiesStepView()
    view.request = request
    view.kwargs = {"step_slug": step_slug}
    view.args = []
    return view


class GetRegistrationContextTests(TenantTestCase):
    """Tests for BaseWizardStepView.get_registration_context robustness."""

    def setUp(self):
        super().setUp()
        self.user = FamilyUserFactory()
        self.view = _make_view(self.user)

    def test_none_registrations_does_not_crash(self):
        """get_registrations returning None must not crash get_registration_context."""
        with mock.patch.object(self.view, "get_registrations", return_value=(None, None)):
            context = self.view.get_registration_context()
        self.assertFalse(context["has_registrations"])

    def test_none_registrations_yields_empty_queryset_in_context(self):
        """registrations key in context must be an iterable even when get_registrations returns None."""
        with mock.patch.object(self.view, "get_registrations", return_value=(None, None)):
            context = self.view.get_registration_context()
        list(context["registrations"])  # must not raise


class DispatchRedirectTests(TenantTestCase):
    """Tests for BaseWizardStepView.dispatch redirect logic."""

    def setUp(self):
        super().setUp()
        self.user = FamilyUserFactory()
        self.step = WizardStepFactory(slug="activities", display_in_navigation=True)
        self.view = _make_view(self.user)

    def _dispatch_with_all_steps_not_ready(self, visible_steps):
        not_ready = mock.MagicMock()
        not_ready.is_ready.return_value = False
        with mock.patch("wizard.views.get_step_handler", return_value=not_ready):
            with mock.patch.object(self.view, "get_step", return_value=self.step):
                with mock.patch.object(self.view, "get_workflow") as mock_wf:
                    mock_wf.return_value.get_visible_steps.return_value = visible_steps
                    return self.view.dispatch(self.view.request)

    def test_redirects_to_entry_point_when_no_step_is_ready(self):
        """If every visible step is not ready, fall back to the wizard entry point."""
        response = self._dispatch_with_all_steps_not_ready([self.step])
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("wizard:entry_point"))

    def test_redirects_to_entry_point_when_no_visible_steps(self):
        """Same fallback when the visible step list is empty."""
        response = self._dispatch_with_all_steps_not_ready([])
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("wizard:entry_point"))

    def test_redirects_to_last_ready_visible_step(self):
        """When the current step is not ready, redirect to the last ready visible step."""
        ready_step = WizardStepFactory(slug="children", display_in_navigation=True)

        def handler_factory(step, context):
            h = mock.MagicMock()
            h.is_ready.return_value = step.slug == "children"
            return h

        with mock.patch("wizard.views.get_step_handler", side_effect=handler_factory):
            with mock.patch.object(self.view, "get_step", return_value=self.step):
                with mock.patch.object(self.view, "get_workflow") as mock_wf:
                    mock_wf.return_value.get_visible_steps.return_value = [ready_step, self.step]
                    response = self.view.dispatch(self.view.request)

        self.assertEqual(response.status_code, 302)
        self.assertIn("children", response["Location"])
