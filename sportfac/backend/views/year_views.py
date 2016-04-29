from django.conf import settings
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.core.urlresolvers import reverse, reverse_lazy
from django.utils.http import is_safe_url
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from django.views.generic import (CreateView, DeleteView, DetailView, FormView,
                                  ListView, UpdateView)

from ..forms import YearSelectForm
from .mixins import BackendMixin


__all__ = ['ChangeYearFormView', ]


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


