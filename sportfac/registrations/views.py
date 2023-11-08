import datetime
import json
import logging

from django.conf import settings
from django.contrib import messages
from django.db import IntegrityError
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.generic import DeleteView, DetailView, FormView, ListView, TemplateView

import requests
from appointments.models import Appointment
from backend.dynamic_preferences_registry import global_preferences_registry
from braces.views import LoginRequiredMixin, UserPassesTestMixin
from postfinancecheckout.rest import ApiException
from profiles.forms import AcceptTermsForm
from profiles.models import School
from sentry_sdk import capture_exception

from sportfac.views import NotReachableException, WizardMixin

from .forms import EmptyForm
from .models import Bill, Child, Registration


logger = logging.getLogger(__name__)


@method_decorator(never_cache, name="dispatch")
class PaymentMixin:
    def get_transaction(self, invoice):
        if settings.KEPCHUP_PAYMENT_METHOD == "datatrans":
            from payments.datatrans import get_transaction

            try:
                transaction = get_transaction(self.request, invoice)
            except requests.exceptions.RequestException:
                transaction = None
            return transaction

        if settings.KEPCHUP_PAYMENT_METHOD == "postfinance":
            from payments.postfinance import get_transaction

            try:
                transaction = get_transaction(self.request, invoice)
            except requests.exceptions.RequestException:
                transaction = None
            except ApiException as exc:
                capture_exception(exc)
                logger.error("Postfinance API error: %s", exc)
                transaction = None
            return transaction
        return None

    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


class BillMixin:
    def get_context_data(self, **kwargs):
        # noinspection PyUnresolvedReferences
        context = super().get_context_data(**kwargs)
        preferences = global_preferences_registry.manager()
        offset_days = preferences["payment__DELAY_DAYS"]
        # noinspection PyUnresolvedReferences
        if hasattr(self, "object"):
            base_date = self.object.created  # self.request.REGISTRATION_END
        else:
            base_date = now()
        context["delay"] = base_date + datetime.timedelta(days=offset_days)
        context["iban"] = preferences["payment__IBAN"]
        context["address"] = preferences["payment__ADDRESS"]
        context["place"] = preferences["payment__PLACE"]

        return context


class BillingView(LoginRequiredMixin, BillMixin, ListView):
    template_name = "registrations/billing.html"

    def get_queryset(self):
        return Bill.objects.filter(family=self.request.user).order_by("created")


class BillDetailView(LoginRequiredMixin, PaymentMixin, BillMixin, DetailView):
    """
    Display the bill (family user view)
    """

    template_name = "registrations/bill-detail.html"

    def get_queryset(self):
        if self.request.user.is_manager:
            return Bill.objects.all()
        return Bill.objects.filter(family=self.request.user)

    def get_context_data(self, **kwargs):
        bill = self.get_object()
        context = super().get_context_data(**kwargs)
        context["bill"] = bill
        if not bill.is_paid:
            context["transaction"] = self.get_transaction(bill)
        return context


class ChildrenListView(LoginRequiredMixin, ListView):
    template_name = "registrations/children.html"
    context_object_name = "children"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if settings.KEPCHUP_CHILD_SCHOOL:
            context["schools"] = json.dumps(list(School.objects.filter(selectable=True).values("id", "name")))
        else:
            context["school"] = json.dumps([])
        return context

    def get_queryset(self):
        return Child.objects.filter(family=self.request.user).order_by("first_name")


class InstructorMixin(UserPassesTestMixin, LoginRequiredMixin):
    """Mixin for backend. Ensure that the user is logged in and is a sports responsible"""

    pk_url_kwarg = "pk"

    # noinspection PyUnresolvedReferences
    def get_object(self):
        pk = self.kwargs.get(self.pk_url_kwarg)
        return get_object_or_404(Registration, pk=pk)

    def test_func(self, user):
        # noinspection PyUnresolvedReferences
        if self.pk_url_kwarg in self.kwargs:
            course = self.get_object().course
            return user.is_active and user.is_instructor_of(course)
        return user.is_active and user.is_instructor


