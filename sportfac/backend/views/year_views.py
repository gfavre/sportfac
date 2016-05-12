import os

from django.conf import settings
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.core.urlresolvers import reverse, reverse_lazy
from django.core.management import call_command
from django.db import connection, transaction
from django.utils.http import is_safe_url
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from django.views.generic import (CreateView, DeleteView, DetailView, FormView,
                                  ListView, UpdateView)

from activities.models import Course
from ..forms import YearSelectForm, YearCreateForm, YearForm
from ..models import YearTenant, Domain
from ..tasks import create_tenant
from .mixins import BackendMixin


__all__ = ['ChangeYearFormView', 'YearCreateView', 'YearDeleteView', 'YearListView', 'YearUpdateView']


class ChangeYearFormView(SuccessMessageMixin, BackendMixin, FormView):
    form_class = YearSelectForm
        
    def get_success_url(self):
        if not is_safe_url(url=self.success_url, host=self.request.get_host()):
            return reverse('backend:home')
        return self.success_url
    
    def form_valid(self, form):
        self.success_url = form.cleaned_data['next']
        response = super(ChangeYearFormView, self).form_valid(form)
        tenant = form.cleaned_data['tenant']
        self.request.session[settings.VERSION_SESSION_NAME] = tenant.domains.first().domain
        return response
    
    def get_success_message(self, cleaned_data):
        tenant = cleaned_data['tenant']
        message = _("You are now editing %s") % tenant
        if tenant.is_production:
            message = _("You are now editing period currently in production")
        elif tenant.is_past:
            message = _("You are now reviewing %s") % tenant
        elif tenant.is_future:
            message = _("You are now previewing %s") % tenant        
        return mark_safe(message)


class YearListView(BackendMixin, ListView):
    model = YearTenant
    template_name = 'backend/year/list.html'
    

class YearUpdateView(SuccessMessageMixin, BackendMixin, UpdateView):
    model = YearTenant
    form_class = YearForm
    success_url = reverse_lazy('backend:year-list')
    success_message = _('Period has been updated.')
    template_name = 'backend/year/update.html'


class YearDeleteView(SuccessMessageMixin, BackendMixin, DeleteView):
    model = YearTenant
    success_message = _("Period has been deleted.")
    success_url = reverse_lazy('backend:year-list')
    template_name = 'backend/year/confirm_delete.html'
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        identifier = str(self.get_object())
        messages.add_message(self.request, messages.SUCCESS,
                             _("Period %(identifier)s has been deleted.") % {'identifier': identifier})
        connection.set_schema_to_public()
        response = super(YearDeleteView, self).delete(request, *args, **kwargs)
        return response


class YearCreateView(SuccessMessageMixin, BackendMixin, FormView):
    form_class = YearCreateForm
    success_url = reverse_lazy('backend:year-list')
    template_name = 'backend/year/create.html'
    success_message = _("A new period, starting on %s and ending on %s has been defined")
    
    def get_success_message(self, cleaned_data):
        return self.success_message % (cleaned_data['start_date'], cleaned_data['end_date'])
    
    @transaction.atomic
    def form_valid(self, form):
        response = super(YearCreateView, self).form_valid(form)
        start = form.cleaned_data['start_date']
        end = form.cleaned_data['end_date']
        connection.set_schema_to_public()
        tenant, created = YearTenant.objects.get_or_create(
            schema_name='period_%s_%s' % (start.strftime('%Y%m%d'), 
                                          end.strftime('%Y%m%d')),
            defaults = {
                'start_date': start,
                'end_date': end,
                'status': YearTenant.STATUS.creating
            }
        )
        domain, created = Domain.objects.get_or_create(
            tenant=tenant,
            domain='%s-%s' % (start.strftime('%Y%m%d'), 
                              end.strftime('%Y%m%d')),
        )
        copy_from_id = None
        if form.cleaned_data.get('copy_activities', None):
            copy_from_id = form.cleaned_data.get('copy_activities').pk
        create_tenant.delay(start.strftime('%Y%m%d'), end.strftime('%Y%m%d'), 
                            tenant.pk, copy_from_id)
        return response
        