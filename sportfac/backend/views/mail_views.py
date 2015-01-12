from django.contrib import messages
from django.contrib.sites.models import get_current_site
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, \
                                ListView, UpdateView
from django.contrib.messages.views import SuccessMessageMixin

from profiles.models import FamilyUser

from mailer.views import MailView

from .mixins import BackendMixin


class SimpleMailView(BackendMixin, MailView):
    recipients_queryset = FamilyUser.objects.filter(is_superuser=True)
    template_name = 'backend/mail/preview.html'
    success_url = reverse_lazy('backend:home')
    subject = 'Inscription au sport scolaire facultatif - EP Coppet'
    message_template = 'mailer/confirmation.txt'
    
    def get_context_data(self, **kwargs):
        context = super(SimpleMailView, self).get_context_data(**kwargs)
        context['SITE_URL'] = ''.join(('http://', 
                                      get_current_site(self.request).domain,
                                      reverse('wizard_confirm')))
        return context
        