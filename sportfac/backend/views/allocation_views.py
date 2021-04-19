# -*- coding: utf-8 -*-
import datetime
import os
from tempfile import mkdtemp
try:
    import urlparse
    from urllib import urlencode
except ImportError:  # For Python 3
    import urllib.parse as urlparse
    from urllib.parse import urlencode


from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponse
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from django.views.generic import CreateView, DeleteView, DetailView, \
                                ListView, UpdateView
from django.utils.timezone import now

from dateutil.relativedelta import relativedelta

from activities.models import AllocationAccount
from activities.forms import AllocationAccountForm
from .mixins import BackendMixin


__all__ = [
    'AllocationAccountListView', 'AllocationAccountCreateView',  'AllocationAccountUpdateView',
    'AllocationAccountDeleteView', 'AllocationAccountReportView'
]


class AllocationAccountReportView(BackendMixin, ListView):
    model = AllocationAccount
    template_name = 'backend/allocations/report.html'

    def get_context_data(self, **kwargs):
        context = super(AllocationAccountReportView, self).get_context_data(**kwargs)
        context['start'] = (now() - relativedelta(days=29)).date()
        context['end'] = now().date()

        if 'start' in self.request.GET:
            try:
                context['start'] = datetime.datetime.strptime(self.request.GET.get('start'), "%Y-%m-%d").date()
            except ValueError:
                pass
        if 'end' in self.request.GET:
            try:
                context['end'] = datetime.datetime.strptime(self.request.GET.get('end'), "%Y-%m-%d").date()
            except ValueError:
                pass
        context['object_list'] = AllocationAccount.objects.prefetch_related(
            'registrations', 'registrations__bill', 'registrations__course', 'registrations__course__activity',
            'registrations__bill__datatrans_transactions',)

        for allocation_account in context['object_list']:
            registrations = allocation_account.get_registrations(context['start'], context['end'])
            allocation_account.period_registrations = registrations
            allocation_account.period_total = sum([registration.price for registration in registrations])

        url = self.request.get_full_path()
        url_parts = list(urlparse.urlparse(url))
        query = dict(urlparse.parse_qsl(url_parts[4]))
        query.update(pdf=1)
        url_parts[4] = urlencode(query)
        context['pdf_url'] = urlparse.urlunparse(url_parts)
        return context

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        if 'pdf' in self.request.GET:
            from backend.utils import AllocationReportPDFRenderer
            context = self.get_context_data(request=self.request)
            renderer = AllocationReportPDFRenderer(context, self.request)
            tempdir = mkdtemp()
            filename = u'{}-{}-{}.pdf'.format(_("allocations"),
                                              context['start'].isoformat(),
                                              context['end'].isoformat()
                                              )
            filepath = os.path.join(tempdir, filename)
            renderer.render_to_pdf(filepath)
            response = HttpResponse(open(filepath).read(), content_type='application/pdf')
            response['Content-Disposition'] = u'attachment; filename="{}"'.format(filename)
            return response
        return super(AllocationAccountReportView, self).get(request, *args, **kwargs)


class AllocationAccountListView(BackendMixin, ListView):
    model = AllocationAccount
    template_name = 'backend/allocations/list.html'


class AllocationAccountCreateView(SuccessMessageMixin, BackendMixin, CreateView):
    model = AllocationAccount
    form_class = AllocationAccountForm
    success_url = reverse_lazy('backend:allocation-list')
    success_message = _('<a href="%(url)s" class="alert-link">Allocation account (%(number)s)</a> has been created.')
    template_name = 'backend/allocations/create.html'

    def get_success_message(self, cleaned_data):
        url = self.object.get_backend_url()
        return mark_safe(self.success_message % {'url': url,
                                                 'number': self.object.account})


class AllocationAccountUpdateView(SuccessMessageMixin, BackendMixin, UpdateView):
    model = AllocationAccount
    form_class = AllocationAccountForm
    success_url = reverse_lazy('backend:allocation-list')
    success_message = _('<a href="%(url)s" class="alert-link">Allocation account (%(number)s)</a> has been updated.')
    template_name = 'backend/allocations/update.html'

    def get_success_message(self, cleaned_data):
        url = self.object.get_backend_url()
        return mark_safe(self.success_message % {'url': url,
                                                 'number': self.object.number})


class AllocationAccountDeleteView(SuccessMessageMixin, BackendMixin, DeleteView):
    model = AllocationAccount
    success_message = _("Allocation has been deleted.")
    success_url = reverse_lazy('backend:Allocation-list')
    template_name = 'backend/allocations/confirm_delete.html'
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        identifier = self.get_object().number
        messages.add_message(self.request, messages.SUCCESS,
                             _("Allocation account %(identifier)s has been deleted.") % {
                                'identifier': identifier
                             })
        return super(AllocationAccountDeleteView, self).delete(request, *args, **kwargs)
