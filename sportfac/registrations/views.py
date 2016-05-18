from django.core.urlresolvers import reverse_lazy, reverse
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import render
from django.views.generic import FormView, ListView, TemplateView

from braces.views import LoginRequiredMixin

from sportfac.views import WizardMixin, PhaseForbiddenMixin
from profiles.forms import AcceptTermsForm
from .models import Bill, Child, Registration


class ChildrenListView(LoginRequiredMixin, ListView):
    template_name = 'registrations/children.html'
    context_object_name = 'children'
    
    def get_queryset(self):
        return Child.objects.filter(family=self.request.user).order_by('first_name')

class WizardChildrenListView(WizardMixin, ChildrenListView):
    template_name = 'registrations/wizard_children.html'


class RegisteredActivitiesListView(WizardMixin, FormView):
    model = Registration
    form_class = AcceptTermsForm
    success_url = reverse_lazy('wizard_billing')
    template_name = 'registrations/registration_list.html'

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
        context['registered_list'] = self.get_queryset()
        registrations = context['registered_list'].order_by('course__start_date', 
                                                            'course__end_date')
        context['total_price'] = registrations.aggregate(Sum('course__price'))['course__price__sum']
        
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
        with transaction.atomic():
            bill = Bill.objects.create(
                status = Bill.STATUS.just_created,
                family = self.request.user
            )
            for registration in self.get_queryset().all():
                registration.set_valid()
                registration.bill = bill
                registration.save()
            bill.save()
        return super(RegisteredActivitiesListView, self).form_valid(form)


class BillingView(PhaseForbiddenMixin, TemplateView):
    template_name = "registrations/billing.html"
    forbidden_phases = (1,)
    
    def get_context_data(self, **kwargs):
        context = super(BillingView, self).get_context_data(**kwargs)
        context['bills'] = Bill.objects.filter(family=self.request.user)
        context['registered_list'] = self.request.user.get_registrations()
        return context

class WizardBillingView(WizardMixin, TemplateView):
    template_name = "registrations/wizard_billing.html"

    def get_context_data(self, **kwargs):
        context = super(WizardBillingView, self).get_context_data(**kwargs)
        context['bill'] = Bill.objects.filter(family=self.request.user).order_by('created').last()
        return context
    
    def get(self, request, *args, **kwargs):
        response = super(WizardBillingView, self).get(request, *args, **kwargs)
        for bill in Bill.objects.filter(status=Bill.STATUS.just_created, family=self.request.user):
            bill.status = status=Bill.STATUS.waiting
            bill.save()
        return response
    

class SummaryView(BillingView):
    template_name = "registrations/summary.html"