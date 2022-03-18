# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.timezone import now
from django.views.generic import TemplateView

from braces.views import LoginRequiredMixin

from sportfac.views import WizardMixin, NotReachableException
from ..models import AppointmentSlot, Appointment


class SlotsView(TemplateView):
    template_name = 'appointments/slots.html'

    def get_context_data(self, **kwargs):
        context = super(SlotsView, self).get_context_data(**kwargs)
        qs = AppointmentSlot.objects.filter(start__gte=now())
        if qs.objects.exists():
            context['start'] = qs.first().start.date().isoformat()
        else:
            context['start'] = now().date().isoformat()
        context['appointments'] = self.request.user.is_authenticated and qs.filter(family=self.request.user) or Appointment.objects.none()
        context['available_dates'] = sorted(
            set([d.date() for d in qs.values_list('start', flat=True)])
        )
        return context


class SuccessfulRegister(TemplateView):
    """User is not logged in we can't link the appointments juste created. Let's just tell him it worked."""
    template_name = 'appointments/success.html'


class WizardSlotsView(LoginRequiredMixin, WizardMixin, SlotsView):
    template_name = "appointments/wizard_register.html"

    @staticmethod
    def check_initial_condition(request):
        if not request.user.is_authenticated():
            raise NotReachableException('No account created')
        from registrations.models import Bill
        if not request.user.montreux_needs_appointment:
            raise NotReachableException('No appointment expected')
        if not Bill.objects.filter(status=Bill.STATUS.just_created, family=request.user).exists():
            raise NotReachableException('No Bill available')
