# -*- coding: utf-8 -*-
import datetime
import json

from django.conf import settings
from django.contrib import messages
from django.core.urlresolvers import reverse_lazy
from django.db import transaction, connection
from django.db.models import Sum
from django.utils.translation import ugettext as _, get_language
from django.views.generic import DetailView, FormView, ListView, TemplateView

from braces.views import LoginRequiredMixin

from backend.dynamic_preferences_registry import global_preferences_registry
from profiles.forms import AcceptTermsForm
from profiles.models import School
from sportfac.views import WizardMixin
from .models import Bill, Child, Registration
from .tasks import send_confirmation


class ChildrenListView(LoginRequiredMixin, ListView):
    template_name = 'registrations/children.html'
    context_object_name = 'children'

    def get_context_data(self, **kwargs):
        context = super(ChildrenListView, self).get_context_data(**kwargs)
        if settings.KEPCHUP_CHILD_SCHOOL:
            context['schools'] = json.dumps(list(School.objects.filter(selectable=True).values('id', 'name')))
        else:
            context['school'] = json.dumps([])
        return context

    def get_queryset(self):
        return Child.objects.filter(family=self.request.user).order_by('first_name')


class WizardChildrenListView(WizardMixin, ChildrenListView):
    template_name = 'registrations/wizard_children.html'


class RegisteredActivitiesListView(LoginRequiredMixin, WizardMixin, FormView):
    model = Registration
    form_class = AcceptTermsForm
    success_url = reverse_lazy('wizard_billing')
    template_name = 'registrations/registration_list.html'

    def get_success_url(self):
        if self.bill and self.bill.is_paid:
            global_preferences = global_preferences_registry.manager()

            messages.success(
                self.request,
                _("Your registrations have been recorded, thank you!") + '<br>' +
                _("You'll receive a confirmation email from address: %s") % global_preferences['email__FROM_MAIL']
            )
            return reverse_lazy('registrations_registered_activities')
        return self.success_url

    def get_queryset(self):
        return Registration.waiting\
                           .select_related('child',
                                           'course',
                                           'course__activity')\
                           .prefetch_related('extra_infos')\
                           .filter(child__in=self.request.user.children.all())

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(RegisteredActivitiesListView, self).get_context_data(**kwargs)
        registrations = self.get_queryset()
        context['registered_list'] = registrations
        registrations = registrations.order_by('course__start_date', 'course__end_date')
        reductions = {}
        for registration in registrations:
            for extra in registration.course.extra.all():
                reductions[extra.id] = extra.reduction_dict
        context['reductions'] = reductions

        context['applied_reductions'] = {}
        for registration in registrations:
            for extra in registration.extra_infos.all():
                if extra.key.id in reductions:
                    reduction = reductions[extra.key.id].get(extra.value, 0)
                    if reduction:
                        context['applied_reductions'][extra.key.id] = reduction
        context['has_reductions'] = len(context['applied_reductions']) > 0
        context['subtotal'] = registrations.aggregate(Sum('course__price'))['course__price__sum']
        context['total_price'] = context['subtotal'] - sum(context['applied_reductions'].values())

        context['overlaps'] = []
        context['overlapped'] = set()
        for (idx, registration) in list(enumerate(registrations))[:-1]:
            for registration2 in registrations[idx+1:]:
                if registration.overlap(registration2):
                    context['overlaps'].append((registration, registration2))
                    context['overlapped'].add(registration.id)
                    context['overlapped'].add(registration2.id)

        return context

    def form_valid(self, form):
        self.bill = Bill.objects.create(
            status=Bill.STATUS.just_created,
            family=self.request.user
        )
        for registration in self.get_queryset().all():
            registration.set_valid()
            if registration.price == 0:
                registration.paid = True
            registration.bill = self.bill
            registration.save()

        self.bill.save()
        if self.bill.total == 0:
            self.bill.status = Bill.STATUS.paid
            self.bill.save()
        try:
            tenant_pk = connection.tenant.pk
        except AttributeError:
            tenant_pk = None
        transaction.on_commit(lambda: send_confirmation.delay(
            user_pk=self.request.user.pk,
            bill_pk=self.bill.pk,
            tenant_pk=tenant_pk,
            language=get_language(),
        ))
        return super(RegisteredActivitiesListView, self).form_valid(form)


class BillMixin(object):
    def get_context_data(self, **kwargs):
        context = super(BillMixin, self).get_context_data(**kwargs)
        preferences = global_preferences_registry.manager()
        offset_days = preferences['payment__DELAY_DAYS']
        base_date = self.request.REGISTRATION_END
        context['delay'] = base_date + datetime.timedelta(days=offset_days)
        context['iban'] = preferences['payment__IBAN']
        context['address'] = preferences['payment__ADDRESS']
        context['place'] = preferences['payment__PLACE']

        return context


class BillingView(LoginRequiredMixin, BillMixin, ListView):
    template_name = "registrations/billing.html"

    def get_queryset(self):
        return Bill.objects.filter(family=self.request.user).order_by('created')


class BillDetailView(LoginRequiredMixin, BillMixin, DetailView):
    template_name = 'registrations/bill-detail.html'

    def get_queryset(self):
        if self.request.user.is_manager:
            return Bill.objects.all()
        return Bill.objects.filter(family=self.request.user)


class WizardBillingView(LoginRequiredMixin, WizardMixin, BillMixin, TemplateView):
    template_name = "registrations/wizard_billing.html"

    def get_context_data(self, **kwargs):
        context = super(WizardBillingView, self).get_context_data(**kwargs)
        context['bill'] = Bill.objects.filter(family=self.request.user).order_by('created').last()
        return context

    def get(self, request, *args, **kwargs):
        response = super(WizardBillingView, self).get(request, *args, **kwargs)
        for bill in Bill.objects.filter(status=Bill.STATUS.just_created, family=self.request.user):
            bill.status = Bill.STATUS.waiting
            bill.save()
        return response


class SummaryView(LoginRequiredMixin, TemplateView):
    template_name = "registrations/summary.html"

    def get_context_data(self, **kwargs):
        context = super(SummaryView, self).get_context_data(**kwargs)
        context['registered_list'] = self.request.user.get_registrations()
        return context
