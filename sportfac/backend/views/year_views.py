from django.conf import settings
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.core.urlresolvers import reverse, reverse_lazy
from django.db import connection

from django.utils.http import is_safe_url
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from django.views.generic import (CreateView, DeleteView, DetailView, FormView,
                                  ListView, UpdateView)

from ..forms import YearSelectForm, YearCreateForm
from ..models import YearTenant, Domain
from .mixins import BackendMixin


__all__ = ['ChangeYearFormView', 'YearCreateView', ]


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
        response.set_cookie(settings.VERSION_COOKIE_NAME, tenant.domains.first().domain,
                            max_age=settings.SESSION_COOKIE_AGE,
                            secure=settings.SESSION_COOKIE_SECURE or None)
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


class YearCreateView(SuccessMessageMixin, BackendMixin, FormView):
    form_class = YearCreateForm
    success_url = reverse_lazy('backend:home')
    template_name = 'backend/year/create.html'
    success_message = _("A new period, starting on %s and ending on %s has been defined")
    
    def get_success_message(self, cleaned_data):
        return self.success_message % (cleaned_data['start_date'], cleaned_data['end_date'])
    
    def form_valid(self, form):
        response = super(YearCreateView, self).form_valid(form)
        start = form.cleaned_data['start_date']
        end = form.cleaned_data['end_date']
        connection.set_schema_to_public()
        tenant = YearTenant(
            schema_name='period_%s_%s' % (start.strftime('%Y%m%d'), end.strftime('%Y%m%d')),
            start_date=start,
            end_date=end
        )
        tenant.save()
        domain = Domain.objects.create(
            is_primary=False,
            domain='%s-%s' % (start, end),
            tenant=tenant
        )
                
        return response
        # create tenant
        # copy activities
        # set tenant