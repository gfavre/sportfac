from django.conf import settings
from django.db import transaction
from django.shortcuts import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView, TemplateView

from braces.views import LoginRequiredMixin

from appointments.models import Rental
from profiles.models import FamilyUser
from wizard.views import BaseWizardStepView
from ..forms import RegistrationValidationForm, RegistrationValidationFreeForm
from ..models import Bill as Invoice
from ..models import Registration, RegistrationValidation
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

    @transaction.atomic
    def form_valid(self, form):
        user: FamilyUser = self.request.user  # noqa
        invoice = Invoice.objects.create(
            status=Invoice.STATUS.waiting, family=user, payment_method=settings.KEPCHUP_PAYMENT_METHOD
        )
        Registration.waiting.filter(child__family=user).update(bill=invoice, status=Registration.STATUS.valid)
        if settings.KEPCHUP_USE_APPOINTMENTS:
            Rental.objects.filter(child__family=user, paid=False).update(invoice=invoice)

        invoice.save()  # => bill status become paid if all registrations are paid
        if invoice.total == 0:
            invoice.status = Invoice.STATUS.paid
            invoice.save()
        # Create validation entry if consent is given
        RegistrationValidation.objects.create(
            user=user,
            invoice=invoice,
            consent_given=True,
        )
        # TODO Redirect to success or to payment depending on the invoice amount
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user: FamilyUser = self.request.user  # noqa

        validation = context["validation"]
        if not validation:
            validation = RegistrationValidation.objects.filter(
                user=user,
                consent_given=True,
            ).first()
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

        total_amount = sum(reg.price for reg in registrations)
        total_amount += sum(
            sum(extra_infos.price_modifier for extra_infos in reg.extra_infos.all()) for reg in registrations
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user: FamilyUser = self.request.user  # noqa
        context["invoice"] = Invoice.objects.filter(
            family=user, status__in=(Invoice.STATUS.waiting, Invoice.STATUS.just_created)
        ).first()
        registrations = context["invoice"].registrations.all()
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
        context.update(
            {
                "registrations": registrations,
                "rentals": rentals,
                "total_amount": total_amount,
            }
        )

        context["bill"] = context["invoice"]
        context["transaction"] = self.get_transaction(context["invoice"])
        return context