class RegisteredActivitiesListView(LoginRequiredMixin, WizardMixin, FormView):
    """
    This view is used after the course selection in the wizard. The user has selected all his courses
    and now has to confirm his registrations.
    """

    model = Registration
    form_class = AcceptTermsForm
    success_url = reverse_lazy("wizard_billing")
    template_name = "registrations/registration_list.html"

    @staticmethod
    def check_initial_condition(request):
        if not request.user.is_authenticated:
            raise NotReachableException("No account created")
        # noinspection PyUnresolvedReferences
        if not Registration.waiting.filter(child__family=request.user).exists():
            raise NotReachableException("No waiting Registration available")

    def get_success_url(self):
        if settings.KEPCHUP_USE_APPOINTMENTS:
            if self.request.user.montreux_needs_appointment:
                return reverse_lazy("wizard_appointments")
        if self.bill and self.bill.is_paid:
            messages.success(self.request, _("Your registrations have been recorded, thank you!"))
            return reverse_lazy("registrations:registrations_registered_activities")

        return self.success_url  # reverse_lazy("wizard_billing")

    def get_queryset(self):
        # noinspection PyUnresolvedReferences
        return (
            Registration.waiting.select_related("child", "course", "course__activity")
            .prefetch_related("extra_infos")
            .filter(child__in=self.request.user.children.all())
        )

    def set_price_modifiers(self, registrations, context):
        price_modifiers = {}
        for registration in registrations:
            for extra in registration.course.extra.all():
                price_modifiers[extra.id] = extra.price_dict
        context["price_modifiers"] = price_modifiers
        for registration in registrations:
            for extra in registration.extra_infos.all():
                if extra.key.id in price_modifiers:
                    price_modif = price_modifiers[extra.key.id].get(extra.value, 0)
                    if price_modif:
                        context["applied_price_modifications"][extra.key.id] = price_modif

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        registrations = self.get_queryset()
        context["registered_list"] = registrations
        registrations = registrations.order_by("course__start_date", "course__end_date")
        context["applied_price_modifications"] = {}
        self.set_price_modifiers(registrations, context)

        context["has_price_modification"] = len(context["applied_price_modifications"]) != 0
        if settings.KEPCHUP_USE_DIFFERENTIATED_PRICES:
            context["subtotal"] = sum([registration.get_price_category()[0] or 0 for registration in registrations])
        else:
            context["subtotal"] = sum([registration.get_price() or 0 for registration in registrations])
        context["total_price"] = context["subtotal"] + sum(context["applied_price_modifications"].values())
        context["overlaps"] = []
        context["overlapped"] = set()
        if settings.KEPCHUP_DISPLAY_OVERLAP_HELP:
            for idx, registration in list(enumerate(registrations))[:-1]:
                for registration2 in registrations[idx + 1 :]:  # noqa: E203
                    if registration.overlap(registration2):
                        context["overlaps"].append((registration, registration2))
                        context["overlapped"].add(registration.id)
                        context["overlapped"].add(registration2.id)
        return context

    def form_valid(self, form):
        self.bill = Bill.objects.create(
            status=Bill.STATUS.just_created,
            family=self.request.user,
            payment_method=settings.KEPCHUP_PAYMENT_METHOD,
        )
        for registration in self.get_queryset().all():
            registration.set_valid()
            # FIXME: here we are computing the prices a second time, this is dangerous.
            registration.price = registration.get_price()
            if registration.price == 0:
                registration.paid = True
            registration.bill = self.bill
            registration.save()

        self.bill.save()
        if self.bill.total == 0:
            self.bill.status = Bill.STATUS.paid
            self.bill.save()
        if not (settings.KEPCHUP_USE_APPOINTMENTS or settings.KEPCHUP_PAYMENT_METHOD in ["datatrans", "postfinance"]):
            # FIXME: si la facture est à 0: aucun paiement
            self.bill.send_confirmation()

        return super().form_valid(form)


class RegistrationDeleteView(InstructorMixin, DeleteView):
    model = Registration
    template_name = "registrations/confirm_cancel.html"

    def get_success_url(self):
        return self.object.course.get_absolute_url()

    def delete(self, request, *args, **kwargs):
        # noinspection PyAttributeOutsideInit
        self.object = self.get_object()
        success_url = self.get_success_url()
        try:
            self.object.cancel()
            self.object.save()
        except IntegrityError:
            # The registration for child and course existed previously and
            # was already canceled. We do not need to cancel it again
            self.object.delete()
        messages.add_message(self.request, messages.SUCCESS, _("Registration has been canceled."))
        return HttpResponseRedirect(success_url)


class SummaryView(LoginRequiredMixin, TemplateView):
    template_name = "registrations/summary.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["registered_list"] = self.request.user.get_registrations()
        return context


class WizardBillingView(LoginRequiredMixin, BillMixin, PaymentMixin, WizardMixin, TemplateView):
    """
    Display the bill: wizard final step view with pay button
    """

    template_name = "registrations/wizard_billing.html"

    @staticmethod
    def check_initial_condition(request):
        if not request.user.is_authenticated:
            raise NotReachableException("No account created")
        if request.user.montreux_needs_appointment and request.user.montreux_missing_appointments:
            raise NotReachableException("No Appointment taken")

        if not Bill.objects.filter(
            status__in=(Bill.STATUS.just_created, Bill.STATUS.waiting), family=request.user
        ).exists():
            raise NotReachableException("No Bill available")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["bill"] = Bill.objects.filter(family=self.request.user).order_by("created").last()

        context["include_calendar"] = False

        if settings.KEPCHUP_USE_APPOINTMENTS:
            context["include_calendar"] = True
            context["appointments"] = Appointment.objects.filter(family=self.request.user)

        context["transaction"] = self.get_transaction(context["bill"])
        return context

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        for bill in Bill.objects.filter(status=Bill.STATUS.just_created, family=self.request.user):
            bill.status = Bill.STATUS.waiting
            bill.save()
            if settings.KEPCHUP_USE_APPOINTMENTS and bill.is_wire_transfer:
                bill.send_confirmation()
        return response  # noqa: R504


class WizardCancelRegistrationView(LoginRequiredMixin, WizardMixin, FormView):
    success_url = reverse_lazy("wizard_activities")
    form_class = EmptyForm

    @staticmethod
    def check_initial_condition(request):
        if not request.user.is_authenticated:
            raise NotReachableException("No account created")

        if not Bill.objects.filter(
            status__in=(Bill.STATUS.just_created, Bill.STATUS.waiting), family=request.user
        ).exists():
            raise NotReachableException("No Bill available")

    def form_valid(self, form):
        for bill in Bill.objects.filter(
            status__in=(Bill.STATUS.just_created, Bill.STATUS.waiting), family=self.request.user
        ):
            for reg in bill.registrations.all():
                reg.extra_infos.all().delete()
            bill.registrations.all().update(status=Registration.STATUS.waiting, bill=None)
            bill.delete()
        return super().form_valid(form)


class WizardChildrenListView(WizardMixin, ChildrenListView):
    template_name = "registrations/wizard_children.html"

    @staticmethod
    def check_initial_condition(request):
        if not request.user.is_authenticated:
            raise NotReachableException("No account created")
        if Bill.objects.filter(
            family=request.user,
            status=Bill.STATUS.waiting,
            payment_method__in=(Bill.METHODS.datatrans, Bill.METHODS.postfinance),
        ).exists():
            raise NotReachableException("Payment expected first")
