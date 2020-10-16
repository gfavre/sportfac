# -*- coding: utf-8 -*-
from django.contrib.flatpages.models import FlatPage
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from django.utils.translation import ugettext as _
from django.views.generic import ListView, TemplateView, UpdateView

from appointments.models import AppointmentSlot
from ..forms import FlatPageForm
from .mixins import BackendMixin


class FlatPageListView(BackendMixin, ListView):
    model = FlatPage
    template_name = 'backend/site/flatpage_list.html'


class FlatPageUpdateView(SuccessMessageMixin, BackendMixin, UpdateView):
    model = FlatPage
    form_class = FlatPageForm
    template_name = 'backend/site/flatpage_update.html'
    success_url = reverse_lazy('backend:flatpages-list')
    success_message = _('<a href="%(url)s" class="alert-link">Page "%(title)s"</a> has been updated.')

    def get_success_message(self, cleaned_data):
        url = self.success_url
        return mark_safe(
            self.success_message % {'url': self.object.url,
                                    'title': cleaned_data.get('title')}
        )


class AppointmentsManagementView(BackendMixin, TemplateView):
    template_name = 'appointments/backend/create.html'

    def get_context_data(self, **kwargs):
        context = super(AppointmentsManagementView, self).get_context_data(**kwargs)
        if AppointmentSlot.objects.exists():
            context['start'] = AppointmentSlot.objects.first().start.date().isoformat()
        else:
            context['start'] = now().date().isoformat()
        return context


class AppointmentsListView(BackendMixin, ListView):
    model = AppointmentSlot
    template_name = 'appointments/backend/list.html'

    def get_queryset(self):
        return AppointmentSlot.objects.prefetch_related('appointments', 'appointments__child')

