from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.sites.models import get_current_site
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse, reverse_lazy
from django.template import loader, Context, RequestContext
from django.views.generic import CreateView, DeleteView, DetailView, \
                                ListView, UpdateView


from profiles.models import FamilyUser

from mailer.views import MailView

from .mixins import BackendMixin


class NeedConfirmationView(BackendMixin, MailView):
    "Mail to people having not confirmed activities yet."
    recipients_queryset = FamilyUser.objects.filter(is_superuser=False)
    success_url = reverse_lazy('backend:home')
    subject = 'Inscription au sport scolaire facultatif - EP Coppet'
    message_template = 'mailer/confirmation.txt'
    
    def get_context_data(self, **kwargs):
        context = super(NeedConfirmationView, self).get_context_data(**kwargs)
        context['url'] = ''.join(('http://', 
                                  get_current_site(self.request).domain,
                                  reverse('wizard_confirm')))
        return context
 

class NotPaidYetView(BackendMixin, MailView):
    "Mail to people having registered to courses but not paid yet"
    recipients_queryset = FamilyUser.objects.filter(finished_registration=True, 
                                                    paid=False, total__gt=0)
    success_url = reverse_lazy('backend:home')
    subject = 'Inscription au sport scolaire facultatif - EP Coppet - rappel'
    message_template = 'mailer/notpaid.txt'


class ParticipantsView(BackendMixin, MailView):
    recipients_queryset = FamilyUser.objects.filter(is_superuser=False)
    success_url = reverse_lazy('backend:home')
    subject = 'Inscription au sport scolaire facultatif - EP Coppet'
    message_template = 'mailer/confirmation.txt'
    
    def get_recipient_list(self):
        pass
    
    def get_context_data(self, **kwargs):
        context = super(ParticipantsView, self).get_context_data(**kwargs)
        try:
            course = Course.objects.get(id=self.kwargs.get('course'))
            context['course'] = course
        except Course.DoesNotExist:
            pass

        context['url'] = ''.join(('http://', 
                                  get_current_site(self.request).domain,
                                  reverse('wizard_confirm')))
        return context

