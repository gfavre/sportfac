from unittest import mock

from django.contrib.auth.models import AnonymousUser
from django.db import connection
from django.http import Http404
from django.test import RequestFactory
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from activities.tests.factories import CourseFactory
from profiles.tests.factories import FamilyUserFactory
from sportfac.utils import TenantTestCase as TestCase

from ..models import Registration
from ..views.user import BillDetailView
from ..views.user import BillingView
from ..views.user import BillPdfView
from ..views.user import ChildrenListView
from ..views.user import SummaryView
from ..views.wizard import WizardConfirmationStepView
from .factories import BillFactory
from .factories import ChildFactory
from .factories import ExtraInfoFactory
from .factories import RegistrationFactory


class ChildrenListViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = ChildrenListView.as_view()
        self.url = reverse("registrations:registrations_children")
        self.user = FamilyUserFactory()
        self.child = ChildFactory(family=self.user)
        self.request = self.factory.get(self.url)
        self.request.user = self.user

    def test_access_forbidden_if_not_logged_in(self):
        self.request.user = AnonymousUser()
        response = self.view(self.request)
        response.client = self.client
        self.assertRedirects(response, reverse("profiles:auth_login") + "?next=" + self.url)

    def test_only_own_children_in_queryset(self):
        ChildFactory.create_batch(5)
        response = self.view(self.request)
        qs = response.context_data["object_list"]
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first(), self.child)


class BillingViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = BillingView.as_view()
        self.url = reverse("registrations:registrations_billing")
        self.user = FamilyUserFactory()
        self.invoice = BillFactory(family=self.user)
        self.request = self.factory.get(self.url)
        self.request.user = self.user

    def test_access_forbidden_if_not_logged_in(self):
        self.request.user = AnonymousUser()
        response = self.view(self.request)
        response.client = self.client
        self.assertRedirects(response, reverse("profiles:auth_login") + "?next=" + self.url)

    def test_only_own_bills_in_queryset(self):
        BillFactory.create_batch(5)
        response = self.view(self.request)
        qs = response.context_data["object_list"]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first(), self.invoice)


class BillDetailViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = BillDetailView.as_view()
        self.user = FamilyUserFactory()
        self.invoice = BillFactory(family=self.user)
        self.url = self.invoice.get_absolute_url()
        self.request = self.factory.get(self.url)
        self.request.user = self.user

    def test_access_forbidden_if_not_logged_in(self):
        self.request.user = AnonymousUser()
        response = self.view(self.request)
        response.client = self.client
        self.assertRedirects(response, reverse("profiles:auth_login") + "?next=" + self.url)

    def test_user_cannot_access_other_bills(self):
        invoice_2 = BillFactory()
        request = self.factory.get(invoice_2.get_absolute_url())
        request.user = self.user
        with self.assertRaises(Http404):
            self.view(request, pk=invoice_2.pk)

    def test_user_can_access_own_bills(self):
        response = self.view(self.request, pk=self.invoice.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data["object"], self.invoice)

    @override_settings(KEPCHUP_PRICING_MODE="simple", KEPCHUP_NO_PAYMENT=False)
    def test_shows_the_stored_price_not_a_live_recomputation(self):
        # Regression test: the price cell used to call registration.get_price_category()
        # live at render time instead of trusting the stored, already-billed price - so an
        # invoice could silently display a different amount than what was actually charged
        # (and than Bill.total, which sums the stored price), if the course's prices or the
        # family's sibling order changed after the registration was created.
        with override_settings(KEPCHUP_EXPLICIT_SESSION_DATES=False):
            course = CourseFactory(price=180)
        child = ChildFactory(family=self.user)
        registration = RegistrationFactory(course=course, child=child, price=250)
        invoice = BillFactory(family=self.user, registrations=[registration])

        request = self.factory.get(invoice.get_absolute_url())
        request.user = self.user
        response = self.view(request, pk=invoice.pk)
        response.render()

        self.assertIn(b"CHF 250.-", response.content)
        self.assertNotIn(b"CHF 180.-", response.content)

    @override_settings(KEPCHUP_PRICING_MODE="simple", KEPCHUP_NO_PAYMENT=False)
    def test_paid_bill_still_shows_the_total_amount(self):
        # Regression test: billing_partial.html (which carries the total-amount line)
        # used to be skipped entirely once a bill was marked paid - so a paid invoice's
        # detail page/PDF showed the list of registrations but never the total that was
        # actually billed.
        with override_settings(KEPCHUP_EXPLICIT_SESSION_DATES=False):
            course = CourseFactory(price=250)
        child = ChildFactory(family=self.user)
        registration = RegistrationFactory(course=course, child=child, price=250)
        invoice = BillFactory(family=self.user, registrations=[registration], payment_method="iban")
        invoice.close()

        request = self.factory.get(invoice.get_absolute_url())
        request.user = self.user
        response = self.view(request, pk=invoice.pk)
        response.render()

        self.assertIn(b"CHF 250.-", response.content)


class BillPdfViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = BillPdfView.as_view()
        self.user = FamilyUserFactory()
        self.invoice = BillFactory(family=self.user, payment_method="external", pdf=None)
        self.url = self.invoice.get_pdf_url()
        self.request = self.factory.get(self.url)
        self.request.user = self.user

    def test_access_forbidden_if_not_logged_in(self):
        self.request.user = AnonymousUser()
        response = self.view(self.request, pk=self.invoice.pk)
        response.client = self.client
        self.assertRedirects(response, reverse("profiles:auth_login") + "?next=" + self.url)

    def test_user_cannot_access_other_bills(self):
        invoice_2 = BillFactory()
        request = self.factory.get(invoice_2.get_pdf_url())
        request.user = self.user
        with self.assertRaises(Http404):
            self.view(request, pk=invoice_2.pk)

    def test_first_request_triggers_generation_and_returns_pending(self):
        self.assertFalse(self.invoice.pdf)
        response = self.view(self.request, pk=self.invoice.pk)
        self.assertEqual(response.status_code, 202)
        self.invoice.refresh_from_db()
        # CELERY_ALWAYS_EAGER runs the generation task synchronously in tests.
        self.assertTrue(self.invoice.pdf)

    def test_second_request_serves_the_generated_pdf(self):
        self.view(self.request, pk=self.invoice.pk)  # triggers (eager) generation
        second_request = self.factory.get(self.url)
        second_request.user = self.user
        response = self.view(second_request, pk=self.invoice.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")


class SummaryViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = SummaryView.as_view()
        self.url = reverse("registrations:registrations_registered_activities")
        self.user = FamilyUserFactory()
        self.child = ChildFactory(family=self.user)
        self.registration = RegistrationFactory(child=self.child, status="confirmed")
        self.request = self.factory.get(self.url)
        self.request.user = self.user

    def test_access_forbidden_if_not_logged_in(self):
        self.request.user = AnonymousUser()
        response = self.view(self.request)
        response.client = self.client
        self.assertRedirects(response, reverse("profiles:auth_login") + "?next=" + self.url)

    def test_own_registrations_in_context(self):
        RegistrationFactory.create_batch(5, status="confirmed")
        response = self.view(self.request)
        self.assertEqual(response.status_code, 200)
        self.assertIn("registered_list", response.context_data)
        qs = response.context_data["registered_list"]
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first(), self.registration)


class WizardConfirmationStepViewRowSpanTests(TestCase):
    # Regression test: row_span used to call reg.extra_infos.count(), bypassing the
    # extra_infos prefetch already done by get_registrations() and issuing one query per
    # registration on every load of the wizard's confirmation page.
    def setUp(self):
        super().setUp()
        self.user = FamilyUserFactory()
        self.child = ChildFactory(family=self.user)
        request = RequestFactory().get("/")
        request.user = self.user
        self.view = WizardConfirmationStepView()
        self.view.request = request
        self.view.kwargs = {}
        self.view.args = []
        # Only the workflow/step bookkeeping (irrelevant here) is stubbed out - the
        # registration/extra_infos fetching (what we're testing) runs for real.
        self.view.get_step = mock.MagicMock()
        self.view.get_workflow = mock.MagicMock()
        self.view.get_workflow.return_value.get_visible_steps.return_value = []
        self.view.get_next_step = mock.MagicMock(return_value=None)
        self.view.get_previous_step = mock.MagicMock(return_value=None)
        self.view.get_success_url = mock.MagicMock(return_value="/")

    def test_row_span_counts_extra_infos_without_extra_queries(self):
        # Registration count is kept constant across both measurements so the comparison
        # isolates the extra_infos count specifically, rather than an unrelated, pre-existing
        # per-registration query in BaseWizardStepView.get_registration_context().
        registration = RegistrationFactory(child=self.child, status=Registration.STATUS.waiting, price=10)
        ExtraInfoFactory.create_batch(3, registration=registration)

        with CaptureQueriesContext(connection) as few_queries:
            context = self.view.get_context_data()
        self.assertEqual(context["registrations"][0].row_span, 4)

        ExtraInfoFactory.create_batch(7, registration=registration)
        self.view._registration_context = None  # bust BaseWizardStepView's memoized context

        with CaptureQueriesContext(connection) as many_queries:
            context = self.view.get_context_data()
        self.assertEqual(context["registrations"][0].row_span, 11)

        self.assertEqual(len(few_queries.captured_queries), len(many_queries.captured_queries))
