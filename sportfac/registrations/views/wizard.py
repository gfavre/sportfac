import datetime

from braces.views import LoginRequiredMixin
from django.conf import settings
from django.db import connection
from django.db import transaction
from django.shortcuts import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils import translation
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView
from django.views.generic import TemplateView

from appointments.models import Rental
from backend.dynamic_preferences_registry import global_preferences_registry
from profiles.models import FamilyUser
from registrations.tasks import send_bill_confirmation as send_bill_confirmation_task
from registrations.tasks import send_confirmation as send_confirmation_task
from wizard.views import BaseWizardStepView

from ..forms import RegistrationValidationForm
from ..forms import RegistrationValidationFreeForm
from ..models import Bill as Invoice
from ..models import Registration
from ..models import RegistrationValidation
from .user import ChildrenListView
from .utils import PaymentMixin


class WizardChildrenView(BaseWizardStepView, ChildrenListView):
    template_name = "wizard/children.html"


class WizardConfirmationStepView(LoginRequiredMixin, BaseWizardStepView, FormView):
    model = RegistrationValidation
    form_class = RegistrationValidationForm
    step_slug = "confirmation"
    template_name = "wizard/confirm.html"

    def get_form_class(self):
        user: FamilyUser = self.request.user  # noqa
        if user.registration_set.filter(status=Registration.STATUS.waiting, price__gt=0).exists():
            return RegistrationValidationForm
        if settings.KEPCHUP_USE_APPOINTMENTS and Rental.objects.filter(child__family=user, paid=False).exists():
            return RegistrationValidationForm
        return RegistrationValidationFreeForm

    def get_registrations(self, user):
        waiting_registrations = (
            Registration.waiting.filter(child__family=user)
            .select_related("course")
            .prefetch_related("course__extra", "extra_infos")
        )
        if settings.KEPCHUP_PAYMENT_METHOD in ("postfinance", "datatrans"):
            # With immediate payment methods, we are block registration process while invoice is not paid.
            # In this case we can redisplay step with the existing invoice registrations and a note
            # "you validated this step on DATE"
            if waiting_registrations.exists():
                return waiting_registrations, None
            invoice = Invoice.objects.filter(family=user, status=Invoice.STATUS.waiting).first()
            if not invoice:
                return waiting_registrations, None
            return (
                invoice.registrations.select_related("course").prefetch_related("course__extra", "extra_infos"),
                invoice,
            )
        return waiting_registrations, None

    @transaction.atomic
    def form_valid(self, form):
        user: FamilyUser = self.request.user  # noqa

        invoice = Invoice.objects.create(
            status=Invoice.STATUS.waiting, family=user, payment_method=settings.KEPCHUP_PAYMENT_METHOD
        )
        Registration.waiting.filter(child__family=user).update(bill=invoice, status=Registration.STATUS.valid)
        if settings.KEPCHUP_USE_APPOINTMENTS:
            Rental.objects.filter(child__family=user, paid=False).update(invoice=invoice)

        # Create validation entry if consent is given
        RegistrationValidation.objects.create(
            user=user,
            invoice=invoice,
            consent_given=True,
        )
        success_url = self.get_success_url()
        invoice.save()  # => bill status become paid if all registrations are paid
        if invoice.total == 0:
            # Let bypass the end of process if the invoice is free
            # Set the invoice status to paid
            invoice.status = Invoice.STATUS.paid
            invoice.save()
            # Send confirmation
            try:
                tenant_pk = connection.tenant.pk
            except AttributeError:
                tenant_pk = None
            transaction.on_commit(
                lambda: send_confirmation_task.delay(
                    user_pk=str(user.pk),  # noqa: B023
                    tenant_pk=tenant_pk,  # noqa: B023
                    language=translation.get_language(),
                )
            )
            success_url = reverse_lazy("wizard:step", kwargs={"step_slug": "success"})
        elif settings.KEPCHUP_PAYMENT_METHOD == "iban":
            try:
                tenant_pk = connection.tenant.pk
            except AttributeError:
                tenant_pk = None
            transaction.on_commit(
                lambda: send_bill_confirmation_task.delay(
                    user_pk=str(user.pk),  # noqa: B023
                    bill_pk=str(invoice.pk),  # noqa: B023
                    tenant_pk=tenant_pk,  # noqa: B023
                    language=translation.get_language(),
                )
            )
        return HttpResponseRedirect(success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user: FamilyUser = self.request.user  # noqa

        validation = context["validation"]
        if validation:
            context.update(
                {
                    "consent_already_given": True,
                    "validation_date": validation.modified,
                }
            )
        else:
            context.update(
                {
                    "consent_already_given": False,
                    "form": self.form_class(
                        initial={"consent_given": False},
                        previous_url=self.get_previous_url(),
                        tooltip_message=_("Vous devez cocher cette case pour continuer."),
                    ),
                }
            )

        registrations = context["registrations"]  # Registration.waiting.filter(child__in=user.children.all())
        for reg in registrations:
            reg.row_span = 1 + reg.extra_infos.count()

        total_amount = sum(reg.price or 0 for reg in registrations)
        total_amount += sum(
            sum(extra_infos.price_modifier or 0 for extra_infos in reg.extra_infos.all()) for reg in registrations
        )
        rentals = None
        if settings.KEPCHUP_USE_APPOINTMENTS:
            rentals = Rental.objects.filter(child__family=user, paid=False)
            total_amount += sum(rental.amount for rental in rentals)
        context.update(
            {
                "registrations": registrations,
                "rentals": rentals,
                "total_amount": total_amount,
            }
        )
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


class WizardPaymentStepView(LoginRequiredMixin, PaymentMixin, BaseWizardStepView, TemplateView):
    step_slug = "payment"
    template_name = "wizard/payment.html"
    success_url = reverse_lazy("wizard:confirmation")

    def get_registrations(self, user):
        invoice = Invoice.objects.filter(family=user, status=Invoice.STATUS.waiting).first()
        if invoice:
            return (
                invoice.registrations.select_related("course").prefetch_related("course__extra", "extra_infos"),
                invoice,
            )
        return None, None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user: FamilyUser = self.request.user  # noqa
        invoice = Invoice.objects.filter(
            family=user, status__in=(Invoice.STATUS.waiting, Invoice.STATUS.just_created)
        ).first()
        registrations = invoice.registrations.all()
        for reg in registrations:
            reg.row_span = 1 + reg.extra_infos.count()
        total_amount = sum(reg.price for reg in registrations)
        total_amount += sum(
            sum(extra_infos.price_modifier for extra_infos in reg.extra_infos.all()) for reg in registrations
        )
        rentals = None
        if settings.KEPCHUP_USE_APPOINTMENTS:
            rentals = Rental.objects.filter(child__family=user, paid=False)
            total_amount += sum(rental.amount for rental in rentals)
        preferences = global_preferences_registry.manager()
        offset_days = preferences["payment__DELAY_DAYS"]
        base_date = invoice.created  # self.request.REGISTRATION_END

        context.update(
            {
                "registrations": registrations,
                "rentals": rentals,
                "total_amount": total_amount,
                "invoice": invoice,
                "delay": base_date + datetime.timedelta(days=offset_days),
                "iban": preferences.get("payment__IBAN", ""),
                "address": preferences.get("payment__ADDRESS", ""),
                "place": preferences.get("payment__PLACE", ""),
            }
        )

        context["bill"] = context["invoice"]
        return context
