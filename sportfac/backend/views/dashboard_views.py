from datetime import datetime

from django.core.urlresolvers import reverse_lazy
from django.views.generic import FormView, TemplateView
from django.contrib import messages
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from django.db.models import Count

from constance import config
from profiles.models import FamilyUser, Registration
from backend.forms import RegistrationDatesForm
from .mixins import BackendMixin

__all__ = ('HomePageView', 'RegistrationDatesView',)


###############################################################################
# Homepage

class HomePageView(BackendMixin, TemplateView):
    template_name = 'backend/home.html'

    def get_context_data(self, **kwargs):
        def time_str_to_milliseconds(time_str):
            return 1000 * int(datetime.strptime(time_str, '%Y-%m-%d').strftime('%s'))
        
        context = super(HomePageView, self).get_context_data(**kwargs)
        finished = FamilyUser.objects.filter(finished_registration=True)
        
        context['payement_due'] = finished.filter(total__gt=0).count()
        context['paid'] = finished.filter(total__gt=0, paid=True).count()
        registrations = Registration.objects.filter(
            created__range=(config.START_REGISTRATION,
                            config.END_REGISTRATION)
            ).extra({'creation': "to_char(profiles_registration.created, 'YYYY-MM-DD')"}
            ).values('creation'
            ).order_by('creation'
            ).annotate(num=Count('id'))

        context['registrations_per_day'] = [[time_str_to_milliseconds(reg.get('creation')),
                                             reg.get('num')] for reg in registrations]
        return context


###############################################################################
# Dates
class RegistrationDatesView(BackendMixin, FormView):
    template_name = 'backend/registration_dates.html'
    form_class = RegistrationDatesForm
    success_url = reverse_lazy('backend:home')
    
    def form_valid(self, form):
        form.save_to_constance()
        messages.add_message(self.request, messages.SUCCESS, _("Opening and closing dates have been changed"))
        return super(RegistrationDatesView, self).form_valid(form)

    def form_invalid(self, form):
        messages.add_message(self.request, messages.ERROR,
                             mark_safe(_("An error was found in form %s") % form.non_field_errors()))
        return super(RegistrationDatesView, self).form_invalid(form)
